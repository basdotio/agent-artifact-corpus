# Build variables
IMAGE_NAME ?= fm-mcp
IMAGE_TAG ?= latest
CONTAINER_NAME ?= fm-mcp-container
DOCKER_REGISTRY ?= quay.io/cdoan25

.PHONY: build run clean push

# Build the container image
build:
	podman build -t $(DOCKER_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG) -f Containerfile .

# Push the container image to registry
push:
	podman push $(DOCKER_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

# Run the container
run:
	podman run --rm -p 8000:8000 --name $(CONTAINER_NAME) $(DOCKER_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

# Run the container in detached mode
run-detached:
	podman run -d -p 8000:8000 --name $(CONTAINER_NAME) $(DOCKER_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)

# Stop the running container
stop:
	podman stop $(CONTAINER_NAME) || true

# Clean up containers and images
clean:
	podman stop $(CONTAINER_NAME) || true
	podman rm $(CONTAINER_NAME) || true
	podman rmi $(DOCKER_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG) || true

# Build and run in one command
up: build run

# Show help
help:
	@echo "Available targets:"
	@echo "  build         - Build the container image"
	@echo "  push          - Push the container image to registry"
	@echo "  run           - Run the container interactively"
	@echo "  run-detached  - Run the container in background"
	@echo "  stop          - Stop the running container"
	@echo "  clean         - Remove container and image"
	@echo "  up            - Build and run"
	@echo "  help          - Show this help"
