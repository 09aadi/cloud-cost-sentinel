.PHONY: demo-up demo-down plan

TF_DIR = terraform/aws

plan:
	cd $(TF_DIR) && terraform plan

demo-up:
	cd $(TF_DIR) && terraform apply -auto-approve
	aws eks update-kubeconfig --name cloud-cost-sentinel --region us-east-1
	@echo "Cluster is up. kubectl is configured. Deploy the app next."

demo-down:
	cd $(TF_DIR) && terraform destroy -auto-approve
	@echo "Cluster and networking destroyed. State bucket/lock table remain (cheap, permanent)."