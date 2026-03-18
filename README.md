# Distributed Log Analytics Engine

A horizontally scalable system that ingests logs from multiple services via Kafka,
indexes them in Elasticsearch, and surfaces anomalies automatically using an ML pipeline.
Built as a portfolio project targeting Google SWE II.

## Live deployment
- **API:** https://log-analytics-api-m5tcor2tla-uc.a.run.app/health
- **Docs:** https://log-analytics-api-m5tcor2tla-uc.a.run.app/docs

## Architecture
```
Log Producers (Python)
       ↓
  Kafka Topics (logs.web-api, logs.auth-service, logs.payment-service)
       ↓
Python Async Consumers (aiokafka)
       ↓              ↓
Elasticsearch      Postgres
(search index)   (alerts, metadata)
       ↓              ↓
ML Pipeline (Isolation Forest anomaly detection)
       ↓
FastAPI Backend (REST + WebSocket)
       ↓
React Dashboard (live tail, search, service health)
```

## Performance benchmarks
| Metric | Result |
|--------|--------|
| Log ingestion throughput | 9,600+ logs/min |
| Logs indexed and searchable | 34,900+ |
| Search query latency | p95 < 100ms |
| ML anomaly recall | 0.86 |
| ML anomaly precision | 0.60 |
| Test coverage | 86% (101 tests) |

## Tech stack

| Layer | Technologies |
|-------|-------------|
| Ingestion | Apache Kafka, Avro Schema Registry, Python aiokafka |
| Storage | Elasticsearch 8, PostgreSQL 16, Redis 7 |
| ML | scikit-learn (Isolation Forest), pandas, MLflow |
| API | FastAPI, Pydantic v2, WebSockets |
| Frontend | React 18, TypeScript, Tailwind CSS, Recharts |
| Infrastructure | GCP (Cloud Run, Cloud SQL, Memorystore, Artifact Registry), Terraform |
| Testing | pytest, 101 tests, 86% coverage |

## Run locally
```bash
# Start all infrastructure
docker compose up -d

# Activate Python environment
source venv/bin/activate

# Terminal 1 — produce logs
python ingestion/producers/log_producer.py

# Terminal 2 — consume and index
python ingestion/consumers/log_consumer.py

# Terminal 3 — API server
uvicorn api.main:app --reload --port 8000

# Terminal 4 — ML anomaly detection
python -m ml.models.predict

# Terminal 5 — React dashboard
cd frontend && npm run dev
```

Open http://localhost:5173 for the dashboard.
Open http://localhost:8000/docs for the API docs.

## ML pipeline
```bash
# Train the Isolation Forest model
python -m ml.models.train

# Evaluate on golden dataset (500 windows)
python -m ml.evaluation.evaluate
# precision=0.60, recall=0.86, accuracy=0.93
```

## Run tests
```bash
pytest tests/ --cov=. -q
# 101 passed, 86% coverage
```

## Deploy to GCP
```bash
# Build and push Docker image
docker build --platform linux/amd64 -f api/Dockerfile \
  -t us-central1-docker.pkg.dev/log-analytics-engine/log-analytics/api:latest .
docker push us-central1-docker.pkg.dev/log-analytics-engine/log-analytics/api:latest

# Provision all infrastructure
cd infra && terraform apply
```

## Project structure
```
log-analytics-engine/
├── ingestion/          # Kafka producers and consumers
├── processing/         # Elasticsearch indexer
├── ml/                 # Feature engineering, training, inference
├── api/                # FastAPI backend
├── frontend/           # React dashboard
├── infra/              # Terraform (GCP)
├── tests/              # 101 tests, 86% coverage
└── docs/               # Design doc, postmortem, ADRs
```

## Design decisions
See [docs/design-doc-log-analytics.docx](docs/design-doc-log-analytics.docx) for the
full Google-style design document covering architecture choices, alternatives considered,
and open questions.

See [docs/adr/](docs/adr/) for Architecture Decision Records:
- ADR 001: Kafka over RabbitMQ
- ADR 002: Elasticsearch over ClickHouse
- ADR 003: Isolation Forest for anomaly detection