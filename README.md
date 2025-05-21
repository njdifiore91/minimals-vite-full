# Merchant Cash Advance (MCA) Application Processing System

A comprehensive system that automates email-based application processing by integrating the Minimal UI Kit frontend with specialized backend microservices. This system achieves a 93% reduction in manual processing through automation, processes applications in under 5 minutes from receipt to completion, and maintains 99% data extraction accuracy through AI and machine learning.

## System Architecture

### Frontend
- **Minimal UI Kit**: React/TypeScript/Vite-based UI framework

### Backend Microservices
- **Email Service** (Node.js/Nodemailer): Monitors submissions inbox using IMAP protocol
- **Document Service** (Python/scikit-learn): Classifies incoming documents with AI
- **OCR Service** (Python/TensorFlow): Extracts data from documents (typed and handwritten)
- **Data Service** (Java/Spring Boot): Manages application data and business logic
- **Notification Service** (Node.js): Handles alerts and webhooks
- **API Gateway** (Kong): Provides unified API access with security controls

### Infrastructure Components
- **PostgreSQL 14**: Primary database with read replicas
- **RabbitMQ**: Message queue system for service communication
- **Redis 7.0**: Caching layer
- **S3-compatible storage**: Document repository with encryption

## Prerequisites

- Node.js ≥20 (Required for frontend and Node.js microservices)
- Python 3.9+ (Required for Document and OCR services)
- Java 17+ (Required for Data Service)
- Docker (Required for containerization)
- Kubernetes (Required for deployment)
- Terraform (Required for infrastructure)

## Installation and Setup

### Frontend Setup

**Using Yarn (Recommended)**

```sh
yarn install
yarn dev
```

**Using Npm**

```sh
npm i
npm run dev
```

### Microservices Setup

#### Email Service
```sh
cd email-service
npm install
npm run dev
```

#### Document Service
```sh
cd document-service
pip install -r requirements.txt
python -m src.main
```

#### OCR Service
```sh
cd ocr-service
pip install -r requirements.txt
python -m src.main
```

#### Data Service
```sh
cd data-service
./mvnw spring-boot:run
```

#### Notification Service
```sh
cd notification-service
npm install
npm run dev
```

#### API Gateway
```sh
cd api-gateway
docker-compose up -d
```

### Infrastructure Setup

#### Using Terraform
```sh
cd infrastructure/terraform/environments/development
terraform init
terraform apply
```

#### Using Kubernetes
```sh
cd infrastructure/kubernetes
kubectl apply -f namespaces/
kubectl apply -f infrastructure/
kubectl apply -f charts/
```

## Development Workflow

### Frontend Development

1. Start the frontend development server:
   ```sh
   cd frontend
   yarn dev
   ```
2. Access the application at http://localhost:8080

### Backend Development

1. Start all microservices using Docker Compose:
   ```sh
   docker-compose up -d
   ```
2. For individual service development, use the service-specific setup commands above

## Build

### Frontend Build

```sh
cd frontend
yarn build
# or
npm run build
```

### Microservices Build

```sh
# Build all services
docker-compose build

# Build individual services
docker build -t email-service ./email-service
docker build -t document-service ./document-service
docker build -t ocr-service ./ocr-service
docker build -t data-service ./data-service
docker build -t notification-service ./notification-service
docker build -t api-gateway ./api-gateway
```

## Deployment

### Frontend Deployment

The frontend application is deployed using Vercel:

```sh
cd frontend
yarn build
vercel deploy --prod
```

### Microservices Deployment

Microservices are deployed to Kubernetes clusters managed via Terraform:

```sh
# Deploy to development environment
cd infrastructure/terraform/environments/development
terraform apply

# Deploy to staging environment
cd infrastructure/terraform/environments/staging
terraform apply

# Deploy to production environment
cd infrastructure/terraform/environments/production
terraform apply
```

## Minimal UI Kit Reference

### Mock server

By default we provide demo data from : `https://api-dev-minimal-[version].vercel.app`

To set up your local server:

- **Guide:** [https://docs.minimals.cc/mock-server](https://docs.minimals.cc/mock-server).

- **Resource:** [Download](https://www.dropbox.com/sh/6ojn099upi105tf/AACpmlqrNUacwbBfVdtt2t6va?dl=0).

### Full version

- Create React App ([migrate to CRA](https://docs.minimals.cc/migrate-to-cra/)).
- Next.js
- Vite.js

### Starter version

- To remove unnecessary components. This is a simplified version ([https://starter.minimals.cc/](https://starter.minimals.cc/))
- Good to start a new project. You can copy components from the full version.
- Make sure to install the dependencies exactly as compared to the full version.

---

**NOTE:**
_When copying folders remember to also copy hidden files like .env. This is important because .env files often contain environment variables that are crucial for the application to run correctly._