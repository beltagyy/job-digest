# tests/test_db.py
import pytest
import os
import tempfile
from storage.db import JobDatabase


@pytest.fixture
def tmp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    db = JobDatabase(path)
    yield db
    db.close()
    os.unlink(path)


def test_new_job_is_not_seen(tmp_db):
    assert tmp_db.is_seen("job-abc-123") is False


def test_mark_and_check_seen(tmp_db):
    tmp_db.mark_seen("job-abc-123")
    assert tmp_db.is_seen("job-abc-123") is True


def test_mark_seen_twice_does_not_raise(tmp_db):
    tmp_db.mark_seen("job-abc-123")
    tmp_db.mark_seen("job-abc-123")


def test_filter_new_jobs(tmp_db):
    tmp_db.mark_seen("old-job-1")
    jobs = [
        {"id": "old-job-1", "title": "Old"},
        {"id": "new-job-2", "title": "New"},
    ]
    result = tmp_db.filter_new(jobs)
    assert len(result) == 1
    assert result[0]["id"] == "new-job-2"


def test_mark_batch(tmp_db):
    jobs = [{"id": "j1"}, {"id": "j2"}, {"id": "j3"}]
    tmp_db.mark_seen_batch(jobs)
    assert tmp_db.is_seen("j1") is True
    assert tmp_db.is_seen("j2") is True
    assert tmp_db.is_seen("j3") is True
