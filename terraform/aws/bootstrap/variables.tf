variable "region" {
  type    = string
  default = "us-east-1"
}

variable "state_bucket_name" {
  type        = string
  description = "Must be globally unique across all of AWS"
}

variable "lock_table_name" {
  type    = string
  default = "cloud-cost-sentinel-tf-locks"
}