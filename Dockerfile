# syntax=docker/dockerfile:1
FROM python:3.11-slim

# 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 작업 디렉토리 생성 및 설정
WORKDIR /app

# 시스템 패키지 설치 (필요시 추가)
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 및 패키지 설치
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# 소스 코드 복사
COPY . .

# FastAPI 실행 (포트 8000)
CMD ["uvicorn", "decodeat.main:app", "--host", "0.0.0.0", "--port", "8000"]
