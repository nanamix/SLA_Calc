"""
서비스 관리 서비스 단순 테스트
"""

import pytest
import sys
import os
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.데이터베이스설정 import 베이스모델
from services.서비스관리서비스 import 서비스관리서비스
from models.서비스모델 import 서비스생성요청, 서비스타입열거형

# 테스트용 인메모리 SQLite 데이터베이스 URL
테스트_데이터베이스_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """세션 범위의 이벤트 루프 생성"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def 테스트_엔진():
    """테스트용 데이터베이스 엔진 생성"""
    엔진 = create_async_engine(
        테스트_데이터베이스_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
    # 테이블 생성
    async with 엔진.begin() as conn:
        await conn.run_sync(베이스모델.metadata.create_all)
    
    yield 엔진
    
    # 정리
    await 엔진.dispose()


@pytest.fixture
async def 테스트_세션(테스트_엔진):
    """테스트용 데이터베이스 세션 생성"""
    세션팩토리 = async_sessionmaker(
        테스트_엔진,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with 세션팩토리() as 세션:
        yield 세션
        await 세션.rollback()


@pytest.fixture
def 샘플_서비스_데이터():
    """테스트용 샘플 서비스 데이터"""
    return {
        "이름": "테스트 웹 서비스",
        "설명": "테스트용 웹 서비스입니다",
        "목표SLA": 99.9,
        "서비스타입": "web",
        "모니터링설정": {
            "엔드포인트": "https://api.example.com/health",
            "체크간격": 60,
            "타임아웃": 30
        },
        "소유자아이디": "550e8400-e29b-41d4-a716-446655440000"
    }


class Test서비스관리서비스:
    """서비스 관리 서비스 테스트 클래스"""

    @pytest.mark.asyncio
    async def test_서비스_생성_성공(self, 테스트_세션, 샘플_서비스_데이터):
        """서비스 생성 성공 테스트"""
        서비스관리 = 서비스관리서비스(테스트_세션)
        생성요청 = 서비스생성요청(**샘플_서비스_데이터)
        
        생성된서비스 = await 서비스관리.서비스생성(생성요청)
        
        assert 생성된서비스.이름 == 샘플_서비스_데이터["이름"]
        assert 생성된서비스.설명 == 샘플_서비스_데이터["설명"]
        assert 생성된서비스.목표SLA == 샘플_서비스_데이터["목표SLA"]
        assert 생성된서비스.서비스타입 == 샘플_서비스_데이터["서비스타입"]
        assert 생성된서비스.활성여부 is True
        assert 생성된서비스.아이디 is not None

    @pytest.mark.asyncio
    async def test_중복_서비스이름_생성_실패(self, 테스트_세션, 샘플_서비스_데이터):
        """중복된 서비스 이름으로 생성 시 실패 테스트"""
        서비스관리 = 서비스관리서비스(테스트_세션)
        생성요청 = 서비스생성요청(**샘플_서비스_데이터)
        
        # 첫 번째 서비스 생성
        await 서비스관리.서비스생성(생성요청)
        
        # 같은 이름으로 두 번째 서비스 생성 시도
        with pytest.raises(ValueError) as 예외정보:
            await 서비스관리.서비스생성(생성요청)
        
        assert "이미 존재합니다" in str(예외정보.value)

    @pytest.mark.asyncio
    async def test_서비스_조회_성공(self, 테스트_세션, 샘플_서비스_데이터):
        """서비스 조회 성공 테스트"""
        서비스관리 = 서비스관리서비스(테스트_세션)
        생성요청 = 서비스생성요청(**샘플_서비스_데이터)
        
        # 서비스 생성
        생성된서비스 = await 서비스관리.서비스생성(생성요청)
        
        # 서비스 조회
        조회된서비스 = await 서비스관리.서비스조회(생성된서비스.아이디)
        
        assert 조회된서비스 is not None
        assert 조회된서비스.아이디 == 생성된서비스.아이디
        assert 조회된서비스.이름 == 생성된서비스.이름

    @pytest.mark.asyncio
    async def test_존재하지않는_서비스_조회(self, 테스트_세션):
        """존재하지 않는 서비스 조회 테스트"""
        서비스관리 = 서비스관리서비스(테스트_세션)
        존재하지않는_아이디 = str(uuid4())
        
        조회결과 = await 서비스관리.서비스조회(존재하지않는_아이디)
        
        assert 조회결과 is None