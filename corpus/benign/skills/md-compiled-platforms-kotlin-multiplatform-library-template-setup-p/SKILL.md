---
name: setup-publishing
description: Set up and configure publishing for Kotlin Multiplatform libraries. Use when the user wants to configure Maven Central, GitHub Packages, or custom repositories, needs help with publishing setup, or asks about artifact deployment.
---

# Setup Publishing for KMP Libraries

## Purpose

Guide users through configuring flexible publishing to multiple repository types (Maven Central, GitHub Packages, Custom Maven, JFrog, CloudSmith).

## When to Use

- User wants to publish their library
- Asking about Maven Central, GitHub Packages, or custom repositories
- Setting up publishing configuration
- Troubleshooting publishing issues
- Adding or changing publishing targets

## Configuration Workflow

### Step 1: Determine Publishing Strategy

Ask the user:

**"Where do you want to publish your library?"**

Options:
- **Maven Central** - Public open-source libraries
- **GitHub Packages** - Private team libraries (free)
- **Custom Maven** - Self-hosted Nexus/Artifactory
- **JFrog Cloud** - Managed Artifactory
- **CloudSmith** - Modern package hosting
- **Multiple** - Combination of above

### Step 2: Update project.yml

Based on their choice, update `project.yml`:

#### Maven Central Only

```yaml
publishing:
  enabled: true
  group_id: io.github.username  # or com.company
  
  repositories:
    maven_central:
      enabled: true
      auto_release: false
```

#### GitHub Packages Only

```yaml
publishing:
  enabled: true
  group_id: com.yourcompany.kmp
  
  repositories:
    github_packages:
      enabled: true
      owner: org-name
      repository: repo-name
```

#### Maven Central + GitHub Packages (Recommended)

```yaml
publishing:
  enabled: true
  group_id: io.github.username
  
  repositories:
    maven_central:
      enabled: true
      auto_release: false
    
    github_packages:
      enabled: true
      owner: your-org
      repository: maven-packages
  
  strategy:
    snapshots_on_main: true   # Auto-publish snapshots to GitHub
    releases_on_tag: true      # Publish releases to both
```

#### Custom Maven (Nexus/Artifactory)

```yaml
publishing:
  enabled: true
  group_id: com.company.kmp
  
  repositories:
    custom_maven:
      enabled: true
      name: Company Nexus
      releases_url: https://nexus.company.com/repository/maven-releases/
      snapshots_url: https://nexus.company.com/repository/maven-snapshots/
```

#### JFrog Cloud

```yaml
publishing:
  enabled: true
  group_id: com.company.kmp
  
  repositories:
    jfrog:
      enabled: true
      url: https://company.jfrog.io/artifactory/maven-releases/
```

#### CloudSmith

```yaml
publishing:
  enabled: true
  group_id: com.company.kmp
  
  repositories:
    cloudsmith:
      enabled: true
      owner: company
      repository: maven
```

### Step 3: Validate Configuration

Run validation:

```bash
python3 scripts/get-publishing-config.py --validate
```

If errors, fix them in `project.yml` and validate again.

### Step 4: Set Up Secrets

Guide user to add required secrets to GitHub:

**Get required secrets list:**
```bash
python3 scripts/get-publishing-config.py --required-secrets <repository_name>
```

**Common secrets by repository:**

| Repository | Required Secrets |
|------------|------------------|
| maven_central | `MAVEN_CENTRAL_USERNAME`, `MAVEN_CENTRAL_PASSWORD`, `SIGNING_KEY`, `SIGNING_PASSWORD` |
| github_packages | `GITHUB_TOKEN` (auto-provided) |
| custom_maven | `CUSTOM_MAVEN_USERNAME`, `CUSTOM_MAVEN_PASSWORD`, `SIGNING_KEY`, `SIGNING_PASSWORD` |
| jfrog | `JFROG_USERNAME`, `JFROG_PASSWORD`, `SIGNING_KEY`, `SIGNING_PASSWORD` |
| cloudsmith | `CLOUDSMITH_API_KEY`, `SIGNING_KEY`, `SIGNING_PASSWORD` |

**Add secrets:**
1. Go to GitHub repository → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add each required secret

### Step 5: Repository-Specific Setup

#### For Maven Central

1. **Create Sonatype account**: https://central.sonatype.com/
2. **Claim namespace**: Verify group ID (io.github.username or com.company)
3. **Generate GPG key**:
```bash
gpg --full-generate-key
gpg --armor --export-secret-keys KEY_ID | base64 > signing-key.txt
gpg --keyserver keyserver.ubuntu.com --send-keys KEY_ID
```
4. **Add secrets**: `MAVEN_CENTRAL_USERNAME`, `MAVEN_CENTRAL_PASSWORD`, `SIGNING_KEY` (contents of signing-key.txt), `SIGNING_PASSWORD`

Point to: [docs/docs/development/publishing-maven-central.md](../../../docs/docs/development/publishing-maven-central.md)

#### For GitHub Packages

1. **Choose repository**: Same as code or dedicated `maven-packages`
2. **Update project.yml**: Set `owner` and `repository`
3. No additional secrets needed (uses `GITHUB_TOKEN`)

Point to: [docs/docs/development/publishing-github-packages.md](../../../docs/docs/development/publishing-github-packages.md)

#### For Custom Maven

1. **Set up Nexus/Artifactory**: Install and configure
2. **Create repositories**: maven-releases, maven-snapshots
3. **Create deployment user**: With deploy permissions
4. **Get repository URLs**: Update `project.yml`
5. **Add secrets**: `CUSTOM_MAVEN_USERNAME`, `CUSTOM_MAVEN_PASSWORD`

