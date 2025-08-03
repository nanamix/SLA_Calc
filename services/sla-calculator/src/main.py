"""
SLA Calculator 서비스 메인 애플리케이션
FastAPI 기반 마이크로서비스
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config.데이터베이스설정 import 데이터베이스_연결_초기화, 데이터베이스_연결_종료
from controllers.서비스컨트롤러 import 서비스_라우터
from controllers.SLA계산컨트롤러 import SLA계산_라우터
from utils.캐시유틸 import 캐시관리자_초기화, 캐시관리자_종료


@asynccontextmanager
async def 애플리케이션_생명주기(app: FastAPI):
    """애플리케이션 시작/종료 시 실행되는 생명주기 관리"""
    # 시작 시 실행
    await 데이터베이스_연결_초기화()
    await 캐시관리자_초기화()
    yield
    # 종료 시 실행
    await 데이터베이스_연결_종료()
    await 캐시관리자_종료()


# FastAPI 애플리케이션 생성
app = FastAPI(
    title="SLA Calculator API",
    description="서비스 레벨 계약 자동 계산 및 모니터링 API",
    version="1.0.0",
    lifespan=애플리케이션_생명주기
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(서비스_라우터, prefix="/api/v1/services", tags=["서비스"])
app.include_router(SLA계산_라우터, tags=["SLA 계산"])


@app.get("/")
async def 루트_엔드포인트():
    """API 상태 확인 엔드포인트"""
    return {"message": "SLA Calculator API가 정상적으로 실행 중입니다"}


@app.get("/health")
async def 헬스체크():
    """헬스체크 엔드포인트"""
    return {"status": "healthy", "service": "sla-calculator"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)