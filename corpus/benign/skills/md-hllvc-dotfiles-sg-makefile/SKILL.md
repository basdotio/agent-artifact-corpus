---
name: sg-makefile
description: Generate StackGuardian-style Makefiles for Docker build and deploy workflows. Use when user asks to "create a Makefile", "generate build/deploy Makefile", "write Makefile for service", or needs a StackGuardian service Makefile with ECR/Lambda/ECS deployment.
version: 1.0.0
---

# StackGuardian Makefile Generator

Generate Makefiles following StackGuardian conventions for Docker-based build and deploy workflows.

## Workflow

### Step 1: Gather Service Information

Ask the user for:

1. **Service name** - Used in comments and default image names
2. **DASH configuration**:
   - Account ID (e.g., 790543352839)
   - AWS profile name (e.g., default)
   - ECR image name (e.g., stackguardian/my-service)
   - Lambda/service name for deployment (DASH_LAMBDA)
3. **PROD configuration**:
   - Account ID (e.g., 476299211833)
   - AWS profile name (e.g., sg-prod)
   - ECR image name (e.g., my-service-lambda)
   - Lambda/service name for deployment (PROD_LAMBDA)
4. **Build options**:
   - Include git_token secret? (yes/no)
5. **Deploy type**: Lambda, ECS, or custom command

### Step 2: Generate Makefile

Use the template below, replacing placeholders with user-provided values.

## Makefile Template

```makefile
# Makefile for building and pushing Docker images
# StackGuardian Service: {{SERVICE_NAME}}

# Default version - can be overridden via command line: make dash VERSION=1.2.3
VERSION ?= $(shell git describe --tags --always --dirty)

# Registry and image configuration
BUILD_REGION ?= eu-central-1
REGISTRY = $(ACCOUNT_ID).dkr.ecr.$(BUILD_REGION).amazonaws.com
IMAGE_NAME ?=
FULL_IMAGE = $(REGISTRY)/$(IMAGE_NAME)

# Build settings
PLATFORM = linux/arm64
DOCKERFILE = Dockerfile
DOCKER_BUILD_ARGS = --push --pull --platform $(PLATFORM) --provenance=false

# ============================================================================
# DASH Configuration
# ============================================================================
DASH_ACCOUNT_ID = {{DASH_ACCOUNT_ID}}
DASH_PROFILE = {{DASH_PROFILE}}
DASH_IMAGE = {{DASH_IMAGE}}
DASH_LAMBDA = {{DASH_LAMBDA}}

# ============================================================================
# PROD Configuration
# ============================================================================
PROD_ACCOUNT_ID = {{PROD_ACCOUNT_ID}}
PROD_PROFILE = {{PROD_PROFILE}}
PROD_IMAGE = {{PROD_IMAGE}}
PROD_LAMBDA = {{PROD_LAMBDA}}

# Dynamic variables
PROFILE ?=
ACCOUNT_ID ?=
LAMBDA_NAME ?=

DEPLOY_REGION ?= eu-central-1

.PHONY: help version login build deploy build-dash deploy-dash build-deploy-dash build-prod deploy-prod-eu build-deploy-prod-eu deploy-prod-us build-deploy-prod-us deploy-prod-all build-deploy-prod-all

##@ General
help: ## Show this help message
	@echo 'Usage: make <target>'
	@echo ''
	@awk 'BEGIN {FS = ":.*##"; printf ""} /^[a-zA-Z_-]+:.*?## / {printf "  %-24s %s\n", $$1, $$2} /^##@/ {printf "\n\033[1m%s\033[0m\n", substr($$0, 5)}' $(MAKEFILE_LIST)

version: ## Show current version
	@echo $(VERSION)

login:
	@echo "Logging into ECR using profile: $(PROFILE)..."
	@aws --profile $(PROFILE) ecr-public get-login-password --region us-east-1 \
		| docker login --username AWS --password-stdin public.ecr.aws
	@aws --profile $(PROFILE) ecr get-login-password --region eu-central-1 \
		| docker login --username AWS --password-stdin $(REGISTRY)

build: login
	@echo "Building and pushing image: $(FULL_IMAGE):$(VERSION)"
	@docker buildx build \
		-f $(DOCKERFILE) $(DOCKER_BUILD_ARGS) \
		{{GIT_TOKEN_SECRET}}-t $(FULL_IMAGE):$(VERSION) .
	@echo "Build completed: $(FULL_IMAGE):$(VERSION)"

deploy:
{{DEPLOY_COMMAND}}

##@ DASH
DASH_VARS = PROFILE=$(DASH_PROFILE) ACCOUNT_ID=$(DASH_ACCOUNT_ID) IMAGE_NAME=$(DASH_IMAGE) LAMBDA_NAME=$(DASH_LAMBDA)

build-dash: ## Build and push DASH image
	$(MAKE) build $(DASH_VARS)

deploy-dash: ## Deploy DASH Lambda
	$(MAKE) deploy $(DASH_VARS)

build-deploy-dash: ## Build and deploy DASH
	$(MAKE) build deploy $(DASH_VARS)

##@ PROD
PROD_VARS = PROFILE=$(PROD_PROFILE) ACCOUNT_ID=$(PROD_ACCOUNT_ID) IMAGE_NAME=$(PROD_IMAGE) LAMBDA_NAME=$(PROD_LAMBDA)

build-prod: ## Build and push PROD image
	$(MAKE) build $(PROD_VARS)

##@ PROD EU
deploy-prod-eu: ## Deploy PROD to EU
	$(MAKE) deploy $(PROD_VARS)

build-deploy-prod-eu: ## Build and deploy PROD EU
	$(MAKE) build deploy $(PROD_VARS)

##@ PROD US
deploy-prod-us: ## Deploy PROD to US
	$(MAKE) deploy $(PROD_VARS) DEPLOY_REGION=us-east-2

build-deploy-prod-us: ## Build and deploy PROD US
	$(MAKE) build $(PROD_VARS) && $(MAKE) deploy $(PROD_VARS) DEPLOY_REGION=us-east-2

##@ PROD All Regions
deploy-prod-all: ## Deploy PROD to all regions
	$(MAKE) deploy-prod-eu
	$(MAKE) deploy-prod-us

build-deploy-prod-all: ## Build and deploy PROD all
	$(MAKE) build-prod
	$(MAKE) deploy-prod-eu
	$(MAKE) deploy-prod-us
```

