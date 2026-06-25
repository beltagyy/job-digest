# matching/scorer.py
"""
Uses DeepSeek-V3 (via Azure AI Foundry serverless endpoint) to score each job.
Returns enriched job dicts with score (0-100), match reasons, and missing skills.
"""
import os
import json
import logging
from openai import OpenAI
from config import CV_PROFILE, RELOCATION_KEYWORDS, MIN_SCORE_TO_INCLUDE

logger = logging.getLogger(__name__)

# Azure AI Foundry serverless endpoint — uses standard OpenAI-compatible API
client = OpenAI(
    api_key=os.environ["AZURE_AI_API_KEY"],
    base_url=os.environ["AZURE_AI_ENDPOINT"].rstrip("/") + "/openai/v1/",
)

MODEL = os.environ.get("AZURE_AI_MODEL", "DeepSeek-V3")

SCORE_PROMPT = """You are a job-CV matching assistant. Score how well this job matches the candidate's profile.

CANDIDATE PROFILE:
{cv_profile}

JOB:
Title: {title}
Company: {company}
Country: {country}
Description: {description}

Return ONLY a valid JSON object (no markdown, no explanation) in this exact format:
{{"score": <integer 0-100>, "reasons": ["reason1", "reason2", "reason3"], "missing": ["gap1", "gap2"]}}

Scoring guide:
- 85-100: Near-perfect match
- 70-84: Strong match, 1-2 gaps
- 55-69: Decent match, worth considering
- 0-54: Poor match

Be concise - max 3 reasons and 2 missing items."""


def detect_relocation(job: dict) -> bool:
    """Check if job description mentions relocation/visa support."""
    text = (job.get("description", "") + " " + job.get("title", "")).lower()
    return any(kw in text for kw in RELOCATION_KEYWORDS)


def score_job(job: dict) -> dict:
    """Call DeepSeek via Azure to score one job. Falls back to score=0 on error."""
    prompt = SCORE_PROMPT.format(
        cv_profile=CV_PROFILE,
        title=job.get("title", ""),
        company=job.get("company", ""),
        country=job.get("country", ""),
        description=job.get("description", "")[:3000],
    )
    try:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=256,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if model adds them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        logger.warning(f"Model returned invalid JSON for '{job.get('title')}': {e}")
        return {"score": 0, "reasons": [], "missing": ["parse error"]}
    except Exception as e:
        logger.error(f"API error for '{job.get('title')}': {e}")
        return {"score": 0, "reasons": [], "missing": ["api error"]}


def enrich_jobs(jobs: list[dict]) -> list[dict]:
    """Score all jobs, filter below threshold, return sorted by score desc."""
    enriched = []
    for i, job in enumerate(jobs):
        logger.info(f"Scoring {i+1}/{len(jobs)}: {job.get('title')} @ {job.get('company')}")
        result = score_job(job)
        score = result.get("score", 0)
        if score < MIN_SCORE_TO_INCLUDE:
            continue
        enriched.append({
            **job,
            "score":      score,
            "reasons":    result.get("reasons", []),
            "missing":    result.get("missing", []),
            "relocation": detect_relocation(job),
        })

    enriched.sort(key=lambda j: j["score"], reverse=True)
    logger.info(f"Scoring done: {len(enriched)}/{len(jobs)} passed threshold")
    return enriched
