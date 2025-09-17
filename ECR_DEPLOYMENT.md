# AWS ECR 배포 가이드

## 📋 개요
이 문서는 Decodeat API를 AWS ECR(Elastic Container Registry)에 배포하는 방법을 설명합니다.

## 🏗️ ECR 배포 아키텍처
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Local Build   │───►│   AWS ECR       │───►│   ECS/EKS       │
│   Docker Image  │    │   Repository    │    │   Deployment    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 ECR 배포 단계

### 1. 사전 요구사항
- AWS CLI 설치 및 구성
- Docker 설치
- AWS 계정 및 적절한 권한
- ECR 리포지토리 생성

### 2. AWS CLI 설정
```bash
# AWS CLI 설치 (macOS)
brew install awscli

# AWS 자격 증명 구성
aws configure
# AWS Access Key ID: [your-access-key]
# AWS Secret Access Key: [your-secret-key]
# Default region name: [ap-northeast-2]
# Default output format: [json]

# 자격 증명 확인
aws sts get-caller-identity
```

### 3. ECR 리포지토리 생성
```bash
# ECR 리포지토리 생성
aws ecr create-repository \
    --repository-name decodeat-api \
    --region ap-northeast-2

# 리포지토리 목록 확인
aws ecr describe-repositories --region ap-northeast-2
```

### 4. Docker 이미지 빌드 및 푸시

#### 자동 배포 스크립트 생성