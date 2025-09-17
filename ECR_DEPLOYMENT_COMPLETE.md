# AWS ECR 완전 배포 가이드

## 🚨 중요: ChromaDB 별도 실행 필요

현재 FastAPI 애플리케이션만 ECR에 푸시했습니다. **ChromaDB는 별도로 실행해야 합니다.**

## 🏗️ 배포 아키텍처

### 현재 상황
```
┌─────────────────┐    ❌ ChromaDB 없음
│   FastAPI       │    
│   (Port 8000)   │    
│   ECR Image     │    
└─────────────────┘    
```

### 필요한 구조
```
┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │───►│    ChromaDB     │
│   (Port 8000)   │    │   (Port 8001)   │
│   ECR Image     │    │   별도 실행      │
└─────────────────┘    └─────────────────┘
```

## 🚀 배포 옵션

### Option 1: ECS에서 멀티 컨테이너 실행

#### 1. ChromaDB 컨테이너도 ECR에 푸시
```bash
# ChromaDB 이미지 태그 및 푸시
docker pull chromadb/chroma:latest
docker tag chromadb/chroma:latest [account-id].dkr.ecr.ap-northeast-2.amazonaws.com/chromadb:latest
docker push [account-id].dkr.ecr.ap-northeast-2.amazonaws.com/chromadb:latest
```

#### 2. ECS Task Definition 생성
```json
{
  "family": "decodeat-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "decodeat-api",
      "image": "[account-id].dkr.ecr.ap-northeast-2.amazonaws.com/decodeat-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "CHROMA_HOST",
          "value": "localhost"
        },
        {
          "name": "CHROMA_PORT",
          "value": "8001"
        }
      ],
      "dependsOn": [
        {
          "containerName": "chromadb",
          "condition": "HEALTHY"
        }
      ]
    },
    {
      "name": "chromadb",
      "image": "[account-id].dkr.ecr.ap-northeast-2.amazonaws.com/chromadb:latest",
      "portMappings": [
        {
          "containerPort": 8001,
          "protocol": "tcp"
        }
      ],
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:8000/api/v1/heartbeat || exit 1"
        ],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

### Option 2: 단일 컨테이너에서 실행

#### Docker Compose를 사용한 로컬 테스트
```bash
# 1. ECR 이미지로 docker-compose 수정
# 2. 로컬에서 테스트
docker-compose up -d

# 3. 테스트 후 ECS 배포
```

### Option 3: 외부 ChromaDB 서비스 사용

#### AWS에서 ChromaDB 별도 실행
```bash
# 1. EC2에 ChromaDB 설치
# 2. 환경 변수 수정
CHROMA_HOST=[chromadb-ec2-ip]
CHROMA_PORT=8000
```

## 🔧 즉시 해결 방법

### 1. 환경 변수 수정
현재 `.env` 파일에 ChromaDB 설정 추가:

```bash
# ChromaDB 설정 추가
CHROMA_HOST=localhost  # 또는 외부 ChromaDB 주소
CHROMA_PORT=8001
```

### 2. Docker 실행 시 ChromaDB 함께 실행

#### 방법 A: Docker Network 사용
```bash
# 1. Docker 네트워크 생성
docker network create decodeat-network

# 2. ChromaDB 컨테이너 실행
docker run -d \
  --name chromadb \
  --network decodeat-network \
  -p 8001:8000 \
  chromadb/chroma:latest

# 3. FastAPI 컨테이너 실행 (환경 변수 수정)
docker run -d \
  --name decodeat-api \
  --network decodeat-network \
  -p 8000:8000 \
  -e CHROMA_HOST=chromadb \
  -e CHROMA_PORT=8000 \
  [your-ecr-image]
```

#### 방법 B: Docker Compose 사용
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    networks:
      - decodeat-network

  decodeat-api:
    image: [your-ecr-image]
    ports:
      - "8000:8000"
    environment:
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8000
    depends_on:
      - chromadb
    networks:
      - decodeat-network

networks:
  decodeat-network:
    driver: bridge
```

## 🧪 테스트 방법

### 1. 헬스체크
```bash
# FastAPI 헬스체크
curl http://localhost:8000/health

# ChromaDB 헬스체크
curl http://localhost:8001/api/v1/heartbeat
```

### 2. 추천 시스템 테스트
```bash
# 벡터 서비스 테스트
curl -X POST http://localhost:8000/api/v1/recommend/user-based \
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

## ⚠️ 주의사항

1. **포트 매핑**: ChromaDB는 내부적으로 8000번 포트를 사용하지만, 외부에서는 8001번으로 매핑
2. **네트워크**: 컨테이너 간 통신을 위해 같은 네트워크에 있어야 함
3. **환경 변수**: `CHROMA_HOST`를 컨테이너 이름 또는 IP로 설정
4. **의존성**: FastAPI가 ChromaDB 시작 후에 실행되도록 설정

## 🎯 권장 배포 순서

1. **로컬 테스트**: Docker Compose로 멀티 컨테이너 테스트
2. **ECR 준비**: ChromaDB 이미지도 ECR에 푸시
3. **ECS 배포**: Task Definition으로 멀티 컨테이너 배포
4. **모니터링**: CloudWatch로 로그 및 메트릭 확인

현재 FastAPI만 ECR에 있으므로, ChromaDB를 함께 실행하는 방법을 선택해야 합니다!