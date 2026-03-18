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

  launch_block_device_mappings {
    device_name           = "/dev/sda1"
    volume_size           = 25
    volume_type           = "gp3"
    delete_on_termination = true
  }

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
  image_family      = "csye6225-webapp"
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
    source      = "${path.root}/../scripts/setup.sh"
    destination = "/tmp/setup.sh"
  }

  provisioner "shell" {
    environment_vars = [
      "DEBIAN_FRONTEND=noninteractive",
    ]
    inline = [
      "chmod +x /tmp/setup.sh",
      "sudo -E bash /tmp/setup.sh /tmp/webapp.zip",
    ]
  }

  # Install CloudWatch Unified Agent
  provisioner "shell" {
    inline = [
      "echo 'Installing CloudWatch Unified Agent...'",
      "sudo apt-get update -y",
      "sudo apt-get install -y wget",
      "wget -O /tmp/amazon-cloudwatch-agent.deb https://amazoncloudwatch-agent.s3.amazonaws.com/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb",
      "sudo dpkg -i /tmp/amazon-cloudwatch-agent.deb",
      "rm -f /tmp/amazon-cloudwatch-agent.deb",
      "echo 'CloudWatch Agent installed successfully'"
    ]
  }

  # Copy CloudWatch Agent configuration
  provisioner "file" {
    source      = "${path.root}/../cloudwatch/amazon-cloudwatch-agent.json"
    destination = "/tmp/amazon-cloudwatch-agent.json"
  }

  provisioner "shell" {
    inline = [
      "sudo mkdir -p /opt/aws/amazon-cloudwatch-agent/etc/",
      "sudo mv /tmp/amazon-cloudwatch-agent.json /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json",
      "sudo chown root:root /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json",
      "sudo chmod 644 /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json",
      "sudo systemctl enable amazon-cloudwatch-agent",
      "echo 'CloudWatch Agent configuration copied and service enabled'"
    ]
  }

  provisioner "shell" {
    inline = [
      "sudo rm -f /tmp/webapp.zip /tmp/setup.sh /tmp/amazon-cloudwatch-agent.json",
      "sudo apt-get clean",
      "sudo rm -rf /var/lib/apt/lists/*",
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
    source      = "${path.root}/../scripts/setup.sh"
    destination = "/tmp/setup.sh"
  }

  provisioner "shell" {
    environment_vars = [
      "DEBIAN_FRONTEND=noninteractive",
    ]
    inline = [
      "chmod +x /tmp/setup.sh",
      "sudo -E bash /tmp/setup.sh /tmp/webapp.zip",
    ]
  }

  provisioner "shell" {
    inline = [
      "sudo rm -f /tmp/webapp.zip /tmp/setup.sh",
      "sudo apt-get clean",
      "sudo rm -rf /var/lib/apt/lists/*",
    ]
  }
}
