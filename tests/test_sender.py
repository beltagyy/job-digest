# tests/test_sender.py
import os
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def set_env_vars():
    os.environ["RESEND_API_KEY"] = "test-key"
    os.environ["DIGEST_TO_EMAIL"] = "test@example.com"
    os.environ["DIGEST_FROM_EMAIL"] = "sender@example.com"
    yield
    os.environ.pop("RESEND_API_KEY", None)
    os.environ.pop("DIGEST_TO_EMAIL", None)
    os.environ.pop("DIGEST_FROM_EMAIL", None)


def _import_sender():
    import importlib
    import email_digest.sender as mod
    importlib.reload(mod)
    return mod


@patch("email_digest.sender.resend.Emails.send")
def test_send_digest_success(mock_send):
    mock_send.return_value = {"id": "msg_123"}
    sender = _import_sender()

    result = sender.send_digest("<h1>Test</h1>", job_count=5, run_date="2026-07-20")

    assert result is True
    mock_send.assert_called_once()
    call_args = mock_send.call_args[0][0]
    assert call_args["from"] == "sender@example.com"
    assert call_args["to"] == ["test@example.com"]
    assert "5 new matches" in call_args["subject"]
    assert "<h1>Test</h1>" in call_args["html"]


@patch("email_digest.sender.resend.Emails.send")
def test_send_digest_zero_jobs(mock_send):
    mock_send.return_value = {"id": "msg_456"}
    sender = _import_sender()

    result = sender.send_digest("<p>Empty</p>", job_count=0, run_date="2026-07-20")

    assert result is True
    call_args = mock_send.call_args[0][0]
    assert "no new matches" in call_args["subject"]


@patch("email_digest.sender.resend.Emails.send")
def test_send_digest_failure(mock_send):
    mock_send.side_effect = Exception("API error")
    sender = _import_sender()

    result = sender.send_digest("<h1>Test</h1>", job_count=3, run_date="2026-07-20")

    assert result is False


@patch("email_digest.sender.resend.Emails.send")
def test_send_digest_default_from_email(mock_send):
    mock_send.return_value = {"id": "msg_789"}
    os.environ.pop("DIGEST_FROM_EMAIL", None)
    sender = _import_sender()

    sender.send_digest("<p>Hi</p>", job_count=1, run_date="2026-07-20")

    call_args = mock_send.call_args[0][0]
    assert call_args["from"] == "onboarding@resend.dev"
