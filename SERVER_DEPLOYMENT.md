# 서버에서 ECR 이미지 실행 가이드

## 🚀 서버에서 ECR 이미지 실행 방법

### 1. 서버에서 AWS CLI 설정 및 ECR 로그인

```bash
# AWS CLI 설치 (Ubuntu/Debian)
sudo apt update
sudo apt install awscli -y

# 또는 최신 버전 설치
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# AWS 자격 증명 설정
aws configure
# AWS Access Key ID: [your-access-key]
# AWS Secret Access Key: [your-secret-key]
# Default region name: ap-northeast-2
# Default output format: json

# ECR 로그인
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin 959315331850.dkr.ecr.ap-northeast-2.amazonaws.com
```

### 2. 이미지 Pull 및 실행

#### Option A: FastAPI만 실행 (ChromaDB 없이 - 제한적 기능)
```bash
# ECR에서 이미지 Pull
docker pull 959315331850.dkr.ecr.ap-northeast-2.amazonaws.com/decodeat-python-server:latest

# 환경 변수 파일 생성
cat > .env << EOF
GEMINI_API_KEY=AIzaSyBryq5KrYjkCB9k4WbdUYFYHN5Mk-Q59C8
GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-key.json
DEBUG=false
HOST=0.0.0.0
PORT=8000
CHROMA_HOST=localhost
CHROMA_PORT=8001
EOF

# FastAPI 컨테이너 실행
docker run -d \
  --name decodeat-api \
  -p 8000:8000 \
  --env-file .env \
  959315331850.dkr.ecr.ap-northeast-2.amazonaws.com/decodeat-python-server:latest
```

#### Option B: ChromaDB와 함께 실행 (권장)
```bash
# 1. Docker 네트워크 생성
docker network create decodeat-network

# 2. ChromaDB 컨테이너 실행
docker run -d \
  --name chromadb \
  --network decodeat-network \
  -p 8001:8000 \
  -v chromadb_data:/chroma/chroma \
  chromadb/chroma:latest

# 3. ChromaDB 헬스체크 (30초 정도 대기)
sleep 30
curl http://localhost:8001/api/v1/heartbeat

# 4. FastAPI 컨테이너 실행
docker run -d \
  --name decodeat-api \
  --network decodeat-network \
  -p 8000:8000 \
  -e GEMINI_API_KEY=AIzaSyBryq5KrYjkCB9k4WbdUYFYHN5Mk-Q59C8 \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-key.json \
  -e DEBUG=false \
  -e CHROMA_HOST=chromadb \
  -e CHROMA_PORT=8000 \
  959315331850.dkr.ecr.ap-northeast-2.amazonaws.com/decodeat-python-server:latest
```

#### Option C: Docker Compose 사용 (가장 권장)
```bash
# docker-compose.prod.yml 생성
cat > docker-compose.prod.yml << 'EOF'
version: '3.8'

services:
  chromadb:
    image: chromadb/chroma:latest
    container_name: decodeat-chromadb
    ports:
      - "8001:8000"
    volumes:
      - chromadb_data:/chroma/chroma
    environment:
      - CHROMA_SERVER_HOST=0.0.0.0
      - CHROMA_SERVER_HTTP_PORT=8000
      - CHROMA_SERVER_CORS_ALLOW_ORIGINS=["*"]
    networks:
      - decodeat-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/heartbeat"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  decodeat-api:
    image: 959315331850.dkr.ecr.ap-northeast-2.amazonaws.com/decodeat-python-server:latest
    container_name: decodeat-api
    ports:
      - "8000:8000"
    environment:
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8000
      - GEMINI_API_KEY=AIzaSyBryq5KrYjkCB9k4WbdUYFYHN5Mk-Q59C8
      - GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-key.json
      - DEBUG=false
    depends_on:
      chromadb:
        condition: service_healthy
    networks:
      - decodeat-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

volumes:
  chromadb_data:
    driver: local

networks:
  decodeat-network:
    driver: bridge
EOF

# Docker Compose로 실행
docker-compose -f docker-compose.prod.yml up -d
```

### 3. 서비스 확인

```bash
# 컨테이너 상태 확인
docker ps

# FastAPI 헬스체크
curl http://localhost:8000/health

# ChromaDB 헬스체크
curl http://localhost:8001/api/v1/heartbeat

# API 문서 확인
curl http://localhost:8000/docs

# 로그 확인
docker logs decodeat-api
docker logs decodeat-chromadb
```

### 4. 테스트

```bash
# 영양성분 분석 테스트
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "image_urls": ["https://example.com/nutrition-label.jpg"]
  }'

# 추천 시스템 테스트
curl -X POST "http://localhost:8000/api/v1/recommend/user-based" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "behavior_data": [
      {
        "product_id": 123,
        "behavior_type": "LIKE",
        "timestamp": "2024-01-01T00:00:00Z"
      }
    ],
    "limit": 10
  }'
```

## 🔧 자동화 스크립트

### 서버 배포 자동화 스크립트 생성
```bash
cat > deploy-server.sh << 'EOF'
#!/bin/bash

set -e

echo "🚀 서버 배포 시작..."

# ECR 로그인
echo "🔑 ECR 로그인 중..."
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin 959315331850.dkr.ecr.ap-northeast-2.amazonaws.com

# 기존 컨테이너 정리
echo "🧹 기존 컨테이너 정리 중..."
docker-compose -f docker-compose.prod.yml down || true

# 최신 이미지 Pull
echo "📥 최신 이미지 Pull 중..."
docker pull 959315331850.dkr.ecr.ap-northeast-2.amazonaws.com/decodeat-python-server:latest

# 서비스 시작
echo "🚀 서비스 시작 중..."
docker-compose -f docker-compose.prod.yml up -d

# 헬스체크 대기
echo "⏳ 서비스 시작 대기 중..."
sleep 60

# 헬스체크
echo "🔍 헬스체크 중..."
curl -f http://localhost:8000/health || exit 1
curl -f http://localhost:8001/api/v1/heartbeat || exit 1

echo "✅ 배포 완료!"
echo "📋 서비스 정보:"
echo "  - FastAPI: http://localhost:8000"
echo "  - API 문서: http://localhost:8000/docs"
echo "  - ChromaDB: http://localhost:8001"
EOF

chmod +x deploy-server.sh
```

## 🔄 업데이트 방법

```bash
# 새 버전 배포
./deploy-server.sh

# 또는 수동으로
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

## 🛠️ 문제 해결

### 로그 확인
```bash
# 모든 로그
docker-compose -f docker-compose.prod.yml logs -f

# 특정 서비스 로그
docker logs decodeat-api -f
docker logs decodeat-chromadb -f
```

### 컨테이너 재시작
```bash
# 특정 서비스 재시작
docker-compose -f docker-compose.prod.yml restart decodeat-api

# 모든 서비스 재시작
docker-compose -f docker-compose.prod.yml restart
```

### 완전 재배포
```bash
# 모든 것 정리 후 재시작
docker-compose -f docker-compose.prod.yml down -v
docker system prune -f
./deploy-server.sh
```

## 🎯 권장 실행 방법

**Docker Compose 사용 (Option C)을 강력히 권장합니다:**
1. 의존성 관리가 자동화됨
2. 헬스체크 기능 포함
3. 자동 재시작 기능
4. 로그 관리 용이
5. 업데이트 간편

이 방법으로 실행하면 완전한 기능을 사용할 수 있습니다!