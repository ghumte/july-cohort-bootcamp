```bash
docker compose up --build
curl -s http://localhost:8000/health/live
curl -s http://localhost:8000/health/ready

python scripts/demo_full_flow.py
```