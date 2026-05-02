# Cloud-Native Web Application

A backend-focused web application built with FastAPI and PostgreSQL, designed for cloud-native deployment on AWS and GCP. The project combines API development, authentication, relational data modeling, image/file storage, observability, machine image baking, and infrastructure integration for asynchronous workflows.

## Why This Project Matters

This repository reflects the type of backend and full-stack engineering work I want to do professionally:

- designing REST APIs
- building database-backed services
- integrating cloud services into application workflows
- packaging applications for repeatable deployment
- adding metrics, logging, and health checks for operations

## Architecture

The application is centered around a FastAPI service that exposes versioned API endpoints and persists data in PostgreSQL. In cloud deployments, it integrates with:

- **S3** for syllabus file storage
- **SNS** for asynchronous user-verification events
- **CloudWatch** for logs and metrics
- **Packer** for machine image creation
- **Terraform-managed infrastructure** for compute, networking, storage, IAM, and supporting services

At startup, the service detects whether it is running on AWS or GCP and adjusts cloud-specific behavior accordingly.

## Tech Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Authentication:** HTTP Basic Auth with password hashing
- **Cloud:** AWS S3, SNS, CloudWatch, EC2 image pipeline
- **Tooling:** Packer, Postman/Newman, GitHub Actions

## Core Features

- User registration and authenticated self-service account APIs
- Health check endpoint for service monitoring
- Course and syllabus-related data models
- S3-backed file handling
- SNS publishing for downstream verification workflows
- Structured logging and metrics middleware
- Automated API testing with Newman

## API Surface

Key routes include:

- `GET /healthz`
- `POST /v1/user`
- `GET /v1/user/self`
- `PUT /v1/user/self`

Swagger docs are available locally at `/docs`.

## Repository Structure

```text
webapp/
├── app/
│   ├── main.py
│   ├── auth.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── s3_client.py
│   ├── metrics.py
│   ├── db_metrics.py
│   ├── middleware.py
│   └── logging_config.py
├── cloudwatch/
│   └── amazon-cloudwatch-agent.json
├── packer/
│   └── aws-gcp.pkr.hcl
├── scripts/
│   └── setup.sh
├── postman_collection.json
├── postman_environment.template.json
└── requirements.txt
```

## Local Development

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Node.js 18+ for Newman-based API testing

### Setup

```bash
git clone git@github.com:YOUR_USERNAME/webapp.git
cd webapp

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

createdb webapp_db
echo 'DATABASE_URL=postgresql://YOUR_USERNAME@localhost:5432/webapp_db' > .env

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open:

- App: `http://127.0.0.1:8000`
- Docs: `http://127.0.0.1:8000/docs`

## Testing

Integration tests are exercised with Postman/Newman.

```bash
npm install -g newman

psql webapp_db -c "DELETE FROM users;"

newman run postman_collection.json \
  --env-var "test_user_username=test@example.com" \
  --env-var "test_user_password=TestPassword123!" \
  --env-var "test_user_new_password=NewPassword123!"
```

## Deployment Notes

This repository is intended to work as part of a larger cloud-native deployment flow:

- **Packer** builds machine images
- **Terraform** provisions infrastructure
- **EC2 user data** injects runtime configuration
- **SNS** triggers asynchronous verification workflows
- **CloudWatch** collects logs and metrics

## What This Repo Demonstrates

- backend API design
- relational data modeling
- cloud service integration
- deployment-minded application structure
- observability and operational readiness

## Related Repositories

- `serverless` - Lambda-based asynchronous email verification workflow
- `tf-infra` - Terraform code for the infrastructure that supports this application
