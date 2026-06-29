# matching/scorer.py
"""
Uses DeepSeek-V3.2 (via Azure AI Foundry) to score jobs and generate cover letters.

KEY FIX: Azure serverless has a 128k token-per-session limit that kills the process
silently at ~150 jobs. We work around this by scoring in subprocess batches of 80 —
each subprocess spawns a fresh HTTP session with zero accumulated tokens.
"""
import os
import sys
import json
import logging
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import RELOCATION_KEYWORDS, MIN_SCORE_TO_INCLUDE, KNOWN_RELOCATORS

logger = logging.getLogger(__name__)

BATCH_SIZE = 40   # jobs per subprocess — small batches run in parallel
MAX_PARALLEL = 7  # max concurrent subprocesses

# Title must contain at least one of these to be worth scoring
TITLE_MUST_INCLUDE = {
    "cloud", "security", "devops", "devsecops", "platform", "kubernetes",
    "k8s", "sre", "reliability", "infrastructure", "infra", "architect",
    "engineer", "automation", "aws", "azure", "gcp",
}

# If title contains any of these it is immediately discarded
TITLE_JUNK = {
    "junior", "intern", "internship", "trainee", "werkstudent", "praktikant",
    "sales", "account executive", "marketing", "hr ", "human resources",
    "recruiter", "finance", "legal", "copywriter", "designer", "product manager",
    "scrum master", "project manager", "it-workplace", "workplace engineer",
    "support engineer", "helpdesk", "1st line", "2nd line",
}

SCORE_PROMPT = """Score this job for: Senior Cloud Security Engineer, 6yr, AWS/Azure/GCP, Kubernetes/EKS/AKS, Cilium/eBPF, Falco, Wiz CNAPP, DevSecOps, ArgoCD, Terraform, Pulumi, GDPR/NIS2, Go/Python. Cairo→EU relocation.

Job: {title} @ {company} ({country})
{description}

Return ONLY JSON: {{"score":<0-100>,"reasons":["r1","r2"],"missing":["g1"]}}
85+=perfect,70+=strong,55+=decent,<55=poor. Max 2 reasons, 1 gap."""

COVER_LETTER_PROMPT = """Write 2 paragraphs (3 lines each) as Mohamed ElBeltagy applying for {title} at {company}, {location}.
Mohamed: Senior Cloud Security Engineer, 6yr AWS/K8s/Wiz/DevSecOps, Cairo→EU.
Job context: {description}
Para 1: why THIS company+role excites him, what he brings.
Para 2: 2 matching technical strengths + interest closing.
No "I am writing to apply", no signature, plain text."""


# ── Subprocess worker script ──────────────────────────────────────────────────
# This runs inside each batch subprocess — fresh process = fresh API session
_WORKER_SCRIPT = """
import os, sys, json
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

MODEL = os.environ.get("AZURE_AI_MODEL", "DeepSeek-V3.2")
client = OpenAI(
    api_key=os.environ["AZURE_AI_API_KEY"],
    base_url=os.environ["AZURE_AI_ENDPOINT"].rstrip("/") + "/openai/v1/",
)

SCORE_PROMPT = {score_prompt!r}
COVER_PROMPT = {cover_prompt!r}
THRESHOLD = {threshold}

jobs = json.loads(sys.stdin.read())
results = []

for job in jobs:
    # Score
    try:
        resp = client.chat.completions.create(
            model=MODEL, max_tokens=200, temperature=0.1,
            messages=[{{"role":"user","content":SCORE_PROMPT.format(
                title=job.get("title",""),
                company=job.get("company",""),
                country=job.get("country",""),
                description=job.get("description","")[:600],
            )}}]
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
        result = json.loads(raw.strip())
    except Exception as e:
        result = {{"score":0,"reasons":[],"missing":["error"]}}

    score = result.get("score", 0)
    if score < THRESHOLD:
        results.append(None)
        continue

    # Cover letter for passing jobs
    try:
        cl_resp = client.chat.completions.create(
            model=MODEL, max_tokens=280, temperature=0.7,
            messages=[{{"role":"user","content":COVER_PROMPT.format(
                title=job.get("title",""),
                company=job.get("company",""),
                location=job.get("location",""),
                description=job.get("description","")[:500],
            )}}]
        )
        cover_letter = cl_resp.choices[0].message.content.strip()
    except Exception:
        cover_letter = ""

    results.append({{
        **job,
        "score": score,
        "reasons": result.get("reasons", []),
        "missing": result.get("missing", []),
        "cover_letter": cover_letter,
    }})

print(json.dumps(results))
"""


