"""
데이터베이스 연결 및 설정 관리
PostgreSQL 비동기 연결 설정
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator

# 데이터베이스 URL 설정
데이터베이스_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:password@localhost:5432/sla_calculator"
)

# SQLAlchemy 엔진 생성
엔진 = create_async_engine(
    데이터베이스_URL,
    echo=True,  # 개발 환경에서 SQL 쿼리 로깅
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # 연결 상태 확인
)

# 세션 팩토리 생성
비동기세션팩토리 = async_sessionmaker(
    엔진,
    class_=AsyncSession,
    expire_on_commit=False
)

# 베이스 모델 클래스
베이스모델 = declarative_base()


async def 데이터베이스_연결_초기화():
    """데이터베이스 연결 초기화"""
    try:
        # 데이터베이스 테이블 생성 (개발 환경에서만)
        if os.getenv("ENVIRONMENT") == "development":
            async with 엔진.begin() as conn:
                await conn.run_sync(베이스모델.metadata.create_all)
        print("데이터베이스 연결이 성공적으로 초기화되었습니다.")
    except Exception as e:
        print(f"데이터베이스 연결 초기화 실패: {e}")
        raise


async def 데이터베이스_연결_종료():
    """데이터베이스 연결 종료"""
    try:
        await 엔진.dispose()
        print("데이터베이스 연결이 정상적으로 종료되었습니다.")
    except Exception as e:
        print(f"데이터베이스 연결 종료 중 오류: {e}")


async def 데이터베이스세션_가져오기() -> AsyncGenerator[AsyncSession, None]:
    """
    데이터베이스 세션을 가져오는 의존성 함수
    FastAPI 의존성 주입에서 사용
    """
    async with 비동기세션팩토리() as 세션:
        try:
            yield 세션
        except Exception:
            await 세션.rollback()
            raise
        finally:
            await 세션.close()