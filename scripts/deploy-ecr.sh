#!/bin/bash

# AWS ECR 배포 스크립트
# Usage: ./scripts/deploy-ecr.sh [region] [repository-name] [tag]

set -e

# 기본값 설정
AWS_REGION=${1:-"ap-northeast-2"}
REPOSITORY_NAME=${2:-"decodeat-api"}
IMAGE_TAG=${3:-"latest"}

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 AWS ECR 배포 시작${NC}"
echo -e "${YELLOW}Region: ${AWS_REGION}${NC}"
echo -e "${YELLOW}Repository: ${REPOSITORY_NAME}${NC}"
echo -e "${YELLOW}Tag: ${IMAGE_TAG}${NC}"

# AWS CLI 설치 확인
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI가 설치되지 않았습니다.${NC}"
    echo "설치 방법: brew install awscli"
    exit 1
fi

# Docker 설치 확인
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker가 설치되지 않았습니다.${NC}"
    exit 1
fi

# AWS 자격 증명 확인
echo -e "${BLUE}🔐 AWS 자격 증명 확인 중...${NC}"
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS 자격 증명이 설정되지 않았습니다.${NC}"
    echo "설정 방법: aws configure"
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
FULL_IMAGE_NAME="${ECR_URI}/${REPOSITORY_NAME}:${IMAGE_TAG}"

echo -e "${GREEN}✅ AWS 계정 ID: ${AWS_ACCOUNT_ID}${NC}"

# ECR 리포지토리 존재 확인 및 생성
echo -e "${BLUE}📦 ECR 리포지토리 확인 중...${NC}"
if ! aws ecr describe-repositories --repository-names ${REPOSITORY_NAME} --region ${AWS_REGION} &> /dev/null; then
    echo -e "${YELLOW}⚠️  리포지토리가 존재하지 않습니다. 생성 중...${NC}"
    aws ecr create-repository \
        --repository-name ${REPOSITORY_NAME} \
        --region ${AWS_REGION} \
        --image-scanning-configuration scanOnPush=true
    echo -e "${GREEN}✅ ECR 리포지토리 생성 완료${NC}"
else
    echo -e "${GREEN}✅ ECR 리포지토리 확인 완료${NC}"
fi

# ECR 로그인
echo -e "${BLUE}🔑 ECR 로그인 중...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}
echo -e "${GREEN}✅ ECR 로그인 완료${NC}"

# 환경 변수 파일 확인
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env 파일이 존재하지 않습니다.${NC}"
    echo "cp .env.example .env 명령으로 생성하고 값을 설정하세요."
    exit 1
fi

# GCP 키 파일 확인
if [ ! -f "gcp-key.json" ]; then
    echo -e "${RED}❌ gcp-key.json 파일이 존재하지 않습니다.${NC}"
    echo "Google Cloud 서비스 계정 키 파일을 추가하세요."
    exit 1
fi

# Docker 이미지 빌드
echo -e "${BLUE}🔨 Docker 이미지 빌드 중...${NC}"
docker build -t ${REPOSITORY_NAME}:${IMAGE_TAG} .
echo -e "${GREEN}✅ Docker 이미지 빌드 완료${NC}"

# 이미지 태그 지정
echo -e "${BLUE}🏷️  이미지 태그 지정 중...${NC}"
docker tag ${REPOSITORY_NAME}:${IMAGE_TAG} ${FULL_IMAGE_NAME}
echo -e "${GREEN}✅ 이미지 태그 지정 완료${NC}"

# ECR에 이미지 푸시
echo -e "${BLUE}📤 ECR에 이미지 푸시 중...${NC}"
docker push ${FULL_IMAGE_NAME}
echo -e "${GREEN}✅ ECR 이미지 푸시 완료${NC}"

# 이미지 정보 출력
echo -e "${BLUE}📋 배포 정보${NC}"
echo -e "${YELLOW}ECR URI: ${FULL_IMAGE_NAME}${NC}"
echo -e "${YELLOW}이미지 크기:${NC}"
docker images ${REPOSITORY_NAME}:${IMAGE_TAG} --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

# ECR 이미지 목록 확인
echo -e "${BLUE}📦 ECR 리포지토리 이미지 목록${NC}"
aws ecr list-images --repository-name ${REPOSITORY_NAME} --region ${AWS_REGION} --output table

# 로컬 이미지 정리 (선택사항)
read -p "로컬 Docker 이미지를 정리하시겠습니까? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}🧹 로컬 이미지 정리 중...${NC}"
    docker rmi ${REPOSITORY_NAME}:${IMAGE_TAG} ${FULL_IMAGE_NAME} || true
    echo -e "${GREEN}✅ 로컬 이미지 정리 완료${NC}"
fi

echo -e "${GREEN}🎉 ECR 배포 완료!${NC}"
echo -e "${BLUE}다음 단계:${NC}"
echo -e "${YELLOW}1. ECS 서비스 업데이트: aws ecs update-service --cluster [cluster-name] --service [service-name] --force-new-deployment${NC}"
echo -e "${YELLOW}2. EKS 배포 업데이트: kubectl set image deployment/decodeat-api decodeat-api=${FULL_IMAGE_NAME}${NC}"
echo -e "${YELLOW}3. 또는 docker run으로 테스트: docker run -p 8000:8000 ${FULL_IMAGE_NAME}${NC}"