def is_relevant_title(job: dict) -> bool:
    """Quick pre-filter — skip obvious junk before hitting the AI."""
    title = job.get("title", "").lower()
    if any(junk in title for junk in TITLE_JUNK):
        return False
    return any(kw in title for kw in TITLE_MUST_INCLUDE)


def detect_relocation(job: dict) -> bool:
    text = (job.get("description", "") + " " + job.get("title", "")).lower()
    return any(kw in text for kw in RELOCATION_KEYWORDS)


def detect_known_relocator(job: dict) -> bool:
    company = job.get("company", "").lower()
    return any(name in company for name in KNOWN_RELOCATORS)


def _score_batch(batch: list[dict]) -> list[dict]:
    """
    Score one batch of jobs in a fresh subprocess.
    Fresh process = fresh HTTP session = zero accumulated tokens.
    """
    script = _WORKER_SCRIPT.format(
        score_prompt=SCORE_PROMPT,
        cover_prompt=COVER_LETTER_PROMPT,
        threshold=MIN_SCORE_TO_INCLUDE,
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        script_path = f.name

    try:
        proc = subprocess.run(
            [sys.executable, script_path],
            input=json.dumps(batch),
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ},
        )
        if proc.returncode != 0:
            logger.error(f"Batch subprocess failed: {proc.stderr[:500]}")
            return []
        results = json.loads(proc.stdout)
        return [r for r in results if r is not None]
    except subprocess.TimeoutExpired:
        logger.error("Batch subprocess timed out after 300s")
        return []
    except Exception as e:
        logger.error(f"Batch subprocess error: {e}")
        return []
    finally:
        os.unlink(script_path)


def enrich_jobs(jobs: list[dict]) -> list[dict]:
    """
    Score all jobs using parallel subprocesses (batch size 40, up to 7 concurrent).
    Each subprocess gets a fresh API session — no 128k token limit accumulation.
    Wall-clock time = time of the slowest single batch (~3 min) instead of sum.
    """
    # Pre-filter junk titles
    relevant = [j for j in jobs if is_relevant_title(j)]
    skipped = len(jobs) - len(relevant)
    if skipped:
        logger.info(f"Pre-filter: skipped {skipped} irrelevant, scoring {len(relevant)}/{len(jobs)}")

    batches = [relevant[i:i+BATCH_SIZE] for i in range(0, len(relevant), BATCH_SIZE)]
    logger.info(f"Scoring {len(relevant)} jobs in {len(batches)} parallel batches of {BATCH_SIZE}")

    enriched = []

    # Launch all batches concurrently, cap at MAX_PARALLEL simultaneous processes
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL) as executor:
        future_to_batch = {
            executor.submit(_score_batch, batch): (i + 1, len(batch))
            for i, batch in enumerate(batches)
        }
        for future in as_completed(future_to_batch):
            batch_num, batch_size = future_to_batch[future]
            try:
                results = future.result()
                for r in results:
                    enriched.append({
                        **r,
                        "relocation":      detect_relocation(r),
                        "known_relocator": detect_known_relocator(r),
                    })
                logger.info(f"Batch {batch_num} done: {len(results)}/{batch_size} passed threshold")
            except Exception as e:
                logger.error(f"Batch {batch_num} failed: {e}")

    enriched.sort(key=lambda j: j["score"], reverse=True)
    logger.info(f"Scoring done: {len(enriched)}/{len(jobs)} passed {MIN_SCORE_TO_INCLUDE}% threshold")
    return enriched
