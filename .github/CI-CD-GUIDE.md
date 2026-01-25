# CI/CD Pipeline Documentation

This project uses GitHub Actions for automated testing, building, and deployment.

## Workflows

### 1. CI - Build and Test (`ci.yml`)

**Trigger**: Push or PR to `main` or `develop` branches

**Jobs**:
- ✅ **Java Backend Tests**: Compile, test, and build JAR
- ✅ **Frontend Tests**: Install dependencies and build Next.js
- ✅ **Python Agent Tests**: Lint with flake8
- 🔒 **Security Scan**: Trivy vulnerability scanning

**Artifacts**: Backend JAR file (7 days retention)

---

### 2. Docker Build (`docker-build.yml`)

**Trigger**: 
- Push to `main` branch
- Version tags (`v*.*.*`)
- Manual dispatch

**What it does**:
- Builds Docker images for all 3 services
- Pushes to GitHub Container Registry (ghcr.io)
- Tags with multiple formats:
  - `latest` (for main branch)
  - `v1.2.3` (semantic version)
  - `main-abc1234` (branch + commit SHA)

**Images produced**:
```
ghcr.io/<your-username>/enterprise-rag-backend:latest
ghcr.io/<your-username>/enterprise-rag-frontend:latest
ghcr.io/<your-username>/enterprise-rag-python-agent:latest
```

---

### 3. AWS Deployment (`deploy-aws.yml`)

**Trigger**:
- Push to `main` branch
- Manual dispatch with environment selection

**What it does**:
1. Creates deployment package (docker-compose + configs)
2. Copies to EC2 via SSH
3. Pulls latest Docker images
4. Restarts services with zero-downtime
5. Runs health checks
6. Cleans up old images

**Deployment flow**:
```
GitHub → Build Package → SCP to EC2 → Pull Images → Restart Services → Health Check
```

---

### 4. Release Management (`release.yml`)

**Trigger**:
- Push version tag (`v1.0.0`, `v2.1.3`, etc.)
- Manual dispatch with version input

**What it does**:
1. Generates changelog from git commits
2. Creates GitHub Release with notes
3. Includes Docker pull commands
4. Updates VERSION file in repo

**How to create a release**:
```bash
# Create and push a tag
git tag v1.0.0
git push origin v1.0.0

# Or use GitHub UI to create a release
```

---

## Required GitHub Secrets

Configure these in: **Settings → Secrets and variables → Actions**

### AWS Deployment Secrets

| Secret | Description | Example |
|--------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS IAM access key | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret key | `wJalrXUtnFEMI/K7MDENG/...` |
| `AWS_REGION` | AWS region | `us-east-2` |
| `EC2_HOST` | EC2 public IP or DNS | `3.136.27.24` |
| `EC2_USER` | SSH username | `ubuntu` |
| `EC2_SSH_KEY` | Private SSH key | `-----BEGIN RSA PRIVATE KEY-----...` |

### Application Secrets

| Secret | Description |
|--------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for embeddings/chat |
| `JWT_SECRET` | Secret for JWT token signing |

### Automatic Secrets

| Secret | Description |
|--------|-------------|
| `GITHUB_TOKEN` | Auto-provided by GitHub Actions |

---

## Setting Up Secrets

### 1. AWS Credentials

```bash
# Create IAM user with EC2 and ECR permissions
# Download access key and add to GitHub secrets
```

### 2. EC2 SSH Key

```bash
# Get your EC2 private key
cat ~/.ssh/your-ec2-key.pem

# Copy entire content including:
# -----BEGIN RSA PRIVATE KEY-----
# ...
# -----END RSA PRIVATE KEY-----

# Paste into GitHub secret: EC2_SSH_KEY
```

### 3. OpenAI API Key

```bash
# Get from: https://platform.openai.com/api-keys
# Add to GitHub secret: OPENAI_API_KEY
```

---

## Pipeline Flow Diagram

```
┌─────────────────┐
│  Developer      │
│  git push       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   CI Workflow   │
│  - Test Java    │
│  - Test Frontend│
│  - Test Python  │
│  - Security Scan│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Docker Build   │
│  - Build images │
│  - Push to GHCR │
│  - Tag versions │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AWS Deployment │
│  - Copy files   │
│  - Pull images  │
│  - Restart      │
│  - Health check │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Production     │
│  Running on EC2 │
└─────────────────┘
```

---

## Manual Deployment

### Deploy to AWS manually

```bash
# Via GitHub UI
1. Go to Actions → Deploy to AWS EC2
2. Click "Run workflow"
3. Select environment (production/staging)
4. Click "Run workflow"
```

### Create a release

```bash
# Via Git tags
git tag v1.0.0
git push origin v1.0.0

# Via GitHub UI
1. Go to Releases → Draft a new release
2. Create new tag (e.g., v1.0.0)
3. Add release notes
4. Publish release
```

---

## Monitoring Deployments

### Check workflow status

```bash
# GitHub UI
Actions → Select workflow → View logs

# GitHub CLI
gh run list
gh run view <run-id>
```

### Check deployment on EC2

```bash
# SSH to EC2
ssh -i ~/.ssh/your-key.pem ubuntu@3.136.27.24

# Check running containers
docker ps

# Check logs
docker logs java_backend
docker logs rag_frontend

# Check health
curl http://localhost:8080/actuator/health
```

---

## Rollback Strategy

### Rollback to previous version

```bash
# SSH to EC2
ssh -i ~/.ssh/your-key.pem ubuntu@3.136.27.24

# Use specific version tag
cd deployment
docker-compose down

# Edit docker-compose.yml to use previous version
# Change: image: ghcr.io/.../backend:latest
# To:     image: ghcr.io/.../backend:v1.0.0

docker-compose up -d
```

---

## Troubleshooting

### Build fails

```bash
# Check logs in GitHub Actions UI
# Common issues:
# - Missing dependencies in pom.xml or package.json
# - Test failures
# - Security vulnerabilities
```

### Deployment fails

```bash
# Check GitHub Actions logs
# Common issues:
# - SSH key permissions (should be 600)
# - EC2 security group blocking ports
# - Missing environment variables
# - Docker registry authentication
```

### Health check fails

```bash
# SSH to EC2 and check logs
docker logs java_backend --tail=100

# Check if services are running
docker ps

# Check resources
docker stats
```

---

## Best Practices

1. **Always test locally first**
   ```bash
   docker-compose up --build
   ```

2. **Use feature branches**
   ```bash
   git checkout -b feature/new-feature
   # Work on feature
   git push origin feature/new-feature
   # Create PR to main
   ```

3. **Tag releases semantically**
   - `v1.0.0` - Major release (breaking changes)
   - `v1.1.0` - Minor release (new features)
   - `v1.1.1` - Patch release (bug fixes)

4. **Monitor after deployment**
   - Check Grafana dashboards
   - Review Prometheus alerts
   - Monitor application logs

5. **Keep secrets secure**
   - Never commit secrets to git
   - Rotate keys regularly
   - Use environment-specific secrets
