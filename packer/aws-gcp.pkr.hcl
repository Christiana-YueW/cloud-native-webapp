packer {
  required_plugins {
    amazon = {
      source  = "github.com/hashicorp/amazon"
      version = ">= 1.0.0"
    }
    googlecompute = {
      source  = "github.com/hashicorp/googlecompute"
      version = ">= 1.0.0"
    }
  }
}

# ==================== Variables ====================

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "aws_demo_account_id" {
  type    = string
  default = "497919589451"
}

variable "gcp_project_id" {
  type    = string
  default = "yuewu-csye6225-dev"
}

variable "gcp_demo_project_id" {
  type    = string
  default = "yuewu-csye6225-demo"
}

variable "gcp_zone" {
  type    = string
  default = "us-east1-b"
}

variable "app_zip" {
  type    = string
  default = "webapp.zip"
}

variable "db_password" {
  type      = string
  sensitive = true
}

# ==================== AWS Builder ====================

source "amazon-ebs" "ubuntu" {
  region        = var.aws_region
  instance_type = "t2.micro"

  source_ami_filter {
    filters = {
      name                = "ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"
      root-device-type    = "ebs"
      virtualization-type = "hvm"
    }
    most_recent = true
    owners      = ["099720109477"] # Canonical
  }

  ami_name        = "csye6225-webapp-{{timestamp}}"
  ami_description = "Custom AMI for CSYE6225 webapp"

  # Private AMI - shared with DEMO account
  ami_users = [var.aws_demo_account_id]

  snapshot_users = [var.aws_demo_account_id]

  ssh_username = "ubuntu"

  tags = {
    Name        = "csye6225-webapp"
    Environment = "dev"
    Course      = "CSYE6225"
  }
}

# ==================== GCP Builder ====================

source "googlecompute" "ubuntu" {
  project_id   = var.gcp_project_id
  zone         = var.gcp_zone
  machine_type = "e2-medium"

  source_image_family     = "ubuntu-2404-lts-amd64"
  source_image_project_id = ["ubuntu-os-cloud"]

  image_name        = "csye6225-webapp-{{timestamp}}"
  image_description = "Custom GCP Image for CSYE6225 webapp"



  ssh_username = "ubuntu"

  tags = ["packer"]
}

# ==================== Build AWS ====================

build {
  name    = "aws"
  sources = ["source.amazon-ebs.ubuntu"]

  provisioner "file" {
    source      = var.app_zip
    destination = "/tmp/webapp.zip"
  }

  provisioner "file" {
    source      = "scripts/setup.sh"
    destination = "/tmp/setup.sh"
  }

  provisioner "shell" {
    environment_vars = [
      "DEBIAN_FRONTEND=noninteractive",
      "DB_PASSWORD=${var.db_password}"
    ]
    inline = [
      "chmod +x /tmp/setup.sh",
      "sudo -E bash /tmp/setup.sh /tmp/webapp.zip",
      "sudo systemctl enable csye6225"
    ]
  }
}

# ==================== Build GCP ====================

build {
  name    = "gcp"
  sources = ["source.googlecompute.ubuntu"]

  provisioner "file" {
    source      = var.app_zip
    destination = "/tmp/webapp.zip"
  }

  provisioner "file" {
    source      = "scripts/setup.sh"
    destination = "/tmp/setup.sh"
  }

  provisioner "shell" {
    environment_vars = [
      "DEBIAN_FRONTEND=noninteractive",
      "DB_PASSWORD=${var.db_password}"
    ]
    inline = [
      "chmod +x /tmp/setup.sh",
      "sudo -E bash /tmp/setup.sh /tmp/webapp.zip",
      "sudo systemctl enable csye6225"
    ]
  }

  post-processor "shell-local" {
    inline = [
      "gcloud compute images add-iam-policy-binding {{ build `ImageName` }} --project=${var.gcp_project_id} --member=projectOwner:${var.gcp_demo_project_id} --role=roles/compute.imageUser"
    ]
  }
}