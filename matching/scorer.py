# matching/scorer.py
"""
Uses DeepSeek-V3.2 (via Azure AI Foundry) to score each job and generate
a tailored cover letter for Mohamed's profile.
"""
import os
import json
import logging
from openai import OpenAI
from config import CV_PROFILE, RELOCATION_KEYWORDS, MIN_SCORE_TO_INCLUDE, KNOWN_RELOCATORS

# Title must contain at least one of these to be worth scoring
TITLE_MUST_INCLUDE = {
    "cloud", "security", "devops", "devsecops", "platform", "kubernetes",
    "k8s", "sre", "reliability", "infrastructure", "infra", "architect",
    "engineer", "devops", "automation", "aws", "azure", "gcp",
}

# If title contains any of these it's immediately discarded (junk filter)
TITLE_JUNK = {
    "junior", "intern", "internship", "trainee", "werkstudent", "praktikant",
    "sales", "account executive", "marketing", "hr ", "human resources",
    "recruiter", "finance", "legal", "copywriter", "designer", "product manager",
    "scrum master", "project manager", "it-workplace", "workplace engineer",
    "support engineer", "helpdesk", "1st line", "2nd line",
}


def is_relevant_title(job: dict) -> bool:
    """Quick pre-filter — avoids burning AI tokens on obvious junk."""
    title = job.get("title", "").lower()
    # Reject if junk keyword found
    if any(junk in title for junk in TITLE_JUNK):
        return False
    # Accept if at least one relevant keyword found
    return any(kw in title for kw in TITLE_MUST_INCLUDE)

logger = logging.getLogger(__name__)

# Lazy client — initialized on first use so imports don't require env vars
_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.environ["AZURE_AI_API_KEY"],
            base_url=os.environ["AZURE_AI_ENDPOINT"].rstrip("/") + "/openai/v1/",
        )
    return _client


MODEL = os.environ.get("AZURE_AI_MODEL", "DeepSeek-V3.2")

SCORE_PROMPT = """Score this job for: Senior Cloud Security Engineer, 6yr exp, AWS/Azure/GCP, Kubernetes/EKS/AKS, Cilium/eBPF, Falco, Wiz CNAPP, DevSecOps, ArgoCD, Terraform, Pulumi, GDPR/NIS2, Go/Python. Relocating Cairo→EU.

Job: {title} @ {company} ({country})
{description}

Return ONLY JSON: {{"score":<0-100>,"reasons":["r1","r2"],"missing":["g1"]}}
85-100=perfect,70-84=strong,55-69=decent,<55=poor. Max 2 reasons+1 gap."""

COVER_LETTER_PROMPT = """Write 2 short paragraphs (3 lines each) as Mohamed ElBeltagy applying for {title} at {company} in {location}.
Mohamed: Senior Cloud Security Engineer, 6yr, AWS/K8s/Wiz/DevSecOps, relocating Cairo→EU.
Job: {description}
- Para 1: excitement about THIS company+role, what he brings
- Para 2: 2 matching technical strengths + closing
No "I am writing to apply", no signature, plain text only."""


def detect_relocation(job: dict) -> bool:
    """Check if job description or title mentions relocation/visa support."""
    text = (job.get("description", "") + " " + job.get("title", "")).lower()
    return any(kw in text for kw in RELOCATION_KEYWORDS)


def detect_known_relocator(job: dict) -> bool:
    """Check if company is on the known-relocator list (visa/relocation track record)."""
    company = job.get("company", "").lower()
    return any(name in company for name in KNOWN_RELOCATORS)


def score_job(job: dict) -> dict:
    """Score one job against CV. Returns dict with score, reasons, missing."""
    prompt = SCORE_PROMPT.format(
        cv_profile=CV_PROFILE,
        title=job.get("title", ""),
        company=job.get("company", ""),
        country=job.get("country", ""),
        description=job.get("description", "")[:800],   # capped to stay under token limit
    )
    try:
        response = _get_client().chat.completions.create(
            model=MODEL,
            max_tokens=256,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON for '{job.get('title')}': {e}")
        return {"score": 0, "reasons": [], "missing": ["parse error"]}
    except Exception as e:
        logger.error(f"API error for '{job.get('title')}': {e}")
        return {"score": 0, "reasons": [], "missing": ["api error"]}


def generate_cover_letter(job: dict) -> str:
    """Generate a 2-paragraph tailored cover letter for one job."""
    prompt = COVER_LETTER_PROMPT.format(
        cv_profile=CV_PROFILE,
        title=job.get("title", ""),
        company=job.get("company", ""),
        location=job.get("location", ""),
        description=job.get("description", "")[:800],   # capped to stay under token limit
    )
    try:
        response = _get_client().chat.completions.create(
            model=MODEL,
            max_tokens=300,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Cover letter error for '{job.get('title')}': {e}")
        return ""


def enrich_jobs(jobs: list[dict]) -> list[dict]:
    """
    Score all jobs, filter below threshold, generate cover letters for passing jobs.
    Returns list sorted by score descending.
    """
    # Pre-filter junk titles before hitting the AI
    relevant = [j for j in jobs if is_relevant_title(j)]
    skipped = len(jobs) - len(relevant)
    if skipped:
        logger.info(f"Pre-filter: skipped {skipped} irrelevant titles, scoring {len(relevant)}/{len(jobs)}")

    enriched = []
    for i, job in enumerate(relevant):
        logger.info(f"Scoring {i+1}/{len(relevant)}: {job.get('title')} @ {job.get('company')}")
        result = score_job(job)
        score = result.get("score", 0)

        if score < MIN_SCORE_TO_INCLUDE:
            continue

        # Generate cover letter only for jobs that passed the threshold
        logger.info(f"  → {score}% match — generating cover letter")
        cover_letter = generate_cover_letter(job)

        enriched.append({
            **job,
            "score":           score,
            "reasons":         result.get("reasons", []),
            "missing":         result.get("missing", []),
            "relocation":      detect_relocation(job),
            "known_relocator": detect_known_relocator(job),
            "cover_letter":    cover_letter,
        })

    enriched.sort(key=lambda j: j["score"], reverse=True)
    logger.info(f"Scoring done: {len(enriched)}/{len(jobs)} passed {MIN_SCORE_TO_INCLUDE}% threshold")
    return enriched
