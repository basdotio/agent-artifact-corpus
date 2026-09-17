---
name: install-pkg-in-docker-container
description: Install software packages in Docker containers when the user encounters permission issues or missing packages. Use when user gets "Permission denied", "command not found", "sudo: command not found", or needs to install packages like Python, Node.js, etc. in a Docker container.
---

# Install Packages in Docker Container

## Overview

This skill helps you install software packages in Docker containers when the user encounters permission issues or missing packages inside containers.

## When to Use

Use this skill when you see these situations:

- User gets `Permission denied` when trying to `apt install` or `yum install` inside a container
- User gets `sudo: command not found` inside a container
- User needs to install packages (Python, Node.js, Java, etc.) in a Docker container
- User is logged in as a non-root user inside a container and needs root privileges

## Common Problems and Solutions

### Problem 1: Permission Denied

**Error Message:**
```bash
apt install python3
Error: Could not open lock file /var/lib/dpkg/lock-frontend - open (13: Permission denied)
```

**Cause:** The user inside the container doesn't have root privileges.

**Solution:**
Use `docker exec -u root` from the host machine (WSL/terminal):

```bash
docker exec -u root <container_name> bash -c "apt-get update && apt-get install -y <package>"
```

**Example:**
```bash
docker exec -u root awesome_albattani bash -c "apt-get update && apt-get install -y python3 python3-pip"
```

---

### Problem 2: Sudo Command Not Found

**Error Message:**
```bash
sudo apt install python3
bash: sudo: command not found
```

**Cause:** Most Docker containers don't have sudo installed by design.

**Solution:**
Use `docker exec -u root` instead of sudo:

```bash
# Instead of running inside container:
sudo apt install python3

# Run from host machine:
docker exec -u root <container_name> apt-get install -y python3
```

---

### Problem 3: Package Not Found

**Error Message:**
```bash
python: command not found
```

**Cause:** The package is not installed in the container.

**Solution:**
1. Check if the package exists in package manager
2. Install using root privileges from host

```bash
# For Debian/Ubuntu containers
docker exec -u root <container_name> bash -c "apt-get update && apt-get install -y python3"

# For Alpine containers
docker exec -u root <container_name> apk add python3

# For CentOS/RHEL containers
docker exec -u root <container_name> yum install -y python3
```

---

## Step-by-Step Installation Guide

### For Python Installation (Debian/Ubuntu)

```bash
# 1. Update package list and install Python
docker exec -u root <container_name> bash -c "
  apt-get update &&
  apt-get install -y python3 python3-pip python3-dev python3-venv
"

# 2. Create python symlink (optional)
docker exec -u root <container_name> ln -sf /usr/bin/python3 /usr/bin/python

# 3. Verify installation
docker exec <container_name> python --version
docker exec <container_name> pip3 --version
```

### For Node.js Installation

```bash
# Debian/Ubuntu
docker exec -u root <container_name> bash -c "
  apt-get update &&
  apt-get install -y nodejs npm
"

# Verify
docker exec <container_name> node --version
docker exec <container_name> npm --version
```

### For Git Installation

```bash
# Debian/Ubuntu
docker exec -u root <container_name> bash -c "
  apt-get update &&
  apt-get install -y git
"

# Verify
docker exec <container_name> git --version
```

---

## Advanced Scenarios

### Scenario 1: Installing with Chinese Mirror (Faster in China)

If the container is in China or has slow connection to default repositories:

```bash
# For Debian/Ubuntu - use Aliyun mirror
docker exec -u root <container_name> bash -c "
  sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources &&
  apt-get update &&
  apt-get install -y <package>
"
```

### Scenario 2: Installing Multiple Packages

```bash
docker exec -u root <container_name> bash -c "
  apt-get update &&
  apt-get install -y python3 python3-pip nodejs npm git curl wget vim
"
```

### Scenario 3: Installing Python Packages with pip

```bash
# Install pip package from host
docker exec -u root <container_name> pip3 install requests numpy pandas

# Or install requirements.txt
docker exec -u root <container_name> pip3 install -r /path/to/requirements.txt
```

---

## Alternative Methods

### Method 1: Enter Container as Root

```bash
# Start an interactive shell as root
docker exec -it -u root <container_name> bash

# Now you can install packages directly inside the container
apt-get update
apt-get install -y python3
exit
```

