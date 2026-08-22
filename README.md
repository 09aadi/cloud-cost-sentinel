# cloud-cost-sentinel

A multi-cloud cost anomaly detection service. Ingests billing data, tracks daily spend history, and flags unusual cost spikes before they become a surprise invoice -- built as a hands-on infrastructure project covering the full path from local development to a cross-cloud, GitOps-deployed Kubernetes platform.

> **Status: actively under development.** This README reflects the current state honestly and is updated as each phase lands -- nothing below is claimed as done unless it's checked off.

## Why this exists

Cost governance is a real, everyday DevOps concern -- not a common portfolio project. Most infra-learning projects (URL shorteners, todo APIs) optimize for simplicity and skip the part where you actually reason about spend, thresholds, and what "anomalous" even means for a given account. This project exists to build and demonstrate that reasoning end-to-end, on real multi-cloud infrastructure, not just the application code.

## Architecture

```
   client ---> [ FastAPI (API) ] ---> PostgreSQL
                      |                (accounts, cost
                      v                 history, anomalies)
                [ Redis ]  (cached cost summaries)
                      ^
                      |
                [ Worker ]  ---> Billing data source
                (scheduled          (mock data locally;
                 ingestion +         real Cost Explorer /
                 anomaly              GCP Billing export
                 detection)           as a stretch goal)
```

## Current state (updated as work lands)

Built and tested so far:
- `CloudAccount` and `CostRecord` models, related via foreign key
- `POST /accounts`, `GET /accounts` — create and list tracked cloud accounts
- `POST /accounts/{account_id}/cost-records` — ingest a cost record for an account, with a 404 guard for unknown accounts
- `GET /accounts/{account_id}/cost-records` — list an account's cost history
- Mass-assignment protection verified (clients cannot inject `id` or `created_at`)
- Cross-account data isolation verified (a real bug was caught here during testing — see Project log)

Not yet built: anomaly detection, scheduled ingestion, Redis caching, containerization, all infrastructure/deployment items below.

## Planned feature set

- [x] Register and manage tracked cloud accounts (AWS / GCP / Azure)
- [x] Manual cost-record ingestion via API
- [x] Historical cost trends via API (per-account cost record history)
- [ ] Scheduled ingestion of daily billing data per account
- [ ] Anomaly detection on spend (rolling average / day-over-day threshold)
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
docker run --name pg-local -e POSTGRES_PASSWORD=yourpassword \
  -e POSTGRES_DB=cloudcostsentinel -p 5432:5432 \
  -v pg-data:/var/lib/postgresql/data -d postgres:16
# note: if your password contains special characters (@, :, /, #, ?),
# URL-encode them in DATABASE_URL in .env (e.g. @ becomes %40) --
# raw special characters break connection-string parsing.

# run the API
uvicorn app.main:app --reload
```

## Project log

This project is built in public as part of a structured DevOps learning plan, including deliberately diagnosed failures along the way rather than only polished happy-path commits.

**Cross-account data isolation bug (caught in testing).** The initial `GET /accounts/{account_id}/cost-records` implementation correctly checked that the requested account existed, but the actual database query never filtered by `account_id` -- it returned every cost record in the table, regardless of which account was requested. Caught by testing the endpoint against an account that genuinely had records and noticing the response included rows belonging to a different account. Fixed by adding `.filter(CostRecord.cloud_account_id == account_id)` to the query, and re-verified against the original account that had leaked data, not just a fresh one.

**Connection string parsing failure from an unescaped special character.** A Postgres password containing `@` broke `DATABASE_URL` parsing -- the parser split on the password's own `@` instead of the one separating credentials from host, producing a nonsensical hostname and a `could not translate host name` error. Fixed by URL-encoding the password (`%40` for `@`).

## License

MIT