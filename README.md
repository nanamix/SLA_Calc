# SLA Calculator - 자동 SLA 계산 애플리케이션

DevOps 팀을 위한 서비스 레벨 계약(SLA) 자동 모니터링 및 계산 도구입니다.

## 🏗️ 아키텍처

이 애플리케이션은 마이크로서비스 아키텍처를 기반으로 하며, Kubernetes + Istio 환경에서 실행됩니다.

### 서비스 구성
- **Web Dashboard**: React 기반 프론트엔드 (포트: 3000)
- **Auth Service**: 인증 서비스 (Node.js, 포트: 3001)
- **SLA Calculator**: SLA 계산 엔진 (Python FastAPI, 포트: 8000)
- **Data Collector**: 데이터 수집 서비스 (Python, 포트: 8001)
- **Notification Service**: 알림 서비스 (Node.js, 포트: 3002)
- **Report Generator**: 보고서 생성 서비스 (Python, 포트: 8002)
- **User Management**: 사용자 관리 서비스 (Node.js, 포트: 3003)

### 인프라 구성
- **PostgreSQL**: 메인 데이터베이스
- **Redis**: 캐시 및 메시지 큐
- **Nginx**: API Gateway (로컬 개발용)
- **Istio**: 서비스 메시 (프로덕션 환경)

## 🚀 빠른 시작

### 로컬 개발 환경 (Docker Compose)

1. **저장소 클론**
   ```bash
   git clone <repository-url>
   cd sla-calculator
   ```

2. **환경 변수 설정**
   ```bash
   cp .env.example .env
   # .env 파일을 편집하여 필요한 환경 변수 설정
   ```

3. **Docker Compose로 실행**
   ```bash
   # 모든 서비스 시작
   docker-compose up -d
   
   # 로그 확인
   docker-compose logs -f
   
   # 특정 서비스 재빌드
   docker-compose build [service-name]
   ```

4. **접속 확인**
   - 웹 대시보드: http://localhost:3000
   - API Gateway: http://localhost:8080
   - 개별 서비스: 각각의 포트로 접속 가능

### Kubernetes + Istio 환경

1. **Istio 설치 확인**
   ```bash
   istioctl version
   ```

2. **네임스페이스 생성 및 Istio 사이드카 주입 활성화**
   ```bash
   kubectl apply -f infrastructure/k8s/namespaces/
   kubectl label namespace sla-calculator istio-injection=enabled
   ```

3. **ConfigMaps 및 Secrets 생성**
   ```bash
   kubectl apply -f infrastructure/k8s/configmaps/
   # Secrets는 별도로 생성 필요 (보안상 Git에 포함하지 않음)
   ```

4. **애플리케이션 배포**
   ```bash
   kubectl apply -f infrastructure/k8s/deployments/
   ```

5. **Istio 설정 적용**
   ```bash
   kubectl apply -f infrastructure/istio/
   ```

6. **배포 상태 확인**
   ```bash
   kubectl get pods,svc -n sla-calculator
   istioctl proxy-status
   ```

## 📁 프로젝트 구조

```
sla-calculator/
├── services/                 # 마이크로서비스
│   ├── web-dashboard/       # React 프론트엔드
│   ├── auth-service/        # 인증 서비스
│   ├── sla-calculator/      # SLA 계산 엔진
│   ├── data-collector/      # 데이터 수집 서비스
│   ├── notification-service/ # 알림 서비스
│   ├── report-generator/    # 보고서 생성 서비스
│   └── user-management/     # 사용자 관리 서비스
├── infrastructure/          # 인프라 설정
│   ├── docker/             # Docker 관련 파일
│   ├── k8s/               # Kubernetes 매니페스트
│   ├── istio/             # Istio 설정
│   └── nginx/             # Nginx 설정
├── scripts/               # 유틸리티 스크립트
├── docker-compose.yml     # 로컬 개발 환경
└── README.md
```

## 🔧 개발 가이드

### 한글 코딩 가이드라인
- **변수명**: 한글 카멜케이스 (예: `사용자이름`, `서비스목록`)
- **함수명**: 한글 동사형 (예: `사용자생성`, `SLA계산`)
- **클래스명**: 한글 파스칼케이스 (예: `사용자관리자`, `SLA계산기`)
- **주석**: 모든 주석은 한글로 작성

### 테스트 실행
```bash
# 단위 테스트
npm test                    # Node.js 서비스
pytest                     # Python 서비스

# 통합 테스트
npm run test:integration

# E2E 테스트
npm run test:e2e
```

### 데이터베이스 관리
```bash
# 마이그레이션 실행
npm run db:migrate

# 시드 데이터 생성
npm run db:seed

# 데이터베이스 리셋
npm run db:reset
```

## 🔐 보안 설정

### Secrets 생성 (Kubernetes)
```bash
# PostgreSQL 비밀번호
kubectl create secret generic postgresql-secret \
  --from-literal=password=your-secure-password \
  -n sla-calculator

# JWT 시크릿
kubectl create secret generic auth-secrets \
  --from-literal=jwt-secret=your-jwt-secret \
  -n sla-calculator

# TLS 인증서 (HTTPS용)
kubectl create secret tls sla-calculator-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  -n sla-calculator
```

## 📊 모니터링

### Istio 기반 관찰성
- **Kiali**: 서비스 메시 시각화
- **Jaeger**: 분산 추적
- **Prometheus**: 메트릭 수집
- **Grafana**: 대시보드 및 알림

### 접속 방법
```bash
# Kiali 대시보드
istioctl dashboard kiali

# Jaeger 추적
istioctl dashboard jaeger

# Grafana 대시보드
istioctl dashboard grafana
```

## 🚨 문제 해결

### 일반적인 문제들

1. **Docker 빌드 실패**
   ```bash
   docker system prune -a
   docker-compose build --no-cache
   ```

2. **Kubernetes Pod 시작 실패**
   ```bash
   kubectl describe pod <pod-name> -n sla-calculator
   kubectl logs <pod-name> -n sla-calculator
   ```

3. **Istio 사이드카 주입 안됨**
   ```bash
   kubectl label namespace sla-calculator istio-injection=enabled --overwrite
   kubectl rollout restart deployment -n sla-calculator
   ```

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/새기능`)
3. Commit your Changes (`git commit -m '새기능 추가'`)
4. Push to the Branch (`git push origin feature/새기능`)
5. Open a Pull Request

## 📞 지원

문제가 있거나 질문이 있으시면 이슈를 생성해 주세요.