Point to: [docs/docs/development/publishing-custom-maven.md](../../../docs/docs/development/publishing-custom-maven.md)

#### For JFrog Cloud

1. **Sign up**: https://jfrog.com/start-free/
2. **Create repositories**: maven-releases, maven-snapshots
3. **Generate API token**: Profile → Authentication Settings
4. **Add secrets**: `JFROG_USERNAME`, `JFROG_PASSWORD` (API token)

Point to: [docs/docs/development/publishing-cloud-services.md#jfrog](../../../docs/docs/development/publishing-cloud-services.md#jfrog)

#### For CloudSmith

1. **Sign up**: https://cloudsmith.com/
2. **Create repository**: Maven type
3. **Generate API key**: Settings → API Keys
4. **Add secrets**: `CLOUDSMITH_API_KEY`

Point to: [docs/docs/development/publishing-cloud-services.md#cloudsmith](../../../docs/docs/development/publishing-cloud-services.md#cloudsmith)

### Step 6: Test Locally

Before publishing to remote repositories:

```bash
# Build everything
./gradlew clean build

# Validate API compatibility
./gradlew apiCheck

# Publish to local Maven repository
./gradlew publishToMavenLocal

# Check artifacts
ls -la ~/.m2/repository/
```

Look for:
- `.jar` files
- `.pom` files
- `.module` files
- `.asc` files (if signing enabled)

### Step 7: Publish

#### Via GitHub Actions (Recommended)

```bash
# Update version
# gradle.properties: VERSION_NAME=1.0.0

# Commit and tag
git add gradle.properties
git commit -m "chore: prepare release 1.0.0"
git push origin main

# Create and push tag
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0

# Create GitHub release (triggers publishing)
gh release create v1.0.0 --title "v1.0.0" --notes "Release notes"
```

#### Manual (Local)

```bash
# Ensure credentials are set
./gradlew publish
```

## Troubleshooting Guide

### Configuration Issues

```bash
# Validate configuration
python3 scripts/get-publishing-config.py --validate

# Check enabled repositories
python3 scripts/get-publishing-config.py --list-enabled

# View specific repository config
python3 scripts/get-publishing-config.py --repository maven_central
```

### Common Errors

**"Group ID cannot contain hyphens"**
- Fix: Use dots instead: `com.company.kmp` not `com.company-kmp`

**"No repositories enabled"**
- Fix: Set `enabled: true` for at least one repository in `project.yml`

**"401 Unauthorized" during publish**
- Check: Secrets are correct in GitHub
- Verify: Account credentials haven't expired
- Test: Log in to repository web UI manually

**"Signature verification failed"**
- Check: `SIGNING_KEY` is complete (including BEGIN/END markers)
- Verify: `SIGNING_PASSWORD` is correct
- Try: Re-export GPG key and update secret

**"Repository not found"**
- Check: Repository URLs in `project.yml` are correct
- Verify: Repository exists and you have access
- Test: Try accessing URL in browser

### Skip Signing (Local Development)

For testing without signing:

```bash
./gradlew publish -PskipSigning=true
```

## Best Practices

### Security

- ✅ Always use GitHub Actions secrets for credentials
- ✅ Never commit credentials to version control
- ✅ Use API tokens instead of passwords when possible
- ✅ Rotate credentials regularly
- ✅ Use minimum required permissions

### Versioning

- ✅ Follow semantic versioning (MAJOR.MINOR.PATCH)
- ✅ Use `-SNAPSHOT` for development versions
- ✅ Tag all releases in Git
- ✅ Keep CHANGELOG.md updated

### Release Process

- ✅ Test locally with `publishToMavenLocal` first
- ✅ Run all tests and API validation
- ✅ Update documentation before releasing
- ✅ Let CI/CD handle publishing (don't publish from local)
- ✅ Verify publication after release

### Multi-Repository Strategy

**Public + Private:**
```yaml
# Maven Central for public releases
# GitHub Packages for private snapshots
repositories:
  maven_central:
    enabled: true
  github_packages:
    enabled: true
```

**Benefits:**
- Public users get stable releases from Maven Central
- Team gets fast snapshot updates from GitHub Packages
- Keep development versions private

## Quick Reference

### Check Configuration

```bash
# Validate
python3 scripts/get-publishing-config.py --validate

# List enabled repos
python3 scripts/get-publishing-config.py --list-enabled

# Get repo config
python3 scripts/get-publishing-config.py --repository maven_central

# Check required secrets
python3 scripts/get-publishing-config.py --required-secrets maven_central
```

### Publish Commands

```bash
# Local Maven repository (testing)
./gradlew publishToMavenLocal

# All configured repositories
./gradlew publish

# Skip signing (local dev)
./gradlew publish -PskipSigning=true
```

### Update Version

```properties
# gradle.properties
VERSION_NAME=1.0.0           # Release
VERSION_NAME=1.0.0-SNAPSHOT  # Development
VERSION_NAME=1.0.0-alpha.1   # Pre-release
```

## Documentation Links

- [Publishing Overview](../../../docs/docs/development/publishing.md)
- [Maven Central Guide](../../../docs/docs/development/publishing-maven-central.md)
- [GitHub Packages Guide](../../../docs/docs/development/publishing-github-packages.md)
- [Custom Maven Guide](../../../docs/docs/development/publishing-custom-maven.md)
- [Cloud Services Guide](../../../docs/docs/development/publishing-cloud-services.md)