## Placeholder Substitutions

### Git Token Secret

**If git_token is enabled:**
```
--secret id=git_token,env=GIT_TOKEN \
		```

**If git_token is disabled:** Leave empty (just the `-t` line follows directly)

### Deploy Command Templates

**Lambda deployment:**
```makefile
deploy:
	@aws lambda update-function-code \
		--region $(DEPLOY_REGION) \
		--function-name $(LAMBDA_NAME) \
		--image-uri $(FULL_IMAGE):$(VERSION)
```

**ECS deployment:**
```makefile
deploy:
	@aws ecs update-service \
		--region $(DEPLOY_REGION) \
		--cluster {{CLUSTER_NAME}} \
		--service $(LAMBDA_NAME) \
		--force-new-deployment
```

**Custom deployment:** Ask user to provide their deploy command using `$(DEPLOY_REGION)`, `$(LAMBDA_NAME)`, `$(FULL_IMAGE)`, and `$(VERSION)` variables.

## Important Notes

- All recipe lines MUST use tabs (not spaces) for indentation
- The `help` target uses awk to parse `##` comments for self-documentation
- `##@` creates section headers in help output
- DASH is typically the development/staging environment
- PROD has two regions: EU (eu-central-1) and US (us-east-2)
- The build target always pushes to ECR (--push flag)
- Platform is linux/arm64 by default for AWS Lambda ARM architecture

## Example Usage

When a user says "create a Makefile for the auth-service":

1. Ask for DASH and PROD configurations
2. Ask if git_token secret is needed
3. Ask for deploy type (Lambda/ECS/custom)
4. Generate the complete Makefile with all values substituted
5. Write to `Makefile` in the current directory
