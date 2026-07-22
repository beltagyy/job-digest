# tests/test_run.py
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Set required env vars before any imports
os.environ["RESEND_API_KEY"] = "test-key"
os.environ["DIGEST_TO_EMAIL"] = "test@example.com"
os.environ["ANTHROPIC_API_KEY"] = "test-anthropic-key"

# Stub heavy external deps before run.py imports them
_stubs = {}
for _m in ["jobspy", "jobspy.scrape_jobs", "xing", "anthropic",
           "scrapers.jobspy_scraper", "scrapers.xing_scraper", "scrapers.yej_scraper"]:
    _stubs[_m] = MagicMock()
sys.modules.update(_stubs)

import run as run_mod


@pytest.fixture(autouse=True)
def ensure_env():
    yield
    for key in ["RESEND_API_KEY", "DIGEST_TO_EMAIL", "ANTHROPIC_API_KEY"]:
        os.environ.pop(key, None)


SAMPLE_JOBS = [
    {
        "id": "abc123", "title": "Cloud Engineer", "company": "TestCorp",
        "location": "Berlin, Germany", "country_code": "DE", "country": "Germany",
        "url": "https://example.com/1", "source": "linkedin",
        "description": "Cloud engineering role.", "date_posted": "2026-07-20",
        "is_remote": False,
    },
]


@patch.object(run_mod, "send_digest", return_value=True)
@patch.object(run_mod, "render_digest", return_value="<html>digest</html>")
@patch.object(run_mod, "enrich_jobs", return_value=[{**SAMPLE_JOBS[0], "score": 90, "reasons": [], "missing": [], "relocation": False}])
@patch.object(run_mod, "JobDatabase")
@patch.object(run_mod, "fetch_xing", return_value=[])
@patch.object(run_mod, "fetch_jobspy", return_value=SAMPLE_JOBS)
def test_full_run(mock_jobspy, mock_xing, mock_db_cls, mock_enrich, mock_render, mock_send):
    mock_db = MagicMock()
    mock_db.filter_new.return_value = SAMPLE_JOBS
    mock_db_cls.return_value = mock_db

    with patch("sys.argv", ["run.py"]):
        run_mod.main()

    mock_enrich.assert_called_once()
    mock_render.assert_called_once()
    mock_send.assert_called_once()


@patch.object(run_mod, "send_digest", return_value=True)
@patch.object(run_mod, "render_digest", return_value="<html>dry</html>")
@patch.object(run_mod, "enrich_jobs", return_value=[])
@patch.object(run_mod, "JobDatabase")
@patch.object(run_mod, "fetch_xing", return_value=[])
@patch.object(run_mod, "fetch_jobspy", return_value=SAMPLE_JOBS)
def test_dry_run(mock_jobspy, mock_xing, mock_db_cls, mock_enrich, mock_render, mock_send):
    mock_db = MagicMock()
    mock_db.filter_new.return_value = SAMPLE_JOBS
    mock_db_cls.return_value = mock_db

    with patch("sys.argv", ["run.py", "--dry-run"]):
        run_mod.main()

    mock_render.assert_called_once()
    mock_send.assert_not_called()


@patch.object(run_mod, "send_digest", return_value=True)
@patch.object(run_mod, "render_digest", return_value="<html></html>")
@patch.object(run_mod, "enrich_jobs", return_value=[])
@patch.object(run_mod, "JobDatabase")
@patch.object(run_mod, "fetch_xing")
@patch.object(run_mod, "fetch_jobspy", return_value=[])
def test_no_xing_flag(mock_jobspy, mock_xing, mock_db_cls, mock_enrich, mock_render, mock_send):
    mock_db = MagicMock()
    mock_db.filter_new.return_value = []
    mock_db_cls.return_value = mock_db

    with patch("sys.argv", ["run.py", "--no-xing"]):
        run_mod.main()

    mock_xing.assert_not_called()


@patch.object(run_mod, "send_digest", return_value=False)
@patch.object(run_mod, "render_digest", return_value="<html>fail</html>")
@patch.object(run_mod, "enrich_jobs", return_value=[{**SAMPLE_JOBS[0], "score": 90, "reasons": [], "missing": [], "relocation": False}])
@patch.object(run_mod, "JobDatabase")
@patch.object(run_mod, "fetch_xing", return_value=[])
@patch.object(run_mod, "fetch_jobspy", return_value=SAMPLE_JOBS)
def test_send_failure_exits(mock_jobspy, mock_xing, mock_db_cls, mock_enrich, mock_render, mock_send):
    mock_db = MagicMock()
    mock_db.filter_new.return_value = SAMPLE_JOBS
    mock_db_cls.return_value = mock_db

    with patch("sys.argv", ["run.py"]):
        with pytest.raises(SystemExit) as exc_info:
            run_mod.main()
        assert exc_info.value.code == 1


@patch.object(run_mod, "send_digest", return_value=True)
@patch.object(run_mod, "render_digest", return_value="<html>empty</html>")
@patch.object(run_mod, "enrich_jobs", return_value=[])
@patch.object(run_mod, "JobDatabase")
@patch.object(run_mod, "fetch_xing", return_value=[])
@patch.object(run_mod, "fetch_jobspy", return_value=[])
def test_empty_jobs(mock_jobspy, mock_xing, mock_db_cls, mock_enrich, mock_render, mock_send):
    mock_db = MagicMock()
    mock_db.filter_new.return_value = []
    mock_db_cls.return_value = mock_db

    with patch("sys.argv", ["run.py", "--dry-run"]):
        run_mod.main()

    mock_enrich.assert_not_called()
