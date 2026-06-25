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
        "location": "Berlin, Germany",
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
        "location": "Amsterdam, Netherlands",
        "description": "Looking for Java developer with Spring Boot experience. No cloud needed.",
        "country": "Netherlands",
    }


def _mock_completion(content: str) -> MagicMock:
    """Build a mock OpenAI chat completion response."""
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    return response


def test_detect_relocation_positive(cloud_security_job):
    assert detect_relocation(cloud_security_job) is True


def test_detect_relocation_negative(unrelated_job):
    assert detect_relocation(unrelated_job) is False


def test_score_job_returns_valid_structure(cloud_security_job):
    mock_resp = _mock_completion(json.dumps({
        "score": 88,
        "reasons": ["Matches Kubernetes security", "AWS experience", "Wiz CNAPP mentioned"],
        "missing": ["No SPIFFE/SPIRE mention"],
    }))
    with patch("matching.scorer._get_client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = mock_resp
        result = score_job(cloud_security_job)

    assert "score" in result
    assert "reasons" in result
    assert "missing" in result
    assert 0 <= result["score"] <= 100
    assert isinstance(result["reasons"], list)


def test_score_job_handles_invalid_json(cloud_security_job):
    mock_resp = _mock_completion("not valid json at all")
    with patch("matching.scorer._get_client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = mock_resp
        result = score_job(cloud_security_job)

    assert result["score"] == 0
    assert "parse error" in result["missing"]


def test_score_job_handles_api_error(cloud_security_job):
    with patch("matching.scorer._get_client") as mock_client:
        mock_client.return_value.chat.completions.create.side_effect = Exception("API down")
        result = score_job(cloud_security_job)

    assert result["score"] == 0
    assert "api error" in result["missing"]


def test_enrich_jobs_filters_low_scores(cloud_security_job, unrelated_job):
    # job1 scores 90 → passes → gets cover letter call
    # job2 scores 20 → filtered out → no cover letter call
    responses = [
        _mock_completion(json.dumps({"score": 90, "reasons": ["great match"], "missing": []})),
        _mock_completion("Cover letter for cloud security job"),
        _mock_completion(json.dumps({"score": 20, "reasons": ["poor match"], "missing": ["everything"]})),
    ]

    with patch("matching.scorer._get_client") as mock_client:
        mock_client.return_value.chat.completions.create.side_effect = responses
        result = enrich_jobs([cloud_security_job, unrelated_job])

    assert len(result) == 1
    assert result[0]["id"] == "abc123"
    assert result[0]["score"] == 90


def test_enrich_jobs_sorted_by_score(cloud_security_job, unrelated_job):
    # score job1=85, cover letter job1, score job2=72, cover letter job2
    # (enrich_jobs scores then immediately generates cover letter per job)
    responses = [
        _mock_completion(json.dumps({"score": 85, "reasons": ["strong"], "missing": []})),
        _mock_completion("Cover letter for job 1"),
        _mock_completion(json.dumps({"score": 72, "reasons": ["decent"], "missing": []})),
        _mock_completion("Cover letter for job 2"),
    ]

    with patch("matching.scorer._get_client") as mock_client:
        mock_client.return_value.chat.completions.create.side_effect = responses
        result = enrich_jobs([cloud_security_job, unrelated_job])

    assert len(result) == 2
    assert result[0]["score"] >= result[1]["score"]
