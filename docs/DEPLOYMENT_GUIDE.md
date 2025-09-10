# Deployment Guide

## 배포 환경 구성

### 1. 프로덕션 환경 요구사항

#### 시스템 요구사항
- **OS**: Ubuntu 20.04 LTS 이상 또는 CentOS 8 이상
- **CPU**: 최소 2 코어, 권장 4 코어
- **RAM**: 최소 4GB, 권장 8GB
- **Storage**: 최소 20GB SSD
- **Network**: 안정적인 인터넷 연결 (Google APIs 접근 필요)

#### 소프트웨어 요구사항
- **Python**: 3.11 이상
- **Docker**: 20.10 이상 (컨테이너 배포 시)
- **Nginx**: 1.18 이상 (리버스 프록시)
- **SSL 인증서**: Let's Encrypt 또는 상용 인증서

### 2. 환경 변수 설정

#### 프로덕션 환경 변수
```bash
# .env.production
GEMINI_API_KEY=your_production_gemini_key
GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-key.json
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
WORKERS=4
MAX_REQUESTS=1000
MAX_REQUESTS_JITTER=50
```

#### 보안 설정
```bash
# 추가 보안 설정
ALLOWED_HOSTS=["yourdomain.com", "api.yourdomain.com"]
CORS_ORIGINS=["https://yourdomain.com"]
API_RATE_LIMIT=100  # 분당 요청 수
MAX_IMAGE_SIZE=10485760  # 10MB
REQUEST_TIMEOUT=120  # 2분
```

## Docker 배포

### 1. Dockerfile 최적화

#### 멀티스테이지 빌드
```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# 비root 사용자 생성
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# 빌드된 패키지 복사
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# 애플리케이션 코드 복사
COPY decodeat/ ./decodeat/
COPY gcp-key.json .

# 권한 설정
RUN chown -R appuser:appuser /app
USER appuser

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 환경 변수 설정
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-key.json
ENV PYTHONPATH=/app

EXPOSE 8000

# Gunicorn으로 실행
CMD ["gunicorn", "decodeat.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

### 2. Docker Compose 설정

#### docker-compose.prod.yml
```yaml
version: '3.8'

services:
  nutrition-api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - DEBUG=false
      - LOG_LEVEL=INFO
      - WORKERS=4
    volumes:
      - ./gcp-key.json:/app/gcp-key.json:ro
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - nutrition-api
    restart: unless-stopped

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    command: redis-server --appendonly yes

volumes:
  redis_data:
```

### 3. Nginx 설정

#### nginx.conf
```nginx
events {
    worker_connections 1024;
}

