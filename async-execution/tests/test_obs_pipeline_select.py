from __future__ import annotations

from app.contracts import JobRecord, JobStatus
from app.worker import _uses_observability_pipeline


def _job(metadata: dict[str, str]) -> JobRecord:
    return JobRecord(
        job_id="job_test",
        tenant_id="tenant_acme",
        user_id="user_42",
        idempotency_key="k",
        request_hash="h",
        payload={"prompt": "status of ORD-1001?", "thread_id": "t1", "metadata": metadata},
        status=JobStatus.QUEUED,
        attempts=0,
        max_attempts=3,
        checkpoint_index=0,
        cancel_requested=False,
        next_retry_delay=None,
        result=None,
        error=None,
        version=1,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def test_observability_pipeline_selected_by_scenario_metadata():
    assert _uses_observability_pipeline(_job({"obs_scenario": "correct"})) is True


def test_observability_pipeline_selected_by_pipeline_flag():
    assert _uses_observability_pipeline(_job({"pipeline": "observability"})) is True


def test_default_pipeline_unchanged():
    assert _uses_observability_pipeline(_job({"contact_preference": "email"})) is False
