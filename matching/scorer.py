# matching/scorer.py
"""
Uses Claude Haiku to score each job against Mohamed's CV profile.
Returns enriched job dicts with score (0-100), match reasons, and missing skills.
"""
import os
import json
import logging
import anthropic
from config import CV_PROFILE, RELOCATION_KEYWORDS, MIN_SCORE_TO_INCLUDE

logger = logging.getLogger(__name__)

# Single client reused across all scoring calls
anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

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
- 85-100: Near-perfect match, candidate has almost all required skills
- 70-84: Strong match, 1-2 gaps but mostly aligned
- 55-69: Decent match, worth considering
- 0-54: Poor match, significant skill or seniority mismatch

Be concise - max 3 reasons and 2 missing items."""


def detect_relocation(job: dict) -> bool:
    """Check if job description mentions relocation/visa support."""
    text = (job.get("description", "") + " " + job.get("title", "")).lower()
    return any(kw in text for kw in RELOCATION_KEYWORDS)


def score_job(job: dict) -> dict:
    """
    Call Claude Haiku to score one job against CV_PROFILE.
    Returns dict with keys: score, reasons, missing.
    Falls back to score=0 on any API error.
    """
    prompt = SCORE_PROMPT.format(
        cv_profile=CV_PROFILE,
        title=job.get("title", ""),
        company=job.get("company", ""),
        country=job.get("country", ""),
        description=job.get("description", "")[:3000],
    )
    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.content[0].text.strip())
    except json.JSONDecodeError as e:
        logger.warning(f"Claude returned invalid JSON for '{job.get('title')}': {e}")
        return {"score": 0, "reasons": [], "missing": ["parse error"]}
    except anthropic.APIError as e:
        logger.error(f"Claude API error for '{job.get('title')}': {e}")
        return {"score": 0, "reasons": [], "missing": ["api error"]}


def enrich_jobs(jobs: list[dict]) -> list[dict]:
    """
    Score all jobs, attach results to each job dict, filter below threshold.
    Returns list sorted by score descending.
    """
    enriched = []
    for i, job in enumerate(jobs):
        logger.info(f"Scoring job {i+1}/{len(jobs)}: {job.get('title')} @ {job.get('company')}")
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
    logger.info(f"Scoring done: {len(enriched)}/{len(jobs)} jobs passed threshold")
    return enriched