http {
    upstream nutrition_api {
        server nutrition-api:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/m;

    server {
        listen 80;
        server_name yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com;

        # SSL 설정
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
        ssl_prefer_server_ciphers off;

        # 보안 헤더
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

        # API 프록시
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://nutrition_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # 타임아웃 설정
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 120s;
            
            # 큰 요청 허용
            client_max_body_size 20M;
        }

        # 헬스체크
        location /health {
            proxy_pass http://nutrition_api;
            access_log off;
        }

        # 정적 파일 (문서)
        location /docs {
            proxy_pass http://nutrition_api;
        }

        # 기본 응답
        location / {
            return 200 '{"status": "Nutrition Label API", "version": "1.0.0"}';
            add_header Content-Type application/json;
        }
    }
}
```

## 클라우드 배포

### 1. AWS ECS 배포

#### task-definition.json
```json
{
  "family": "nutrition-label-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "nutrition-api",
      "image": "your-account.dkr.ecr.region.amazonaws.com/nutrition-label-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DEBUG",
          "value": "false"
        },
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        }
      ],
      "secrets": [
        {
          "name": "GEMINI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:gemini-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/nutrition-label-api",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:8000/health || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

#### 배포 스크립트
```bash
#!/bin/bash
# deploy-aws.sh

set -e

# 변수 설정
AWS_REGION="us-west-2"
ECR_REPOSITORY="nutrition-label-api"
CLUSTER_NAME="nutrition-api-cluster"
SERVICE_NAME="nutrition-api-service"

# ECR 로그인
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# 이미지 빌드 및 푸시
docker build -t $ECR_REPOSITORY .
docker tag $ECR_REPOSITORY:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

# ECS 서비스 업데이트
aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force-new-deployment

echo "배포 완료!"
```

### 2. Google Cloud Run 배포

#### cloudbuild.yaml
```yaml
steps:
  # Docker 이미지 빌드
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/nutrition-label-api', '.']

  # 이미지 푸시
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/nutrition-label-api']

  # Cloud Run 배포
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'nutrition-label-api'
      - '--image'
      - 'gcr.io/$PROJECT_ID/nutrition-label-api'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'
      - '--memory'
      - '2Gi'
      - '--cpu'
      - '2'
      - '--max-instances'
      - '10'
      - '--set-env-vars'
      - 'DEBUG=false,LOG_LEVEL=INFO'

images:
  - 'gcr.io/$PROJECT_ID/nutrition-label-api'
```

#### 배포 명령어
```bash
# Google Cloud 프로젝트 설정
gcloud config set project YOUR_PROJECT_ID

# Cloud Build 실행
gcloud builds submit --config cloudbuild.yaml

# 환경 변수 설정
gcloud run services update nutrition-label-api \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY \
  --region us-central1
```

## 모니터링 및 로깅

### 1. Prometheus + Grafana 설정

#### prometheus.yml
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'nutrition-api'
    static_configs:
      - targets: ['nutrition-api:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:9113']

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

#### alert_rules.yml
```yaml
groups:
  - name: nutrition-api-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(api_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"

      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m])) > 30
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }} seconds"

      - alert: ServiceDown
        expr: up{job="nutrition-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "Nutrition API service is not responding"
```

### 2. ELK Stack 로깅

#### logstash.conf
```ruby
input {
  beats {
    port => 5044
  }
}

filter {
  if [fields][service] == "nutrition-api" {
    json {
      source => "message"
    }
    
    date {
      match => [ "timestamp", "ISO8601" ]
    }
    
    mutate {
      add_field => { "service" => "nutrition-api" }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "nutrition-api-%{+YYYY.MM.dd}"
  }
}
```

#### filebeat.yml
```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /app/logs/*.log
  fields:
    service: nutrition-api
  fields_under_root: true

output.logstash:
  hosts: ["logstash:5044"]

logging.level: info
```

## 성능 최적화

### 1. 애플리케이션 최적화

#### Gunicorn 설정
```python
# gunicorn.conf.py
import multiprocessing

# 서버 소켓
bind = "0.0.0.0:8000"
backlog = 2048

# 워커 프로세스
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# 타임아웃
timeout = 120
keepalive = 2

# 로깅
accesslog = "/app/logs/access.log"
errorlog = "/app/logs/error.log"
loglevel = "info"

# 프로세스 이름
proc_name = "nutrition-api"

# 메모리 관리
preload_app = True
```

#### 캐싱 구현
```python
import redis
import json
import hashlib
from typing import Optional

class CacheService:
    """Redis 기반 캐싱 서비스."""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host='redis',
            port=6379,
            decode_responses=True
        )
    
    def _generate_key(self, prefix: str, data: str) -> str:
        """캐시 키 생성."""
        hash_obj = hashlib.md5(data.encode())
        return f"{prefix}:{hash_obj.hexdigest()}"
    
    async def get_ocr_result(self, image_hash: str) -> Optional[str]:
        """OCR 결과 캐시 조회."""
        key = self._generate_key("ocr", image_hash)
        return self.redis_client.get(key)
    
    async def set_ocr_result(self, image_hash: str, text: str, ttl: int = 3600):
        """OCR 결과 캐시 저장."""
        key = self._generate_key("ocr", image_hash)
        self.redis_client.setex(key, ttl, text)
    
    async def get_analysis_result(self, text_hash: str) -> Optional[dict]:
        """분석 결과 캐시 조회."""
        key = self._generate_key("analysis", text_hash)
        result = self.redis_client.get(key)
        return json.loads(result) if result else None
    
    async def set_analysis_result(self, text_hash: str, result: dict, ttl: int = 1800):
        """분석 결과 캐시 저장."""
        key = self._generate_key("analysis", text_hash)
        self.redis_client.setex(key, ttl, json.dumps(result))
```

### 2. 데이터베이스 최적화 (선택사항)

#### PostgreSQL 연동
```python
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class AnalysisResult(Base):
    """분석 결과 저장 테이블."""
    __tablename__ = "analysis_results"
    
    id = Column(String, primary_key=True)
    image_url = Column(String, nullable=False)
    product_name = Column(String)
    nutrition_info = Column(Text)  # JSON 형태
    ingredients = Column(Text)     # JSON 형태
    decode_status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "product_name": self.product_name,
            "nutrition_info": json.loads(self.nutrition_info) if self.nutrition_info else None,
            "ingredients": json.loads(self.ingredients) if self.ingredients else None,
            "decode_status": self.decode_status,
            "created_at": self.created_at.isoformat()
        }
```

## 보안 강화

### 1. API 보안

#### JWT 인증 (선택사항)
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """JWT 토큰 검증."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=["HS256"]
        )
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

@app.post("/api/v1/analyze")
async def analyze_nutrition_label(
    request: AnalyzeRequest,
    user: dict = Depends(verify_token)
):
    """인증이 필요한 분석 엔드포인트."""
    pass
```

#### API 키 인증
```python
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(None)):
    """API 키 검증."""
    if not x_api_key or x_api_key not in settings.valid_api_keys:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    return x_api_key
```

### 2. 네트워크 보안

#### 방화벽 설정 (Ubuntu)
```bash
# UFW 방화벽 설정
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 필요한 포트만 허용
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS

# 특정 IP에서만 접근 허용 (관리용)
sudo ufw allow from YOUR_ADMIN_IP to any port 22
```

#### SSL/TLS 설정
```bash
# Let's Encrypt 인증서 발급
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com

# 자동 갱신 설정
sudo crontab -e
# 다음 라인 추가:
# 0 12 * * * /usr/bin/certbot renew --quiet
```

## 백업 및 복구

### 1. 데이터 백업

#### 설정 파일 백업
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# 설정 파일 백업
cp .env $BACKUP_DIR/
cp docker-compose.prod.yml $BACKUP_DIR/
cp nginx.conf $BACKUP_DIR/

# 로그 파일 압축
tar -czf $BACKUP_DIR/logs.tar.gz logs/

# 인증서 백업
cp -r ssl/ $BACKUP_DIR/

echo "백업 완료: $BACKUP_DIR"
```

#### 자동 백업 설정
```bash
# crontab 설정
0 2 * * * /path/to/backup.sh

# 오래된 백업 정리 (30일 이상)
0 3 * * * find /backup -type d -mtime +30 -exec rm -rf {} \;
```

### 2. 재해 복구

#### 복구 절차
```bash
#!/bin/bash
# restore.sh

BACKUP_DATE=$1
BACKUP_DIR="/backup/$BACKUP_DATE"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "백업 디렉토리가 존재하지 않습니다: $BACKUP_DIR"
    exit 1
fi

# 서비스 중지
docker-compose down

# 설정 파일 복원
cp $BACKUP_DIR/.env .
cp $BACKUP_DIR/docker-compose.prod.yml .
cp $BACKUP_DIR/nginx.conf .

# 로그 복원
tar -xzf $BACKUP_DIR/logs.tar.gz

# 인증서 복원
cp -r $BACKUP_DIR/ssl/ .

# 서비스 재시작
docker-compose up -d

echo "복구 완료"
```

## 운영 체크리스트

### 배포 전 체크리스트

- [ ] 모든 테스트 통과 확인
- [ ] 환경 변수 설정 검증
- [ ] SSL 인증서 유효성 확인
- [ ] 백업 시스템 동작 확인
- [ ] 모니터링 시스템 설정
- [ ] 로그 수집 시스템 설정
- [ ] 보안 설정 검토
- [ ] 성능 테스트 수행
- [ ] 롤백 계획 수립

### 배포 후 체크리스트

- [ ] 헬스체크 엔드포인트 확인
- [ ] API 기능 테스트
- [ ] 응답 시간 모니터링
- [ ] 오류율 확인
- [ ] 로그 수집 상태 확인
- [ ] 메트릭 수집 상태 확인
- [ ] 알림 시스템 테스트
- [ ] 백업 시스템 테스트

### 정기 운영 작업

#### 일일 작업
- 시스템 상태 모니터링
- 오류 로그 검토
- 성능 지표 확인

#### 주간 작업
- 보안 업데이트 적용
- 백업 상태 확인
- 용량 사용량 검토

#### 월간 작업
- SSL 인증서 만료일 확인
- API 키 로테이션
- 성능 최적화 검토
- 보안 감사

이 배포 가이드는 프로덕션 환경에서 안정적이고 확장 가능한 서비스 운영을 위한 모든 필수 요소를 다룹니다.