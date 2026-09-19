"""Bridge: Session-Observability support-ops agent on the async-execution worker.

Selected when job metadata includes:
  pipeline=observability
  and/or obs_scenario=<FaultScenario value>

Real queue wait comes from Redis/Celery — this pipeline does not fake it.
"""

from __future__ import annotations

from typing import Any

from app.contracts import JobRecord
from app.errors import PermanentFailure, TransientFailure


class ObservabilityPipeline:
    """One durable worker step: run support-ops agent + quality/cost checks."""

    steps = ("support_ops",)

    def __init__(self) -> None:
        from obs_agent.agent import SupportOpsAgent
        from obs_agent.config import get_settings
        from obs_agent.tools import ToolGateway

        settings = get_settings(reload=True)
        self.settings = settings
        self.agent = SupportOpsAgent(
            settings=settings,
            gateway=ToolGateway(allow_demo_faults=settings.allow_demo_faults),
        )

    def run_step(self, job: JobRecord, step: str, prior: dict[str, Any]) -> dict[str, Any]:
        del prior  # single-step pipeline
        if step != "support_ops":
            raise PermanentFailure(f"unknown_obs_step:{step}")

        from obs_agent.contracts import FaultScenario, ToolCallRecord
        from obs_agent.cost import check_budgets, estimate_chat_cost_usd
        from obs_agent.quality import check_business_outcome, evaluate_answer, validate_output

        metadata = dict((job.payload or {}).get("metadata") or {})
        scenario_raw = metadata.get("obs_scenario", FaultScenario.CORRECT.value)
        try:
            scenario = FaultScenario(scenario_raw)
        except ValueError as exc:
            raise PermanentFailure(f"unknown_obs_scenario:{scenario_raw}") from exc

        question = str((job.payload or {}).get("prompt") or "")
        try:
            agent_out = self.agent.invoke(
                question=question,
                scenario=scenario,
                order_id=metadata.get("order_id"),
                tenant_id=job.tenant_id,
            )
        except Exception as exc:  # noqa: BLE001
            if "transient" in str(exc).lower() or "Transient" in type(exc).__name__:
                raise TransientFailure(str(exc)) from exc
            raise PermanentFailure(f"obs_agent:{exc}") from exc

        answer = str(agent_out.get("answer") or "")
        citations = list(agent_out.get("citations") or [])
        evidence = list(agent_out.get("evidence") or [])
        tool_calls = [
            ToolCallRecord.model_validate(tc) for tc in (agent_out.get("tool_calls") or [])
        ]
        validation = validate_output(
            answer=answer,
            citations=citations,
            tool_calls=tool_calls,
            require_citation=True,
        )
        grounded_ok, ground_failures, _note = evaluate_answer(answer=answer, evidence=evidence)
        business_ok = check_business_outcome(
            question=question,
            answer=answer,
            tool_calls=tool_calls,
            grounded=grounded_ok,
            validation_ok=validation.ok,
        )
        prompt_tokens = int(agent_out.get("prompt_tokens") or 0)
        completion_tokens = int(agent_out.get("completion_tokens") or 0)
        cost = estimate_chat_cost_usd(prompt_tokens, completion_tokens)
        budget_ok, budget_failures = check_budgets(
            step_count=len(agent_out.get("steps") or []),
            tool_call_count=len(tool_calls),
            estimated_cost_usd=cost,
            execution_ms=float(agent_out.get("model_latency_ms") or 0.0),
        )
        return {
            "step": "support_ops",
            "answer": answer,
            "validation": validation.model_dump(),
            "grounded": grounded_ok,
            "ground_failures": ground_failures,
            "business_success": business_ok,
            "budget_ok": budget_ok,
            "budget_failures": budget_failures,
            "estimated_cost_usd": cost,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "tool_calls": [tc.model_dump() for tc in tool_calls],
            "agent_steps": list(agent_out.get("steps") or []),
            "scenario": scenario.value,
            "provider": (
                f"langchain_openai:{self.settings.openai_model}"
                if self.settings.use_llm
                else "deterministic"
            ),
            "framework": "langgraph+async-execution",
            "errors": list(agent_out.get("errors") or []),
        }
