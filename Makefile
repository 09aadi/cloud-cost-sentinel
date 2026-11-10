.PHONY: plan demo-up demo-down ecr-login image deploy

TF_DIR = terraform/aws
BOOT_DIR = terraform/aws/bootstrap
REGION = us-east-1
GIT_SHA = $(shell git rev-parse --short HEAD)

# The ECR URL comes from the bootstrap stack, which is never destroyed.
ECR_URL = $(shell terraform -chdir=$(BOOT_DIR) output -raw ecr_repository_url)

plan:
	cd $(TF_DIR) && terraform plan

demo-up:
	cd $(TF_DIR) && terraform apply -auto-approve
	aws eks update-kubeconfig --name cloud-cost-sentinel --region $(REGION)
	@echo "Cluster is up. kubectl is configured. Run 'make deploy' next."

# Delete the app first so nothing created inside the cluster can block the VPC delete.
demo-down:
	-helm uninstall ccs
	cd $(TF_DIR) && terraform destroy -auto-approve
	@echo "Cluster and networking destroyed. State bucket, lock table and ECR remain (cheap, permanent)."

ecr-login:
	aws ecr get-login-password --region $(REGION) | docker login --username AWS --password-stdin $(firstword $(subst /, ,$(ECR_URL)))

# Build for linux/amd64 (the t3.medium nodes are x86_64; an Apple Silicon Mac builds arm64 by default).
# Tag = git short SHA. ECR tags are immutable, so commit before building a new image.
image: ecr-login
	docker buildx build --platform linux/amd64 -t $(ECR_URL):$(GIT_SHA) --push .

deploy:
	helm upgrade --install ccs charts/cloud-cost-sentinel \
		--set image.repository=$(ECR_URL) --set image.tag=$(GIT_SHA)
