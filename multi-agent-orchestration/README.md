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

Do not run this stack and the instructor stack on the same ports. This project is `july-sunday-learner`.

## Labs

The two gates in `tests/test_labs.py` only check your functions. They do not start a case or call OpenAI.

```bash
docker compose exec -T api python -m unittest discover -s tests -p test_labs.py -k test_01 -v
docker compose exec -T api python -m unittest discover -s tests -p test_labs.py -v
```

## Run a case

```bash
docker compose exec -T api python -m app.team new risk_timeout
CID="paste-uuid"
docker compose exec -T api python -m app.team run "$CID" --backend fixture
docker compose exec -T api python -m app.team show "$CID"
```

`conflict` should finish BLOCKED. Do not submit that case.

## Approve

Use a READY case.

```bash
docker compose exec -T api python -m app.team submit "$CID" --seconds 600
WID="paste-uuid"
docker compose exec -T -e API_URL=http://localhost:8000 api python -m app.cli show "$WID"
docker compose exec -T -e API_URL=http://localhost:8000 api python -m app.cli approve "$WID" --role finance_manager --reason "Checked INR 18000 and specialist evidence"
docker compose exec -T -e API_URL=http://localhost:8000 api python -m app.cli wait "$WID"
```

## Live OpenAI (optional)

Put `OPENAI_API_KEY` in `.env`, then `docker compose up -d`.

```bash
docker compose exec -T api python -m app.team new healthy
CID="paste-uuid"
docker compose exec -T api python -m app.team run "$CID" --backend openai --timeout 90
```

Keep `--backend fixture` for timeout and conflict drills.

## Stop

```bash
docker compose stop
```
