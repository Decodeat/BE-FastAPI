# Docker 디스크 공간 부족 해결 가이드

## 🚨 오류 분석
```
ERROR: failed to register layer: write /opt/venv/lib/python3.11/site-packages/kubernetes/client/api/__pycache__/core_v1_api.cpython-311.pyc: no space left on device
```

이 오류는 Docker 빌드 중 디스크 공간이 부족해서 발생합니다.

## 🔍 디스크 사용량 확인

```bash
# 전체 디스크 사용량 확인
df -h

# Docker 디스크 사용량 확인
docker system df

# Docker 상세 사용량
docker system df -v
```

## 🧹 즉시 해결 방법

### 1. Docker 시스템 정리 (가장 효과적)

```bash
# 사용하지 않는 모든 Docker 리소스 정리
docker system prune -a --volumes

# 확인 후 실행 (y 입력)
# WARNING! This will remove:
#   - all stopped containers
#   - all networks not used by at least one container
#   - all volumes not used by at least one container
#   - all images without at least one container associated to them
#   - all build cache
```

### 2. 단계별 정리 (신중한 방법)

```bash
# 1. 중지된 컨테이너 정리
docker container prune

# 2. 사용하지 않는 이미지 정리
docker image prune -a

# 3. 사용하지 않는 볼륨 정리
docker volume prune

# 4. 사용하지 않는 네트워크 정리
docker network prune

# 5. 빌드 캐시 정리
docker builder prune -a
```

### 3. 특정 이미지/컨테이너 정리

```bash
# 모든 컨테이너 중지 및 삭제
docker stop $(docker ps -aq)
docker rm $(docker ps -aq)

# 모든 이미지 삭제 (주의!)
docker rmi $(docker images -q)

# 특정 이미지만 삭제
docker images
docker rmi [IMAGE_ID]
```

## 🔧 Dockerfile 최적화

현재 Dockerfile을 더 효율적으로 수정:

```dockerfile
# Multi-stage build for optimized production image
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    find /opt/venv -name "*.pyc" -delete && \
    find /opt/venv -name "__pycache__" -type d -exec rm -rf {} + || true

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN groupadd -r decodeat && useradd -r -g decodeat decodeat

# Set working directory
WORKDIR /app

# Copy application code (exclude unnecessary files)
COPY --chown=decodeat:decodeat decodeat/ ./decodeat/
COPY --chown=decodeat:decodeat main.py ./
COPY --chown=decodeat:decodeat gcp-key.json ./

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/cache && \
    chown -R decodeat:decodeat /app

# Switch to non-root user
USER decodeat

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

## 📦 .dockerignore 파일 생성

불필요한 파일들을 빌드에서 제외:

```bash
cat > .dockerignore << 'EOF'
# Git
.git
.gitignore

# Python
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis

# Virtual environments
venv/
ENV/
env/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Project specific
docs/
examples/
tests/
scripts/
*.md
!README.md

# Logs
logs/
*.log

# Cache
cache/
.cache/

# Temporary files
tmp/
temp/
EOF
```

## 🚀 최적화된 빌드 명령어

```bash
# 1. 디스크 정리
docker system prune -a

# 2. 빌드 캐시 없이 빌드
docker build --no-cache --platform linux/amd64 -t decodeat-python-server .

# 3. 또는 멀티스테이지 빌드 최적화
docker build --target production --platform linux/amd64 -t decodeat-python-server .
```

## 💾 디스크 공간 모니터링

```bash
# 빌드 전 공간 확인
echo "=== 빌드 전 디스크 사용량 ==="
df -h
docker system df

# 빌드 실행
docker build --platform linux/amd64 -t decodeat-python-server .

# 빌드 후 공간 확인
echo "=== 빌드 후 디스크 사용량 ==="
df -h
docker system df
```

## 🔄 대안 방법

### 1. GitHub Actions 사용
```yaml
# .github/workflows/build-and-push.yml
name: Build and Push to ECR

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v1
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ap-northeast-2

    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1

    - name: Build and push
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        ECR_REPOSITORY: decodeat-python-server
        IMAGE_TAG: latest
      run: |
        docker build --platform linux/amd64 -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
```

### 2. 클라우드 빌드 서비스 사용
- AWS CodeBuild
- Google Cloud Build
- Azure Container Registry

## 🎯 즉시 실행할 명령어

```bash
# 1. 모든 Docker 리소스 정리
docker system prune -a --volumes

# 2. 디스크 공간 확인
df -h

# 3. 다시 빌드
docker build --no-cache --platform linux/amd64 -t decodeat-python-server .

# 4. ECR에 태그 및 푸시
docker tag decodeat-python-server:latest 959315331850.dkr.ecr.ap-northeast-2.amazonaws.com/decodeat-python-server:latest
docker push 959315331850.dkr.ecr.ap-northeast-2.amazonaws.com/decodeat-python-server:latest
```

이 방법들로 디스크 공간 문제를 해결할 수 있습니다!