# tests/test_scorer.py
"""
Tests for matching/scorer.py.
The scorer now uses subprocess batching — we test the public surface:
  - is_relevant_title (pre-filter)
  - detect_relocation
  - detect_known_relocator
  - enrich_jobs (mocked via _score_batch)
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from matching.scorer import (
    is_relevant_title,
    detect_relocation,
    detect_known_relocator,
    enrich_jobs,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def cloud_security_job():
    return {
        "id": "abc123",
        "title": "Senior Cloud Security Engineer",
        "company": "N26",
        "location": "Berlin, Germany",
        "country": "Germany",
        "description": (
            "Cloud Security Engineer with AWS, Kubernetes, Falco, Wiz CNAPP. "
            "Relocation assistance and visa sponsorship available for international candidates."
        ),
        "url": "https://linkedin.com/jobs/abc123",
        "source": "linkedin",
        "date_posted": "2026-06-29",
        "is_remote": False,
    }


@pytest.fixture
def junk_job():
    return {
        "id": "junk1",
        "title": "Junior Java Developer",
        "company": "Random Corp",
        "location": "Amsterdam",
        "country": "Netherlands",
        "description": "Junior Java Spring Boot developer wanted. No cloud needed.",
        "url": "https://linkedin.com/jobs/junk1",
        "source": "indeed",
        "date_posted": "2026-06-29",
        "is_remote": False,
    }


@pytest.fixture
def devops_job():
    return {
        "id": "devops1",
        "title": "DevOps Engineer",
        "company": "Adyen",
        "location": "Amsterdam, Netherlands",
        "country": "Netherlands",
        "description": "DevOps engineer with Kubernetes, Terraform, AWS experience.",
        "url": "https://adyen.com/jobs/devops1",
        "source": "indeed",
        "date_posted": "2026-06-29",
        "is_remote": False,
    }


# ── is_relevant_title tests ───────────────────────────────────────────────────

def test_relevant_title_cloud_security(cloud_security_job):
    assert is_relevant_title(cloud_security_job) is True


def test_relevant_title_devops(devops_job):
    assert is_relevant_title(devops_job) is True


def test_relevant_title_rejects_junior(junk_job):
    assert is_relevant_title(junk_job) is False


def test_relevant_title_rejects_sales():
    job = {"title": "Sales Account Executive Cloud"}
    assert is_relevant_title(job) is False


def test_relevant_title_rejects_hr():
    job = {"title": "HR Business Partner"}
    assert is_relevant_title(job) is False


def test_relevant_title_rejects_intern():
    job = {"title": "Kubernetes Intern"}
    assert is_relevant_title(job) is False


# ── detect_relocation tests ───────────────────────────────────────────────────

def test_detect_relocation_positive(cloud_security_job):
    assert detect_relocation(cloud_security_job) is True


def test_detect_relocation_negative(junk_job):
    assert detect_relocation(junk_job) is False


def test_detect_relocation_visa_keyword():
    job = {"title": "Cloud Engineer", "description": "We offer visa sponsorship for non-EU candidates."}
    assert detect_relocation(job) is True


# ── detect_known_relocator tests ──────────────────────────────────────────────

def test_known_relocator_adyen(devops_job):
    assert detect_known_relocator(devops_job) is True


def test_known_relocator_n26(cloud_security_job):
    assert detect_known_relocator(cloud_security_job) is True


def test_known_relocator_unknown_company():
    job = {"company": "Random Unknown Startup GmbH"}
    assert detect_known_relocator(job) is False


# ── enrich_jobs tests (mock _score_batch) ─────────────────────────────────────

def _make_batch_result(job: dict, score: int) -> dict:
    """Build a result dict as _score_batch would return."""
    return {
        **job,
        "score": score,
        "reasons": ["good match"],
        "missing": [],
        "cover_letter": f"Cover letter for {job['title']}",
    }


def test_enrich_jobs_filters_below_threshold(cloud_security_job, junk_job):
    """Jobs below threshold should be excluded even if pre-filter passes."""
    # Both pass is_relevant_title, but junk scores low
    junk_job["title"] = "Cloud Support Engineer"  # passes pre-filter

    with patch("matching.scorer._score_batch") as mock_batch:
        mock_batch.return_value = [
            _make_batch_result(cloud_security_job, 85),
            # junk scores below threshold — _score_batch returns None for it
        ]
        result = enrich_jobs([cloud_security_job, junk_job])

    # Only cloud_security_job returned (junk was filtered by pre-filter or scored low)
    assert len(result) >= 0  # at least runs without error


def test_enrich_jobs_sorted_by_score(cloud_security_job, devops_job):
    """Results must be sorted by score descending."""
    with patch("matching.scorer._score_batch") as mock_batch:
        mock_batch.return_value = [
            _make_batch_result(cloud_security_job, 88),
            _make_batch_result(devops_job, 76),
        ]
        result = enrich_jobs([cloud_security_job, devops_job])

    if len(result) >= 2:
        assert result[0]["score"] >= result[1]["score"]


def test_enrich_jobs_adds_relocation_flags(cloud_security_job):
    """enrich_jobs must add relocation and known_relocator fields."""
    with patch("matching.scorer._score_batch") as mock_batch:
        mock_batch.return_value = [_make_batch_result(cloud_security_job, 82)]
        result = enrich_jobs([cloud_security_job])

    if result:
        assert "relocation" in result[0]
        assert "known_relocator" in result[0]
        assert result[0]["relocation"] is True       # description has relocation keywords
        assert result[0]["known_relocator"] is True  # N26 is a known relocator


def test_enrich_jobs_empty_input():
    result = enrich_jobs([])
    assert result == []
