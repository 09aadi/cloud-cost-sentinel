# cloud-cost-sentinel

A multi-cloud cost anomaly detection service. Ingests billing data, tracks daily spend history, and flags unusual cost spikes before they become a surprise invoice — built as a hands-on infrastructure project covering the full path from local development to a cross-cloud, GitOps-deployed Kubernetes platform.

> 🚧 **Status: actively under development.** This README reflects the current state honestly and is updated as each phase lands — nothing below is claimed as done unless it's checked off.

## Why this exists

Cost governance is a real, everyday DevOps concern — not a common portfolio project. Most infra-learning projects (URL shorteners, todo APIs) optimize for simplicity and skip the part where you actually reason about spend, thresholds, and what "anomalous" even means for a given account. This project exists to build and demonstrate that reasoning end-to-end, on real multi-cloud infrastructure, not just the application code.

## Architecture

```
                 ┌──────────────┐
   client ──────▶│   FastAPI    │──────▶  PostgreSQL
                 │   (API)      │         (accounts, cost
                 └──────┬───────┘          history, anomalies)
                        │
                        ▼
                 ┌──────────────┐
                 │    Redis     │  (cached cost summaries)
                 └──────────────┘
                        ▲
                        │
                 ┌──────────────┐
                 │  Worker      │──────▶  Billing data source
                 │  (scheduled  │         (mock data locally;
                 │  ingestion + │         real Cost Explorer /
                 │  anomaly     │         GCP Billing export
                 │  detection)  │         as a stretch goal)
                 └──────────────┘
```

## Planned feature set

- [ ] Register and manage tracked cloud accounts (AWS / GCP / Azure)
- [ ] Scheduled ingestion of daily billing data per account
- [ ] Anomaly detection on spend (rolling average / day-over-day threshold)
- [ ] Historical cost trends via API
- [ ] Cached cost summaries for fast dashboard reads
- [ ] Containerized (Docker), deployed to both AWS EKS and GCP GKE
- [ ] Real cross-cloud connectivity between the AWS and GCP legs (VPN/peering), not isolated parallel deployments
- [ ] Infrastructure provisioned via modular Terraform with remote state
- [ ] CI/CD via GitHub Actions, with Trivy/Checkov scanning gating releases
- [ ] GitOps delivery via Helm + ArgoCD
- [ ] Observability via Prometheus + Grafana, with alerting on ingestion failures and detected anomalies
- [ ] Secrets management via cloud-native secret stores (no plaintext credentials, ever)
- [ ] Azure added as a third leg once integrated (stretch goal)

## Tech stack

**Application:** Python, FastAPI, SQLAlchemy, Pydantic
**Data:** PostgreSQL, Redis
**Infrastructure:** Docker, Terraform, AWS EKS, GCP GKE
**Delivery:** GitHub Actions, Helm, ArgoCD
**Observability:** Prometheus, Grafana

## Local development

```bash
# clone and enter the repo
git clone <repo-url>
cd cloud-cost-sentinel

# create and activate a virtual environment
python -m venv venv
source venv/Scripts/activate   # Git Bash on Windows

# install dependencies
pip install -r requirements.txt

# start local Postgres (via Docker)
docker run --name pg-local -e POSTGRES_PASSWORD=devpassword \
  -e POSTGRES_DB=cloudcostsentinel -p 5432:5432 -d postgres:16

# run the API
uvicorn app.main:app --reload
```

## Project log

This project is built in public as part of a structured DevOps learning plan, including deliberately diagnosed failures along the way rather than only polished happy-path commits. Notable issues hit and fixed will be documented here as they happen.

## License

MIT
