# tests/test_renderer.py
import pytest
from email_digest.renderer import render_digest


@pytest.fixture
def sample_jobs():
    return [
        {
            "id": "abc123", "title": "Senior Cloud Security Engineer", "company": "Deutsche Bank",
            "location": "Frankfurt, Germany", "country_code": "DE", "country": "Germany",
            "url": "https://linkedin.com/jobs/view/abc123", "source": "linkedin",
            "description": "Cloud security role with relocation assistance.",
            "date_posted": "2026-06-20", "is_remote": False,
            "score": 94, "reasons": ["AWS + K8s security match", "Wiz CNAPP", "GDPR compliance"],
            "missing": [], "relocation": True,
        },
        {
            "id": "ghi789", "title": "DevSecOps Engineer", "company": "N26",
            "location": "Berlin, Germany", "country_code": "DE", "country": "Germany",
            "url": "https://n26.com/jobs/ghi789", "source": "glassdoor",
            "description": "DevSecOps role with relocation support.",
            "date_posted": "2026-06-21", "is_remote": True,
            "score": 87, "reasons": ["DevSecOps match", "ArgoCD + Terraform"],
            "missing": ["Wiz CNAPP"], "relocation": True,
        },
    ]


def test_render_returns_html_string(sample_jobs):
    html = render_digest(sample_jobs, run_date="2026-06-21")
    assert isinstance(html, str)
    assert "<html" in html.lower()


def test_render_contains_job_titles(sample_jobs):
    html = render_digest(sample_jobs, run_date="2026-06-21")
    assert "Senior Cloud Security Engineer" in html
    assert "DevSecOps Engineer" in html


def test_render_shows_scores(sample_jobs):
    html = render_digest(sample_jobs, run_date="2026-06-21")
    assert "94" in html
    assert "87" in html


def test_render_shows_relocation_badge(sample_jobs):
    html = render_digest(sample_jobs, run_date="2026-06-21")
    assert "Relocation" in html


def test_render_groups_by_country(sample_jobs):
    html = render_digest(sample_jobs, run_date="2026-06-21")
    assert "Germany" in html


def test_render_empty_list():
    html = render_digest([], run_date="2026-06-21")
    assert "no new matches" in html.lower() or "0" in html