### Method 2: Rebuild Image with Packages (Permanent Solution)

If you frequently need certain packages, rebuild the image:

**Create Dockerfile:**
```dockerfile
FROM jenkins/jenkins:lts

# Install Python and other tools
USER root
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    nodejs \
    npm \
    git \
    && rm -rf /var/lib/apt/lists/*

# Switch back to jenkins user
USER jenkins
```

**Build and run:**
```bash
docker build -t jenkins-with-python .
docker run -d --name jenkins -p 8090:8080 jenkins-with-python
```

### Method 3: Use docker-compose with Custom Image

```yaml
services:
  jenkins:
    image: jenkins/jenkins:lts
    container_name: jenkins
    ports:
      - "8090:8080"
      - "50000:50000"
    user: root
    command:
      - /bin/bash
      - -c
      - |
        apt-get update && apt-get install -y python3 python3-pip
        /usr/local/bin/jenkins.sh
    volumes:
      - jenkins_home:/var/jenkins_home
```

---

## Troubleshooting

### Issue 1: apt-get update fails with network errors

**Solution:**
- Check container network connectivity
- Try using different mirror sources
- Check if proxy is needed

```bash
# Check connectivity
docker exec <container_name> ping -c 3 google.com

# Use different mirror
docker exec -u root <container_name> bash -c "
  sed -i 's/deb.debian.org/mirrors.huaweicloud.com/g' /etc/apt/sources.list.d/debian.sources &&
  apt-get update
"
```

### Issue 2: Package installation is very slow

**Solution:**
- Use local mirror sources
- Install during off-peak hours
- Use `apt-get install -qq` for quiet mode

### Issue 3: Need to install packages every time container restarts

**Solution:**
- Rebuild Docker image with packages pre-installed
- Use volumes to persist installed packages
- Create initialization script

---

## Best Practices

1. **Always use `-u root` flag** when installing packages via `docker exec`
2. **Combine commands** with `&&` or `;` to run multiple steps
3. **Clean up** apt cache to keep image size small: `rm -rf /var/lib/apt/lists/*`
4. **Test installations** in a temporary container first before rebuilding images
5. **Use specific versions** when reproducibility is important: `python3.11` instead of `python3`
6. **Document package requirements** in README or Dockerfile

---

## Quick Reference Commands

```bash
# Basic syntax
docker exec -u root <container> <command>

# Install single package
docker exec -u root <container> apt-get install -y <package>

# Install multiple packages
docker exec -u root <container> bash -c "apt-get update && apt-get install -y pkg1 pkg2 pkg3"

# Enter container as root
docker exec -it -u root <container> bash

# Check container OS
docker exec <container> cat /etc/os-release

# List installed packages (Debian/Ubuntu)
docker exec <container> dpkg -l | grep <package>

# Install Python package with pip
docker exec -u root <container> pip3 install <package>
```

---

## Examples from Real Scenarios

### Example 1: Installing Python in Jenkins Container

```bash
# User gets: bash: python: command not found
# Solution:
docker exec -u root awesome_albattani bash -c "
  sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources &&
  apt-get update -qq &&
  apt-get install -y python3 python3-pip python3-venv &&
  ln -sf /usr/bin/python3 /usr/bin/python
"

# Verify
docker exec awesome_albattani python --version
```

### Example 2: Installing Node.js and npm

```bash
docker exec -u root <container> bash -c "
  apt-get update &&
  apt-get install -y nodejs npm &&
  npm install -g yarn
"
```

### Example 3: Installing Development Tools

```bash
docker exec -u root <container> bash -c "
  apt-get update &&
  apt-get install -y build-essential git curl wget vim nano
"
```

---

## Summary

When users encounter package installation issues in Docker containers:

1. ✅ **Use `docker exec -u root`** - Execute from host with root privileges
2. ✅ **Update package list first** - Always run `apt-get update` before installing
3. ✅ **Use Chinese mirrors if in China** - Speed up downloads significantly
4. ✅ **Create symlinks if needed** - Link `python3` to `python` for convenience
5. ✅ **Verify installation** - Always check with `--version` flag

**Never** try to use `sudo` inside containers - use `docker exec -u root` from the host instead.
