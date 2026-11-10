# cloud-cost-sentinel

A cloud cost anomaly detection service. It ingests daily billing records per cloud account, keeps the spend history, and flags days where spend jumps well above the recent average. It is built as a hands-on infrastructure project: the application is small on purpose, and the point is the path from local development to a Kubernetes cluster provisioned with Terraform on AWS.

> **Status: under active development.** This README says what exists today. Anything unchecked below is not built yet.

## Why this exists

Cost governance is an everyday DevOps concern, and most infra-learning projects (URL shorteners, todo APIs) skip it. This project reasons about spend, thresholds and what "anomalous" means for an account, and runs on real cloud infrastructure that is created and destroyed on demand to keep cost down.

## Architecture (current target)

```
   client ---> [ FastAPI ] ---> PostgreSQL   (accounts, cost records)
                   |
                   +--------> Redis         (cached cost summaries, 60s TTL)

   Infrastructure (Terraform, AWS us-east-1):
     VPC 10.0.0.0/16: 2 AZs, public + private subnets, one NAT gateway
     EKS 1.36: one managed node group (t3.medium, AL2023, x86_64)
     Remote state: S3 bucket + DynamoDB lock table (created separately)
```

The application is not deployed to the cluster yet. The cluster itself is provisioned, verified and destroyed (see the log below).

## What is built

**Application (`app/`)**
- `POST /accounts`, `GET /accounts`: register and list tracked cloud accounts
- `POST /accounts/{id}/cost-records`, `GET /accounts/{id}/cost-records`: ingest and list daily cost records, with a 404 for unknown accounts
- `GET /accounts/{id}/anomalies`: rolling-average anomaly detection (default: previous 7 records, flags a day more than 50% above that average), implemented in plain Python in `app/anomaly.py`
- `GET /accounts/{id}/summary`: total spend and record count, cached in Redis (cache-aside, 60 second TTL)
- Mass-assignment protection (clients cannot set `id` or `created_at`) and per-account data isolation were checked by hand during development

**Containers**
- `Dockerfile` (python:3.13-slim, runs as a non-root user)
- `docker-compose.yml` runs the API, PostgreSQL 16 and Redis 7. The API waits for the Postgres healthcheck (`service_healthy`) before starting.

**Infrastructure (`terraform/aws/`)**
- `bootstrap/`: S3 state bucket (versioned, `prevent_destroy`) and DynamoDB lock table. Applied once with local state; never destroyed.
- Root module: VPC (`terraform-aws-modules/vpc` ~> 5.0) and EKS (`terraform-aws-modules/eks` ~> 20.0) with the S3 backend. Provider lock file is committed with hashes for `linux_amd64` and `darwin_arm64`.
- A full apply -> verify -> destroy cycle has been run. Evidence: [`docs/evidence/2026-11-10-eks-apply-verify-destroy.md`](docs/evidence/2026-11-10-eks-apply-verify-destroy.md)

## Roadmap

- [x] Accounts and cost-record API with PostgreSQL
- [x] Anomaly detection endpoint
- [x] Redis-cached summaries
- [x] Containerised, with a local Compose stack
- [x] Remote Terraform state (S3 + DynamoDB locking)
- [x] VPC and EKS provisioned from Terraform, verified with `kubectl`, destroyed cleanly
- [x] `/health` (liveness) and `/ready` (database check) endpoints
- [ ] ECR repository applied, image built for `linux/amd64` and pushed (Terraform and `make image` written, not run yet)
- [ ] Helm chart deployed to EKS (chart written: probes, init-container startup ordering, secret kept out of git; not yet linted or deployed)
- [ ] CI with GitHub Actions: build, scan (Trivy, Checkov), push via OIDC (no stored AWS keys)
- [ ] GitOps delivery with ArgoCD
- [ ] Metrics and dashboards (Prometheus, Grafana)
- [ ] Scheduled ingestion of real billing data (currently records are posted by hand)
- [ ] Azure landing zone and AKS running the same chart (separate project)

## Local development

```bash
git clone https://github.com/09aadi/cloud-cost-sentinel
cd cloud-cost-sentinel

# Easiest: the whole stack in containers
docker compose up --build        # API on http://localhost:8000, docs at /docs
```

