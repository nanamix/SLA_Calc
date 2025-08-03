"""
SLA 계산 서비스 단위 테스트
가용성, 응답시간, 처리량 계산 로직 테스트
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.SLA계산서비스 import SLA계산서비스
from models.SLA메트릭모델 import 원시메트릭데이터, 메트릭타입열거형
from models.서비스모델 import 서비스ORM모델


class TestSLA계산서비스:
    """SLA 계산 서비스 테스트 클래스"""

    @pytest.fixture
    def 모의_데이터베이스세션(self):
        """모의 데이터베이스 세션 픽스처"""
        return AsyncMock()

    @pytest.fixture
    def 모의_캐시관리자(self):
        """모의 캐시 관리자 픽스처"""
        캐시관리자 = AsyncMock()
        캐시관리자.get.return_value = None  # 기본적으로 캐시 미스
        캐시관리자.set.return_value = True
        캐시관리자.delete.return_value = True
        return 캐시관리자

    @pytest.fixture
    def SLA계산서비스_인스턴스(self, 모의_데이터베이스세션, 모의_캐시관리자):
        """SLA 계산 서비스 인스턴스 픽스처"""
        return SLA계산서비스(모의_데이터베이스세션, 모의_캐시관리자)

    @pytest.fixture
    def 테스트_서비스(self):
        """테스트용 서비스 데이터 픽스처"""
        서비스 = MagicMock(spec=서비스ORM모델)
        서비스.아이디 = "test-service-id"
        서비스.이름 = "테스트 서비스"
        서비스.목표SLA = Decimal("99.9")
        return 서비스

    class Test가용성계산:
        """가용성 계산 테스트"""

        @pytest.mark.asyncio
        async def test_정상적인_가용성계산(self, SLA계산서비스_인스턴스):
            """정상적인 가용성 계산 테스트"""
            # Given: 총 시간 1440분(24시간), 다운타임 14.4분
            총시간 = 1440.0
            다운타임 = 14.4
            
            # When: 가용성 계산 실행
            원시값, 가용성백분율 = await SLA계산서비스_인스턴스.가용성계산(총시간, 다운타임)
            
            # Then: 99.0% 가용성이 계산되어야 함
            assert 원시값 == 다운타임
            assert 가용성백분율 == 99.0

        @pytest.mark.asyncio
        async def test_완벽한_가용성계산(self, SLA계산서비스_인스턴스):
            """완벽한 가용성 (다운타임 0) 계산 테스트"""
            # Given: 총 시간 1440분, 다운타임 0분
            총시간 = 1440.0
            다운타임 = 0.0
            
            # When: 가용성 계산 실행
            원시값, 가용성백분율 = await SLA계산서비스_인스턴스.가용성계산(총시간, 다운타임)
            
            # Then: 100% 가용성이 계산되어야 함
            assert 원시값 == 0.0
            assert 가용성백분율 == 100.0

        @pytest.mark.asyncio
        async def test_완전한_다운타임_가용성계산(self, SLA계산서비스_인스턴스):
            """완전한 다운타임 가용성 계산 테스트"""
            # Given: 총 시간과 다운타임이 동일
            총시간 = 60.0
            다운타임 = 60.0
            
            # When: 가용성 계산 실행
            원시값, 가용성백분율 = await SLA계산서비스_인스턴스.가용성계산(총시간, 다운타임)
            
            # Then: 0% 가용성이 계산되어야 함
            assert 원시값 == 60.0
            assert 가용성백분율 == 0.0

        @pytest.mark.asyncio
        async def test_잘못된_총시간_입력(self, SLA계산서비스_인스턴스):
            """잘못된 총시간 입력 테스트"""
            # Given: 총시간이 0 이하
            총시간 = 0.0
            다운타임 = 10.0
            
            # When & Then: ValueError가 발생해야 함
            with pytest.raises(ValueError, match="총 시간은 0보다 커야 합니다"):
                await SLA계산서비스_인스턴스.가용성계산(총시간, 다운타임)

        @pytest.mark.asyncio
        async def test_음수_다운타임_입력(self, SLA계산서비스_인스턴스):
            """음수 다운타임 입력 테스트"""
            # Given: 다운타임이 음수
            총시간 = 100.0
            다운타임 = -10.0
            
            # When & Then: ValueError가 발생해야 함
            with pytest.raises(ValueError, match="다운타임은 0 이상이어야 합니다"):
                await SLA계산서비스_인스턴스.가용성계산(총시간, 다운타임)

        @pytest.mark.asyncio
        async def test_다운타임이_총시간_초과(self, SLA계산서비스_인스턴스):
            """다운타임이 총시간을 초과하는 경우 테스트"""
            # Given: 다운타임이 총시간보다 큼
            총시간 = 60.0
            다운타임 = 70.0
            
            # When & Then: ValueError가 발생해야 함
            with pytest.raises(ValueError, match="다운타임은 총 시간을 초과할 수 없습니다"):
                await SLA계산서비스_인스턴스.가용성계산(총시간, 다운타임)

    class Test응답시간계산:
        """응답시간 계산 테스트"""

        @pytest.mark.asyncio
        async def test_정상적인_응답시간계산(self, SLA계산서비스_인스턴스):
            """정상적인 응답시간 계산 테스트"""
            # Given: 총 1000개 요청 중 950개가 목표 응답시간 내 처리
            총요청수 = 1000
            목표응답시간내_요청수 = 950
            
            # When: 응답시간 계산 실행
            원시값, 응답시간SLA백분율 = await SLA계산서비스_인스턴스.응답시간계산(총요청수, 목표응답시간내_요청수)
            
            # Then: 95% 응답시간 SLA가 계산되어야 함
            assert 원시값 == 950.0
            assert 응답시간SLA백분율 == 95.0

        @pytest.mark.asyncio
        async def test_완벽한_응답시간계산(self, SLA계산서비스_인스턴스):
            """완벽한 응답시간 (모든 요청이 목표 시간 내) 계산 테스트"""
            # Given: 모든 요청이 목표 응답시간 내 처리
            총요청수 = 500
            목표응답시간내_요청수 = 500
            
            # When: 응답시간 계산 실행
            원시값, 응답시간SLA백분율 = await SLA계산서비스_인스턴스.응답시간계산(총요청수, 목표응답시간내_요청수)
            
            # Then: 100% 응답시간 SLA가 계산되어야 함
            assert 원시값 == 500.0
            assert 응답시간SLA백분율 == 100.0

        @pytest.mark.asyncio
        async def test_최악의_응답시간계산(self, SLA계산서비스_인스턴스):
            """최악의 응답시간 (모든 요청이 목표 시간 초과) 계산 테스트"""
            # Given: 모든 요청이 목표 응답시간 초과
            총요청수 = 100
            목표응답시간내_요청수 = 0
            
            # When: 응답시간 계산 실행
            원시값, 응답시간SLA백분율 = await SLA계산서비스_인스턴스.응답시간계산(총요청수, 목표응답시간내_요청수)
            
            # Then: 0% 응답시간 SLA가 계산되어야 함
            assert 원시값 == 0.0
            assert 응답시간SLA백분율 == 0.0

        @pytest.mark.asyncio
        async def test_잘못된_총요청수_입력(self, SLA계산서비스_인스턴스):
            """잘못된 총요청수 입력 테스트"""
            # Given: 총요청수가 0 이하
            총요청수 = 0
            목표응답시간내_요청수 = 10
            
            # When & Then: ValueError가 발생해야 함
            with pytest.raises(ValueError, match="총 요청수는 0보다 커야 합니다"):
                await SLA계산서비스_인스턴스.응답시간계산(총요청수, 목표응답시간내_요청수)

        @pytest.mark.asyncio
        async def test_목표응답시간내_요청수가_총요청수_초과(self, SLA계산서비스_인스턴스):
            """목표 응답시간 내 요청수가 총요청수를 초과하는 경우 테스트"""
            # Given: 목표 응답시간 내 요청수가 총요청수보다 큼
            총요청수 = 100
            목표응답시간내_요청수 = 150
            
            # When & Then: ValueError가 발생해야 함
            with pytest.raises(ValueError, match="목표 응답시간 내 요청수는 총 요청수를 초과할 수 없습니다"):
                await SLA계산서비스_인스턴스.응답시간계산(총요청수, 목표응답시간내_요청수)

    class Test처리량계산:
        """처리량 계산 테스트"""

        @pytest.mark.asyncio
        async def test_정상적인_처리량계산(self, SLA계산서비스_인스턴스):
            """정상적인 처리량 계산 테스트"""
            # Given: 목표 처리량 100 req/sec, 실제 처리량 95 req/sec
            실제처리량 = 95.0
            목표처리량 = 100.0
            
            # When: 처리량 계산 실행
            원시값, 처리량SLA백분율 = await SLA계산서비스_인스턴스.처리량계산(실제처리량, 목표처리량)
            
            # Then: 95% 처리량 SLA가 계산되어야 함
            assert 원시값 == 95.0
            assert 처리량SLA백분율 == 95.0

        @pytest.mark.asyncio
        async def test_목표_초과_처리량계산(self, SLA계산서비스_인스턴스):
            """목표를 초과하는 처리량 계산 테스트"""
            # Given: 실제 처리량이 목표보다 높음
            실제처리량 = 120.0
            목표처리량 = 100.0
            
            # When: 처리량 계산 실행
            원시값, 처리량SLA백분율 = await SLA계산서비스_인스턴스.처리량계산(실제처리량, 목표처리량)
            
            # Then: 100%로 제한되어야 함 (120%가 아닌)
            assert 원시값 == 120.0
            assert 처리량SLA백분율 == 100.0

        @pytest.mark.asyncio
        async def test_처리량_0인_경우(self, SLA계산서비스_인스턴스):
            """실제 처리량이 0인 경우 테스트"""
            # Given: 실제 처리량이 0
            실제처리량 = 0.0
            목표처리량 = 100.0
            
            # When: 처리량 계산 실행
            원시값, 처리량SLA백분율 = await SLA계산서비스_인스턴스.처리량계산(실제처리량, 목표처리량)
            
            # Then: 0% 처리량 SLA가 계산되어야 함
            assert 원시값 == 0.0
            assert 처리량SLA백분율 == 0.0

        @pytest.mark.asyncio
        async def test_잘못된_목표처리량_입력(self, SLA계산서비스_인스턴스):
            """잘못된 목표처리량 입력 테스트"""
            # Given: 목표처리량이 0 이하
            실제처리량 = 50.0
            목표처리량 = 0.0
            
            # When & Then: ValueError가 발생해야 함
            with pytest.raises(ValueError, match="목표 처리량은 0보다 커야 합니다"):
                await SLA계산서비스_인스턴스.처리량계산(실제처리량, 목표처리량)

        @pytest.mark.asyncio
        async def test_음수_실제처리량_입력(self, SLA계산서비스_인스턴스):
            """음수 실제처리량 입력 테스트"""
            # Given: 실제처리량이 음수
            실제처리량 = -10.0
            목표처리량 = 100.0
            
            # When & Then: ValueError가 발생해야 함
            with pytest.raises(ValueError, match="실제 처리량은 0 이상이어야 합니다"):
                await SLA계산서비스_인스턴스.처리량계산(실제처리량, 목표처리량)

    class Test메트릭계산_및_저장:
        """메트릭 계산 및 저장 통합 테스트"""

        @pytest.mark.asyncio
        async def test_가용성_메트릭_계산_및_저장(self, SLA계산서비스_인스턴스, 모의_데이터베이스세션, 테스트_서비스):
            """가용성 메트릭 계산 및 저장 테스트"""
            # Given: 가용성 원시 데이터
            원시데이터 = 원시메트릭데이터(
                서비스아이디="test-service-id",
                메트릭타입=메트릭타입열거형.가용성,
                측정시작시간=datetime.now() - timedelta(hours=1),
                측정종료시간=datetime.now(),
                총시간=60.0,
                다운타임=3.0
            )
            
            # Mock 설정
            SLA계산서비스_인스턴스._서비스정보_조회 = AsyncMock(return_value=테스트_서비스)
            SLA계산서비스_인스턴스._서비스_SLA캐시_무효화 = AsyncMock()
            SLA계산서비스_인스턴스._SLA위반_알림처리 = AsyncMock()
            
            # When: 메트릭 계산 및 저장 실행
            결과 = await SLA계산서비스_인스턴스.메트릭계산_및_저장(원시데이터)
            
            # Then: 계산 결과가 올바르게 반환되어야 함
            assert 결과 is not None
            # 데이터베이스 세션의 add, commit, refresh가 호출되어야 함
            assert 모의_데이터베이스세션.add.called
            assert 모의_데이터베이스세션.commit.called
            assert 모의_데이터베이스세션.refresh.called

        @pytest.mark.asyncio
        async def test_존재하지_않는_서비스_오류(self, SLA계산서비스_인스턴스):
            """존재하지 않는 서비스에 대한 오류 테스트"""
            # Given: 존재하지 않는 서비스 ID
            원시데이터 = 원시메트릭데이터(
                서비스아이디="non-existent-service",
                메트릭타입=메트릭타입열거형.가용성,
                측정시작시간=datetime.now() - timedelta(hours=1),
                측정종료시간=datetime.now(),
                총시간=60.0,
                다운타임=3.0
            )
            
            # Mock 설정 (서비스 없음)
            SLA계산서비스_인스턴스._서비스정보_조회 = AsyncMock(return_value=None)
            
            # When & Then: ValueError가 발생해야 함
            with pytest.raises(ValueError, match="서비스 ID 'non-existent-service'를 찾을 수 없습니다"):
                await SLA계산서비스_인스턴스.메트릭계산_및_저장(원시데이터)

        @pytest.mark.asyncio
        async def test_잘못된_메트릭_데이터_오류(self, SLA계산서비스_인스턴스, 테스트_서비스):
            """잘못된 메트릭 데이터에 대한 오류 테스트"""
            # Given: 가용성 계산에 필요한 데이터가 누락된 원시 데이터
            원시데이터 = 원시메트릭데이터(
                서비스아이디="test-service-id",
                메트릭타입=메트릭타입열거형.가용성,
                측정시작시간=datetime.now() - timedelta(hours=1),
                측정종료시간=datetime.now()
                # 총시간, 다운타임 누락
            )
            
            # Mock 설정
            SLA계산서비스_인스턴스._서비스정보_조회 = AsyncMock(return_value=테스트_서비스)
            
            # When & Then: ValueError가 발생해야 함
            with pytest.raises(ValueError, match="가용성 계산을 위해서는 총시간과 다운타임이 필요합니다"):
                await SLA계산서비스_인스턴스.메트릭계산_및_저장(원시데이터)

    class Test캐시_기능:
        """캐시 기능 테스트"""

        @pytest.mark.asyncio
        async def test_캐시_히트_시나리오(self, SLA계산서비스_인스턴스, 모의_캐시관리자):
            """캐시 히트 시나리오 테스트"""
            # Given: 캐시에 데이터가 있는 상황
            캐시된_데이터 = [
                {
                    "아이디": "test-metric-id",
                    "서비스아이디": "test-service-id",
                    "메트릭타입": "availability",
                    "계산된SLA": 99.5
                }
            ]
            모의_캐시관리자.get.return_value = 캐시된_데이터
            
            # When: 서비스 최신 SLA 조회
            결과 = await SLA계산서비스_인스턴스.서비스_최신SLA조회("test-service-id")
            
            # Then: 캐시에서 데이터를 가져와야 함
            assert len(결과) == 1
            assert 결과[0].아이디 == "test-metric-id"
            모의_캐시관리자.get.assert_called_once()

        @pytest.mark.asyncio
        async def test_캐시_미스_시나리오(self, SLA계산서비스_인스턴스, 모의_캐시관리자, 모의_데이터베이스세션):
            """캐시 미스 시나리오 테스트"""
            # Given: 캐시에 데이터가 없는 상황
            모의_캐시관리자.get.return_value = None
            
            # 데이터베이스 쿼리 결과 모킹
            모의_결과 = AsyncMock()
            모의_결과.scalars.return_value.all.return_value = []
            모의_데이터베이스세션.execute.return_value = 모의_결과
            
            # When: 서비스 최신 SLA 조회
            결과 = await SLA계산서비스_인스턴스.서비스_최신SLA조회("test-service-id")
            
            # Then: 데이터베이스에서 조회하고 캐시에 저장해야 함
            assert 결과 == []
            모의_캐시관리자.get.assert_called_once()
            모의_캐시관리자.set.assert_called_once()
            모의_데이터베이스세션.execute.assert_called_once()

    class TestSLA위반_감지:
        """SLA 위반 감지 테스트"""

        @pytest.mark.asyncio
        async def test_SLA위반_감지_성공(self, SLA계산서비스_인스턴스, 모의_데이터베이스세션):
            """SLA 위반 감지 성공 테스트"""
            # Given: SLA 위반 데이터가 있는 상황
            모의_위반메트릭 = MagicMock()
            모의_위반메트릭.서비스아이디 = "test-service-id"
            모의_위반메트릭.메트릭타입 = "availability"
            모의_위반메트릭.계산된SLA = Decimal("98.5")
            모의_위반메트릭.목표SLA = Decimal("99.9")
            모의_위반메트릭.타임스탬프 = datetime.now()
            
            모의_결과 = AsyncMock()
            모의_결과.all.return_value = [(모의_위반메트릭, "테스트 서비스")]
            모의_데이터베이스세션.execute.return_value = 모의_결과
            
            # When: SLA 위반 감지 실행
            위반목록 = await SLA계산서비스_인스턴스.SLA위반_감지("test-service-id", 60)
            
            # Then: 위반 데이터가 반환되어야 함
            assert len(위반목록) == 1
            assert 위반목록[0].서비스아이디 == "test-service-id"
            assert 위반목록[0].서비스이름 == "테스트 서비스"
            assert 위반목록[0].위반정도 == 1.4  # 99.9 - 98.5