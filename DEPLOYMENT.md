# Decodeat API 배포 가이드

## 📋 개요
이 문서는 Decodeat 영양성분 분석 API와 추천 시스템의 Docker 기반 배포 방법을 설명합니다.

## 🏗️ 아키텍처
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │    ChromaDB     │    │     Redis       │
│   (Port 8000)   │◄──►│   (Port 8001)   │    │   (Port 6379)   │
│                 │    │                 │    │   (Optional)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 빠른 시작

### 1. 사전 요구사항
- Docker 20.10+
- Docker Compose 2.0+
- 최소 4GB RAM
- 최소 10GB 디스크 공간

### 2. 환경 설정
```bash
# 저장소 클론
git clone <repository-url>
cd decodeat-api

# 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 실제 값으로 변경

# Google Cloud 서비스 계정 키 추가
# gcp-key.json 파일을 프로젝트 루트에 배치
```

### 3. 배포 실행
```bash
# 배포 스크립트 실행
./scripts/deploy.sh
```

## 🔧 상세 배포 과정

### 1. 환경 변수 설정
`.env` 파일에서 다음 변수들을 설정하세요:

```bash
# 필수 설정
GEMINI_API_KEY=your_actual_gemini_api_key
GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-key.json

# ChromaDB 설정
CHROMA_HOST=chromadb
CHROMA_PORT=8000

# API 설정
DEBUG=false
HOST=0.0.0.0
PORT=8000
```

### 2. 서비스 구성

#### FastAPI 애플리케이션
- **포트**: 8000
- **기능**: 영양성분 분석, 추천 시스템 API
- **헬스체크**: `GET /health`
- **문서**: `GET /docs`

#### ChromaDB
- **포트**: 8001
- **기능**: 벡터 데이터베이스
- **헬스체크**: `GET /api/v1/heartbeat`
- **데이터 저장**: Docker 볼륨 (`chromadb_data`)

#### Redis (선택사항)
- **포트**: 6379
- **기능**: 캐싱 (향후 확장용)
- **데이터 저장**: Docker 볼륨 (`redis_data`)

### 3. Docker Compose 명령어

```bash
# 서비스 시작
docker-compose up -d

# 서비스 중지
docker-compose down

# 로그 확인
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f decodeat-api

# 서비스 재시작
docker-compose restart

# 이미지 재빌드
docker-compose build --no-cache

# 볼륨 포함 완전 삭제
docker-compose down -v
```

## 🔍 모니터링 및 헬스체크

### 헬스체크 엔드포인트
```bash
# FastAPI 헬스체크
curl http://localhost:8000/health

# ChromaDB 헬스체크
curl http://localhost:8001/api/v1/heartbeat

# Redis 헬스체크 (선택사항)
docker exec decodeat-redis redis-cli ping
```

### 로그 모니터링
```bash
# 모든 서비스 로그
docker-compose logs -f

# 실시간 로그 (최근 100줄)
docker-compose logs --tail=100 -f

# 특정 시간 이후 로그
docker-compose logs --since="2024-01-01T00:00:00Z"
```

## 🛠️ 개발 환경 설정

### 로컬 개발
```bash
# 개발 환경 시작
./scripts/dev.sh

# 테스트 포함 개발 환경
./scripts/dev.sh --test
```

### 개발 모드 특징
- 코드 변경 시 자동 재로드
- 디버그 모드 활성화
- 로컬 ChromaDB 컨테이너 사용
- 상세한 로깅

## 🔒 보안 설정

### 프로덕션 보안 체크리스트
- [ ] `.env` 파일에 실제 API 키 설정
- [ ] `gcp-key.json` 파일 권한 확인 (600)
- [ ] CORS 설정을 프로덕션 도메인으로 제한
- [ ] 비루트 사용자로 컨테이너 실행
- [ ] 불필요한 포트 노출 제거
- [ ] SSL/TLS 인증서 설정 (리버스 프록시)

### 환경 변수 보안
```bash
# 민감한 정보는 Docker secrets 사용 권장
echo "your_api_key" | docker secret create gemini_api_key -

# 또는 외부 키 관리 시스템 사용
# - AWS Secrets Manager
# - Azure Key Vault
# - Google Secret Manager
```

## 📊 성능 최적화

### 리소스 제한 설정
```yaml
# docker-compose.yml에 추가
services:
  decodeat-api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

### 캐싱 최적화
- Redis 캐시 활성화
- ChromaDB 인덱스 최적화
- 애플리케이션 레벨 캐싱

## 🚨 문제 해결

### 일반적인 문제들

#### 1. ChromaDB 연결 실패
```bash
# ChromaDB 컨테이너 상태 확인
docker-compose ps chromadb

# ChromaDB 로그 확인
docker-compose logs chromadb

# 포트 충돌 확인
netstat -tulpn | grep 8001
```

#### 2. API 응답 없음
```bash
# FastAPI 컨테이너 상태 확인
docker-compose ps decodeat-api

# 애플리케이션 로그 확인
docker-compose logs decodeat-api

# 컨테이너 내부 접근
docker exec -it decodeat-api bash
```

#### 3. 메모리 부족
```bash
# 메모리 사용량 확인
docker stats

# 불필요한 컨테이너 정리
docker system prune -a
```

#### 4. 디스크 공간 부족
```bash
# Docker 디스크 사용량 확인
docker system df

# 사용하지 않는 볼륨 정리
docker volume prune
```

### 로그 레벨 조정
```bash
# .env 파일에서 로그 레벨 변경
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

## 🔄 업데이트 및 백업

### 애플리케이션 업데이트
```bash
# 새 버전 배포
git pull origin main
docker-compose build --no-cache
docker-compose up -d
```

### 데이터 백업
```bash
# ChromaDB 데이터 백업
docker run --rm -v decodeat_chromadb_data:/data -v $(pwd):/backup alpine tar czf /backup/chromadb-backup.tar.gz -C /data .

# Redis 데이터 백업 (선택사항)
docker exec decodeat-redis redis-cli BGSAVE
docker cp decodeat-redis:/data/dump.rdb ./redis-backup.rdb
```

### 데이터 복원
```bash
# ChromaDB 데이터 복원
docker run --rm -v decodeat_chromadb_data:/data -v $(pwd):/backup alpine tar xzf /backup/chromadb-backup.tar.gz -C /data
```

## 📈 스케일링

### 수평 스케일링
```yaml
# docker-compose.yml
services:
  decodeat-api:
    deploy:
      replicas: 3
    ports:
      - "8000-8002:8000"
```

### 로드 밸런서 설정
- Nginx 또는 HAProxy 사용
- 헬스체크 기반 라우팅
- 세션 어피니티 설정

## 📞 지원

### 문제 보고
- GitHub Issues 사용
- 로그 파일 첨부
- 환경 정보 포함

### 모니터링 도구
- Prometheus + Grafana
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Docker 네이티브 모니터링

## 📝 참고 자료
- [Docker Compose 문서](https://docs.docker.com/compose/)
- [FastAPI 배포 가이드](https://fastapi.tiangolo.com/deployment/)
- [ChromaDB 문서](https://docs.trychroma.com/)
- [Redis 문서](https://redis.io/documentation)