Running the API directly instead:

```bash
python3 -m venv venv
source venv/bin/activate         # Windows Git Bash: source venv/Scripts/activate
python -m pip install -r requirements.txt

# needs a .env with DATABASE_URL (and optionally REDIS_URL)
# URL-encode special characters in the password (@ becomes %40)
uvicorn app.main:app --reload
```

## Infrastructure workflow

Prerequisites: AWS credentials for an IAM user with permission to manage VPC, EKS, IAM, KMS and the state bucket; Terraform >= 1.6; `kubectl`.

```bash
# one time: state bucket and lock table (local state, never destroy)
cd terraform/aws/bootstrap
terraform init
terraform apply -var state_bucket_name=<globally-unique-bucket-name>

# each session
cd ../
terraform init
terraform plan
terraform apply                  # EKS takes roughly 10-20 minutes
aws eks update-kubeconfig --name cloud-cost-sentinel --region us-east-1
kubectl get nodes

# when finished
terraform destroy                # run from terraform/aws, never from bootstrap/
```

The backend block in `terraform/aws/main.tf` contains the literal bucket name because Terraform backend blocks cannot use variables. The `Makefile` wraps these as `make plan`, `make demo-up` and `make demo-down` (the last two use `-auto-approve`).

An EKS cluster and NAT gateway bill by the hour. Destroy the stack when you are done, then confirm nothing is left:

```bash
aws eks list-clusters --region us-east-1
aws ec2 describe-nat-gateways --region us-east-1 --query 'NatGateways[?State==`available`].NatGatewayId'
aws ec2 describe-volumes --region us-east-1 --query 'Volumes[].VolumeId'
aws ec2 describe-addresses --region us-east-1 --query 'Addresses[].AllocationId'
```

## Project log

This is built in public, including the failures that were found and fixed.

**Pinned EKS version that the account could not create.** The first Terraform pinned `cluster_version = "1.30"`. Before applying, `aws eks describe-cluster-versions` showed the account is offered 1.31 to 1.37 only. Moved to 1.36 (standard support until August 2027 per the AWS version-lifecycle page) instead of an older extended-support version, which carries a higher control-plane price.

**Cluster creator would not have had cluster access.** The EKS module (v20) does not grant admin to the identity that created the cluster by default setting alone; admin access has to be requested through an EKS access entry. Added `enable_cluster_creator_admin_permissions = true`, and the plan then showed the access entry and policy association (52 -> 54 resources). `kubectl get nodes` worked straight after apply. The node AMI type is now pinned explicitly to `AL2023_x86_64_STANDARD` rather than left to the module default.

**Plan generated from the wrong file.** The first plan after the fix still showed `1.30` and 52 resources because the edit had not been saved. The mismatch was visible in the plan output (`1.30` in the node group, no access entry). Verified with `grep` against the file on disk, fixed, and re-planned before any apply.

**`.gitignore` lines concatenated.** The file had no trailing newline, so appended lines joined into `__pycache__/.terraform/`, which silently stopped ignoring `__pycache__/`. Found during a repository review; rewritten one pattern per line.

**Large provider binary committed.** A 648MB `.terraform` provider binary was committed by accident and GitHub rejected the push. Recovered by branching fresh from `main` and bringing over only the intended files. `.terraform/` and `*.tfstate` are now ignored, and a `.dockerignore` keeps them out of image builds.

**`requirements.txt` saved as UTF-16.** Created with PowerShell redirection, so it was UTF-16 with CRLF line endings. Converted to UTF-8 with LF so scanners and tooling read it correctly.

**Linux CI would not find `dockerfile`.** The file was lowercase and Docker's default lookup is case-sensitive on Linux. Renamed to `Dockerfile`.

**Cross-account data isolation bug (caught in testing).** `GET /accounts/{id}/cost-records` checked that the account existed but never filtered the query by `account_id`, so it returned every account's records. Found by testing an account that had data and seeing rows from another one. Fixed with `.filter(CostRecord.cloud_account_id == account_id)` and re-verified against the account that had leaked.

**Connection string broken by an unescaped `@`.** A Postgres password containing `@` made the URL parser split on the wrong character and produce a nonsense hostname. Fixed by URL-encoding the password (`%40`).

## License

MIT
