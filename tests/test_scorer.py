# tests/test_scorer.py
import json
import pytest
from unittest.mock import patch, MagicMock
from matching.scorer import score_job, detect_relocation, enrich_jobs


@pytest.fixture
def cloud_security_job():
    return {
        "id": "abc123",
        "title": "Senior Cloud Security Engineer",
        "company": "SAP",
        "description": (
            "We need a Senior Cloud Security Engineer with deep AWS, Kubernetes EKS, "
            "Falco, Wiz CNAPP, and Terraform experience. DevSecOps background required. "
            "Relocation assistance available for international candidates."
        ),
        "country": "Germany",
    }


@pytest.fixture
def unrelated_job():
    return {
        "id": "def456",
        "title": "Java Spring Boot Developer",
        "company": "Random Corp",
        "description": "Looking for Java developer with Spring Boot experience. No cloud needed.",
        "country": "Netherlands",
    }


def test_detect_relocation_positive(cloud_security_job):
    assert detect_relocation(cloud_security_job) is True


def test_detect_relocation_negative(unrelated_job):
    assert detect_relocation(unrelated_job) is False


def test_score_job_returns_valid_structure(cloud_security_job):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps({
        "score": 88,
        "reasons": ["Matches Kubernetes security", "AWS experience", "Wiz CNAPP mentioned"],
        "missing": ["No SPIFFE/SPIRE mention"],
    }))]
    with patch("matching.scorer.anthropic_client.messages.create", return_value=mock_response):
        result = score_job(cloud_security_job)
    assert "score" in result
    assert "reasons" in result
    assert "missing" in result
    assert 0 <= result["score"] <= 100


def test_enrich_jobs_filters_low_scores(cloud_security_job, unrelated_job):
    mock_high = MagicMock()
    mock_high.content = [MagicMock(text=json.dumps({"score": 90, "reasons": ["great"], "missing": []}))]
    mock_low = MagicMock()
    mock_low.content = [MagicMock(text=json.dumps({"score": 20, "reasons": ["poor"], "missing": ["everything"]}))]
    with patch("matching.scorer.anthropic_client.messages.create", side_effect=[mock_high, mock_low]):
        result = enrich_jobs([cloud_security_job, unrelated_job])
    assert len(result) == 1
    assert result[0]["id"] == "abc123"
