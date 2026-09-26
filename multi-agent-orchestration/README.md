# Learner lab

One INR 18,000 refund. You own two functions in `app/team_starter.py`.

- `collect_parallel` — start policy, order, and risk together; return `{role: result}`
- `supervise` — BLOCK wins; all CLEAR → READY; only risk missing on round 1 → FOLLOW_UP; else BLOCKED

READY means ask a human. It is not an approval and not a refund.

## Start

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec -T api python -m app.seed
```

UI: http://localhost:8098

```bash
docker compose exec -T db psql -U lab_admin -d enterprise -c '\d agent_cases'
docker compose exec -T db psql -U lab_admin -d enterprise -c '\d agent_tasks'
docker compose exec -T db psql -U lab_admin -d enterprise -c '\d agent_results'
docker compose exec -T db psql -U lab_admin -d enterprise -c '\d coordination_decisions'
```

## Labs

The two gates in `tests/test_labs.py` only check your functions. They do not start a case or call OpenAI.

```bash
docker compose exec -T api python -m app.team new healthy
CID='enter-case-id-from-above'
docker compose exec -T api python -m app.team run "$CID" --backend fixture

docker compose exec -T db psql -U lab_admin -d enterprise -c "
SELECT specialist, round_no, status, started_at, due_at
FROM agent_tasks
ORDER BY started_at DESC
LIMIT 8;
"


# Inspect the case

docker compose exec -T api python -m app.team show "$CID"

# Submit for Human approval

docker compose exec -T api python -m app.team submit "$CID" --seconds 600

# Approve 
WID='workflow-id-displayed-above'
docker compose exec -T -e API_URL=http://localhost:8000 api python -m app.cli approve "$WID" --role finance_manager --reason "Checked INR 18000 and specialist evidence"
```

## Run a case Risk Timeout

```bash
docker compose exec -T api python -m app.team new risk_timeout
CID="paste-uuid"
docker compose exec -T api python -m app.team run "$CID" --backend fixture
docker compose exec -T api python -m app.team show "$CID"

docker compose exec -T api python -m app.team submit "$CID" --seconds 600

docker compose exec -T api python -m app.cli show "$WID"
WID='noted-workflow-id-above'
#Stop the worker
docker compose stop worker
docker ps

docker compose exec -T -e API_URL=http://localhost:8000 api python -m app.cli approve "$WID" --role finance_manager --reason "Checked INR 18000 and specialist evidence"

docker compose start worker
docker compose exec -T api python -m app.cli wait "$WID"
```

## Run a case scheduler not available

```bash
docker compose stop scheduler
docker compose exec -T api python -m app.team new risk_timeout
CID="paste-uuid"
docker compose exec -T api python -m app.team run "$CID" --backend fixture
docker compose exec -T api python -m app.team show "$CID"

docker compose exec -T api python -m app.team submit "$CID" --seconds 120 --fault lost_response

docker compose exec -T api python -m app.cli show "$WID"
WID='noted-workflow-id-above'
#Stop the worker
docker compose stop worker
docker ps

docker compose exec -T -e API_URL=http://localhost:8000 api python -m app.cli approve "$WID" --role finance_manager --reason "Intentional Late Approval"
docker compose start scheduler
docker compose exec -T api python -m app.cli show "$WID"

docker compose exec -T api python -m app.cli approve "$WID" --role finance_director --reason "Escalated review against unchanged specialist-backed proposal"



docker compose start worker
docker compose exec -T api python -m app.cli wait "$WID"
```
