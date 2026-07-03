# email_digest/renderer.py
"""
Renders the job digest HTML email using Jinja2 templates.
Groups jobs by country and sorts each group by score descending.
"""
from collections import defaultdict
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from config import MIN_SCORE_TO_INCLUDE

TEMPLATE_DIR = Path(__file__).parent / "templates"

_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)


def render_digest(jobs: list[dict], run_date: str) -> str:
    """
    Render the HTML email digest.

    Args:
        jobs:     Enriched job dicts with score, reasons, missing, relocation fields
        run_date: Human-readable date string for the email header (e.g. "2026-06-21")

    Returns:
        HTML string ready to send as email body.
    """
    # Group by country, preserving score-sort within each group
    grouped: dict[str, list] = defaultdict(list)
    for job in sorted(jobs, key=lambda j: j["score"], reverse=True):
        grouped[job["country"]].append(job)

    # Sort countries by their top job score (best-match countries first)
    sorted_grouped = dict(
        sorted(grouped.items(), key=lambda kv: kv[1][0]["score"], reverse=True)
    )

    template = _jinja_env.get_template("digest.html.j2")
    return template.render(
        run_date=run_date,
        grouped=sorted_grouped,
        countries=list(sorted_grouped.keys()),
        total_jobs=len(jobs),
        min_score=MIN_SCORE_TO_INCLUDE,
    )
