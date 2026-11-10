# EKS apply -> verify -> destroy (2026-11-10)

First full run of `terraform/aws` against a real AWS account: provision the VPC and EKS
cluster, prove it works, destroy it, and confirm nothing is left billing.

All output below is transcribed from the terminal. The AWS account ID is replaced with
`<ACCOUNT_ID>` because this repository is public. Nothing else was edited.

- Region: `us-east-1`
- Identity: IAM user `terraDev-01`
- Terraform state: S3 backend with DynamoDB locking (created separately in `terraform/aws/bootstrap`)

## 1. Pre-flight

Which EKS versions the account can create (the original config pinned `1.30`, which is not in this list):

```
$ aws eks describe-cluster-versions --region us-east-1 \
    --query 'clusterVersions[].[clusterVersion,status]' --output table
|  1.37 |  STANDARD_SUPPORT  |
|  1.36 |  STANDARD_SUPPORT  |
|  1.35 |  STANDARD_SUPPORT  |
|  1.34 |  STANDARD_SUPPORT  |
|  1.33 |  EXTENDED_SUPPORT  |
|  1.32 |  EXTENDED_SUPPORT  |
|  1.31 |  EXTENDED_SUPPORT  |
```

Nothing already running before the apply: `aws eks list-clusters` returned `[]` and there were no NAT gateways in the `available` state.

## 2. Plan (after fixing the config)

```
Plan: 54 to add, 0 to change, 0 to destroy.
```

The first plan, made before the fixes, showed `52 to add` with `1.30` on the cluster and node group and no access entry. After the fixes the plan showed `1.36` on the cluster, the `time_sleep` trigger and the node group; `ami_type = "AL2023_x86_64_STANDARD"`; the two extra resources `aws_eks_access_entry["cluster_creator"]` and `aws_eks_access_policy_association["cluster_creator_admin"]`; and zero destroys or replacements.

## 3. Apply

```
Apply complete! Resources: 54 added, 0 changed, 0 destroyed.
```

The managed node group took 2m27s to create.

## 4. Verification

Node and system pods:

```
$ kubectl get nodes -o wide
NAME                        STATUS   ROLES    AGE     VERSION               INTERNAL-IP   OS-IMAGE                        KERNEL-VERSION                        CONTAINER-RUNTIME
ip-10-0-1-47.ec2.internal   Ready    <none>   4m45s   v1.36.5-eks-6e7947a   10.0.1.47     Amazon Linux 2023.12.20261102   6.18.56-125.164.amzn2023.x86_64 (amd64)   containerd://2.3.7+unknown

$ kubectl get pods -A
NAMESPACE     NAME                       READY   STATUS    RESTARTS   AGE
kube-system   aws-node-pbxq9             2/2     Running   0          5m53s
kube-system   coredns-764945d74d-2jndh   1/1     Running   0          9m41s
kube-system   coredns-764945d74d-fkd27   1/1     Running   0          9m41s
kube-system   kube-proxy-x77q8           1/1     Running   0          5m53s
```

The identity that ran Terraform is registered as a cluster admin through an EKS access entry:

```
$ aws eks list-access-entries --cluster-name cloud-cost-sentinel --region us-east-1
arn:aws:iam::<ACCOUNT_ID>:role/aws-service-role/eks.amazonaws.com/AWSServiceRoleForAmazonEKS
arn:aws:iam::<ACCOUNT_ID>:role/default-eks-node-group-20261110045229939600000001
arn:aws:iam::<ACCOUNT_ID>:user/terraDev-01
```

### Outbound networking from a private subnet

The node sits in a private subnet (`10.0.1.0/24`) with no public IP. To prove egress through the NAT gateway, a pod was started from a public image (`nginx:stable`):

```
$ kubectl run nat-test --image=nginx:stable --restart=Never
$ kubectl describe pod nat-test | grep -A8 Events
  Normal  Scheduled  Successfully assigned default/nat-test to ip-10-0-1-47.ec2.internal
  Normal  Pulling    Pulling image "nginx:stable"
  Normal  Pulled     Successfully pulled image "nginx:stable" in 2.448s (2.448s including waiting). Image size: 63639735 bytes.
  Normal  Created    Container created
  Normal  Started    Container started
$ kubectl delete pod nat-test
```

The `kubectl get pod -w` watch printed `http2: client connection lost` once after the pod reached `Running`. That was the client-side watch stream dropping. Regular `kubectl` commands kept working.

## 5. Destroy and cleanup check

`terraform destroy` was run from `terraform/aws` (never from `bootstrap/`). Afterwards, in `us-east-1`:

```
aws eks list-clusters                                   -> { "clusters": [] }
aws ec2 describe-nat-gateways (state=available)         -> []
aws ec2 describe-volumes                                -> []
aws ec2 describe-addresses (Elastic IPs)                -> []
```

The state bucket and lock table remain by design.

## Not yet verified

- The actual AWS charge for this run. Cost data lags by about a day. The Billing console figure will be added here once it is confirmed.
- The `terraform destroy` summary line was not captured; the four empty checks above are the evidence that it completed.
