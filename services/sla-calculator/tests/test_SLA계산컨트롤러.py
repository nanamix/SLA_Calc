"""
SLA 계산 컨트롤러 API 테스트
FastAPI 엔드포인트 테스트
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import app
from models.SLA메트릭모델 import SLA메트릭응답, 메트릭타입열거형, SLA위반알림데이터


class TestSLA계산컨트롤러:
    """SLA 계산 컨트롤러 API 테스트 클래스"""

    @pytest.fixture
    def 테스트_클라이언트(self):
        """테스트 클라이언트 픽스처"""
        return TestClient(app)

    @pytest.fixture
    def 모의_SLA계산서비스(self):
        """모의 SLA 계산 서비스 픽스처"""
        return AsyncMock()

    class TestSLA메트릭_계산_API:
        """SLA 메트릭 계산 API 테스트"""

        @patch('controllers.SLA계산컨트롤러.SLA계산서비스_의존성')
        def test_가용성_메트릭_계산_성공(self, 모의_의존성, 테스트_클라이언트, 모의_SLA계산서비스):
            """가용성 메트릭 계산 API 성공 테스트"""
            # Given: 모의 서비스 설정
            모의_의존성.return_value = 모의_SLA계산서비스
            
            예상_응답 = SLA메트릭응답(
                아이디="test-metric-id",
                서비스아이디="test-service-id",
                메트릭타입="availability",
                원시값=3.0,
                계산된SLA=95.0,
                목표SLA=99.9,
                위반여부=True,
                측정시작시간=datetime.now() - timedelta(hours=1),
                측정종료시간=datetime.now(),
                타임스탬프=datetime.now()
            )
            모의_SLA계산서비스.메트릭계산_및_저장.return_value = 예상_응답
            
            요청_데이터 = {
                "서비스아이디": "test-service-id",
                "메트릭타입": "availability",
                "측정시작시간": "2024-01-01T00:00:00",
                "측정종료시간": "2024-01-01T01:00:00",
                "총시간": 60.0,
                "다운타임": 3.0
            }
            
            # When: API 호출
            응답 = 테스트_클라이언트.post("/api/v1/sla/metrics/calculate", json=요청_데이터)
            
            # Then: 성공 응답 확인
            assert 응답.status_code == 201
            응답_데이터 = 응답.json()
            assert 응답_데이터["아이디"] == "test-metric-id"
            assert 응답_데이터["계산된SLA"] == 95.0
            assert 응답_데이터["위반여부"] == True

        @patch('controllers.SLA계산컨트롤러.SLA계산서비스_의존성')
        def test_응답시간_메트릭_계산_성공(self, 모의_의존성, 테스트_클라이언트, 모의_SLA계산서비스):
            """응답시간 메트릭 계산 API 성공 테스트"""
            # Given: 모의 서비스 설정
            모의_의존성.return_value = 모의_SLA계산서비스
            
            예상_응답 = SLA메트릭응답(
                아이디="test-metric-id-2",
                서비스아이디="test-service-id",
                메트릭타입="response_time",
                원시값=950.0,
                계산된SLA=95.0,
                목표SLA=99.0,
                위반여부=True,
                측정시작시간=datetime.now() - timedelta(hours=1),
                측정종료시간=datetime.now(),
                타임스탬프=datetime.now()
            )
            모의_SLA계산서비스.메트릭계산_및_저장.return_value = 예상_응답
            
            요청_데이터 = {
                "서비스아이디": "test-service-id",
                "메트릭타입": "response_time",
                "측정시작시간": "2024-01-01T00:00:00",
                "측정종료시간": "2024-01-01T01:00:00",
                "총요청수": 1000,
                "목표응답시간내_요청수": 950
            }
            
            # When: API 호출
            응답 = 테스트_클라이언트.post("/api/v1/sla/metrics/calculate", json=요청_데이터)
            
            # Then: 성공 응답 확인
            assert 응답.status_code == 201
            응답_데이터 = 응답.json()
            assert 응답_데이터["메트릭타입"] == "response_time"
            assert 응답_데이터["계산된SLA"] == 95.0

        @patch('controllers.SLA계산컨트롤러.SLA계산서비스_의존성')
        def test_처리량_메트릭_계산_성공(self, 모의_의존성, 테스트_클라이언트, 모의_SLA계산서비스):
            """처리량 메트릭 계산 API 성공 테스트"""
            # Given: 모의 서비스 설정
            모의_의존성.return_value = 모의_SLA계산서비스
            
            예상_응답 = SLA메트릭응답(
                아이디="test-metric-id-3",
                서비스아이디="test-service-id",
                메트릭타입="throughput",
                원시값=95.0,
                계산된SLA=95.0,
                목표SLA=99.0,
                위반여부=True,
                측정시작시간=datetime.now() - timedelta(hours=1),
                측정종료시간=datetime.now(),
                타임스탬프=datetime.now()
            )
            모의_SLA계산서비스.메트릭계산_및_저장.return_value = 예상_응답
            
            요청_데이터 = {
                "서비스아이디": "test-service-id",
                "메트릭타입": "throughput",
                "측정시작시간": "2024-01-01T00:00:00",
                "측정종료시간": "2024-01-01T01:00:00",
                "실제처리량": 95.0,
                "목표처리량": 100.0
            }
            
            # When: API 호출
            응답 = 테스트_클라이언트.post("/api/v1/sla/metrics/calculate", json=요청_데이터)
            
            # Then: 성공 응답 확인
            assert 응답.status_code == 201
            응답_데이터 = 응답.json()
            assert 응답_데이터["메트릭타입"] == "throughput"
            assert 응답_데이터["원시값"] == 95.0

        @patch('controllers.SLA계산컨트롤러.SLA계산서비스_의존성')
        def test_잘못된_메트릭_데이터_오류(self, 모의_의존성, 테스트_클라이언트, 모의_SLA계산서비스):
            """잘못된 메트릭 데이터 오류 테스트"""
            # Given: 모의 서비스에서 ValueError 발생
            모의_의존성.return_value = 모의_SLA계산서비스
            모의_SLA계산서비스.메트릭계산_및_저장.side_effect = ValueError("잘못된 메트릭 데이터")
            
            요청_데이터 = {
                "서비스아이디": "test-service-id",
                "메트릭타입": "availability",
                "측정시작시간": "2024-01-01T00:00:00",
                "측정종료시간": "2024-01-01T01:00:00",
                "총시간": -10.0,  # 잘못된 값
                "다운타임": 3.0
            }
            
            # When: API 호출
            응답 = 테스트_클라이언트.post("/api/v1/sla/metrics/calculate", json=요청_데이터)
            
            # Then: 400 오류 응답 확인
            assert 응답.status_code == 400
            assert "잘못된 메트릭 데이터" in 응답.json()["detail"]

    class Test서비스_최신SLA_조회_API:
        """서비스 최신 SLA 조회 API 테스트"""

        @patch('controllers.SLA계산컨트롤러.SLA계산서비스_의존성')
        def test_서비스_최신SLA_조회_성공(self, 모의_의존성, 테스트_클라이언트, 모의_SLA계산서비스):
            """서비스 최신 SLA 조회 API 성공 테스트"""
            # Given: 모의 서비스 설정
            모의_의존성.return_value = 모의_SLA계산서비스
            
            예상_메트릭목록 = [
                SLA메트릭응답(
                    아이디="metric-1",
                    서비스아이디="test-service-id",
                    메트릭타입="availability",
                    원시값=1.5,
                    계산된SLA=97.5,
                    목표SLA=99.9,
                    위반여부=True,
                    측정시작시간=datetime.now() - timedelta(hours=1),
                    측정종료시간=datetime.now(),
                    타임스탬프=datetime.now()
                ),
                SLA메트릭응답(
                    아이디="metric-2",
                    서비스아이디="test-service-id",
                    메트릭타입="response_time",
                    원시값=980.0,
                    계산된SLA=98.0,
                    목표SLA=95.0,
                    위반여부=False,
                    측정시작시간=datetime.now() - timedelta(hours=1),
                    측정종료시간=datetime.now(),
                    타임스탬프=datetime.now()
                )
            ]
            모의_SLA계산서비스.서비스_최신SLA조회.return_value = 예상_메트릭목록
            
            # When: API 호출
            응답 = 테스트_클라이언트.get("/api/v1/sla/metrics/service/test-service-id")
            
            # Then: 성공 응답 확인
            assert 응답.status_code == 200
            응답_데이터 = 응답.json()
            assert len(응답_데이터) == 2
            assert 응답_데이터[0]["메트릭타입"] == "availability"
            assert 응답_데이터[1]["메트릭타입"] == "response_time"

        @patch('controllers.SLA계산컨트롤러.SLA계산서비스_의존성')
        def test_특정_메트릭타입_조회(self, 모의_의존성, 테스트_클라이언트, 모의_SLA계산서비스):
            """특정 메트릭 타입 조회 테스트"""
            # Given: 모의 서비스 설정
            모의_의존성.return_value = 모의_SLA계산서비스
            
            예상_메트릭목록 = [
                SLA메트릭응답(
                    아이디="metric-1",
                    서비스아이디="test-service-id",
                    메트릭타입="availability",
                    원시값=1.5,
                    계산된SLA=97.5,
                    목표SLA=99.9,
                    위반여부=True,
                    측정시작시간=datetime.now() - timedelta(hours=1),
                    측정종료시간=datetime.now(),
                    타임스탬프=datetime.now()
                )
            ]
            모의_SLA계산서비스.서비스_최신SLA조회.return_value = 예상_메트릭목록
            
            # When: 특정 메트릭 타입으로 API 호출
            응답 = 테스트_클라이언트.get("/api/v1/sla/metrics/service/test-service-id?메트릭타입=availability")
            
            # Then: 성공 응답 확인
            assert 응답.status_code == 200
            응답_데이터 = 응답.json()
            assert len(응답_데이터) == 1
            assert 응답_데이터[0]["메트릭타입"] == "availability"

        @patch('controllers.SLA계산컨트롤러.SLA계산서비스_의존성')
        def test_메트릭_없는_서비스_조회(self, 모의_의존성, 테스트_클라이언트, 모의_SLA계산서비스):
            """메트릭이 없는 서비스 조회 테스트"""
            # Given: 모의 서비스에서 빈 목록 반환
            모의_의존성.return_value = 모의_SLA계산서비스
            모의_SLA계산서비스.서비스_최신SLA조회.return_value = []
            
            # When: API 호출
            응답 = 테스트_클라이언트.get("/api/v1/sla/metrics/service/empty-service-id")
            
            # Then: 빈 목록 응답 확인
            assert 응답.status_code == 200
            응답_데이터 = 응답.json()
            assert len(응답_데이터) == 0

    class TestSLA위반_감지_API:
        """SLA 위반 감지 API 테스트"""

        @patch('controllers.SLA계산컨트롤러.SLA계산서비스_의존성')
        def test_SLA위반_감지_성공(self, 모의_의존성, 테스트_클라이언트, 모의_SLA계산서비스):
            """SLA 위반 감지 API 성공 테스트"""
            # Given: 모의 서비스 설정
            모의_의존성.return_value = 모의_SLA계산서비스
            
            예상_위반목록 = [
                SLA위반알림데이터(
                    서비스아이디="test-service-id",
                    서비스이름="테스트 서비스",
                    메트릭타입="availability",
                    계산된SLA=97.5,
                    목표SLA=99.9,
                    위반시간=datetime.now(),
                    위반정도=2.4
                )
            ]
            모의_SLA계산서비스.SLA위반_감지.return_value = 예상_위반목록
            
            # When: API 호출
            응답 = 테스트_클라이언트.get("/api/v1/sla/violations/service/test-service-id")
            
            # Then: 성공 응답 확인
            assert 응답.status_code == 200
            응답_데이터 = 응답.json()
            assert len(응답_데이터) == 1
            assert 응답_데이터[0]["서비스이름"] == "테스트 서비스"
            assert 응답_데이터[0]["위반정도"] == 2.4

        @patch('controllers.SLA계산컨트롤러.SLA계산서비스_의존성')
        def test_사용자정의_시간범위_위반감지(self, 모의_의존성, 테스트_클라이언트, 모의_SLA계산서비스):
            """사용자 정의 시간 범위 위반 감지 테스트"""
            # Given: 모의 서비스 설정
            모의_의존성.return_value = 모의_SLA계산서비스
            모의_SLA계산서비스.SLA위반_감지.return_value = []
            
            # When: 사용자 정의 시간 범위로 API 호출
            응답 = 테스트_클라이언트.get("/api/v1/sla/violations/service/test-service-id?시간범위_분=120")
            
            # Then: 성공 응답 확인
            assert 응답.status_code == 200
            # 모의 서비스가 올바른 시간 범위로 호출되었는지 확인
            모의_SLA계산서비스.SLA위반_감지.assert_called_once_with("test-service-id", 120)

        @patch('controllers.SLA계산컨트롤러.SLA계산서비스_의존성')
        def test_위반_없는_경우(self, 모의_의존성, 테스트_클라이언트, 모의_SLA계산서비스):
            """SLA 위반이 없는 경우 테스트"""
            # Given: 모의 서비스에서 빈 목록 반환
            모의_의존성.return_value = 모의_SLA계산서비스
            모의_SLA계산서비스.SLA위반_감지.return_value = []
            
            # When: API 호출
            응답 = 테스트_클라이언트.get("/api/v1/sla/violations/service/good-service-id")
            
            # Then: 빈 목록 응답 확인
            assert 응답.status_code == 200
            응답_데이터 = 응답.json()
            assert len(응답_데이터) == 0

    class Test계산_전용_API:
        """계산 전용 API 테스트 (저장하지 않음)"""

        @patch('controllers.SLA계산컨트롤러.SLA계산서비스_의존성')
        def test_가용성_계산_전용_API(self, 모의_의존성, 테스트_클라이언트, 모의_SLA계산서비스):
            """가용성 계산 전용 API 테스트"""
            # Given: 모의 서비스 설정
            모의_의존성.return_value = 모의_SLA계산서비스
            모의_SLA계산서비스.가용성계산.return_value = (3.0, 95.0)
            
            # When: API 호출
            응답 = 테스트_클라이언트.post("/api/v1/sla/calculate/availability?총시간=60.0&다운타임=3.0")
            
            # Then: 성공 응답 확인
            assert 응답.status_code == 200
            응답_데이터 = 응답.json()
            assert 응답_데이터["메트릭타입"] == "가용성"
            assert 응답_데이터["가용성백분율"] == 95.0
            assert 응답_데이터["총시간_분"] == 60.0
            assert 응답_데이터["다운타임_분"] == 3.0

        @patch('controllers.SLA계산컨트롤러.SLA계산서비스_의존성')
        def test_응답시간_계산_전용_API(self, 모의_의존성, 테스트_클라이언트, 모의_SLA계산서비스):
            """응답시간 계산 전용 API 테스트"""
            # Given: 모의 서비스 설정
            모의_의존성.return_value = 모의_SLA계산서비스
            모의_SLA계산서비스.응답시간계산.return_value = (950.0, 95.0)
            
            # When: API 호출
            응답 = 테스트_클라이언트.post("/api/v1/sla/calculate/response-time?총요청수=1000&목표응답시간내_요청수=950")
            
            # Then: 성공 응답 확인
            assert 응답.status_code == 200
            응답_데이터 = 응답.json()
            assert 응답_데이터["메트릭타입"] == "응답시간"
            assert 응답_데이터["응답시간SLA백분율"] == 95.0
            assert 응답_데이터["총요청수"] == 1000
            assert 응답_데이터["목표응답시간내_요청수"] == 950

        @patch('controllers.SLA계산컨트롤러.SLA계산서비스_의존성')
        def test_처리량_계산_전용_API(self, 모의_의존성, 테스트_클라이언트, 모의_SLA계산서비스):
            """처리량 계산 전용 API 테스트"""
            # Given: 모의 서비스 설정
            모의_의존성.return_value = 모의_SLA계산서비스
            모의_SLA계산서비스.처리량계산.return_value = (95.0, 95.0)
            
            # When: API 호출
            응답 = 테스트_클라이언트.post("/api/v1/sla/calculate/throughput?실제처리량=95.0&목표처리량=100.0")
            
            # Then: 성공 응답 확인
            assert 응답.status_code == 200
            응답_데이터 = 응답.json()
            assert 응답_데이터["메트릭타입"] == "처리량"
            assert 응답_데이터["처리량SLA백분율"] == 95.0
            assert 응답_데이터["실제처리량"] == 95.0
            assert 응답_데이터["목표처리량"] == 100.0

        def test_잘못된_가용성_계산_매개변수(self, 테스트_클라이언트):
            """잘못된 가용성 계산 매개변수 테스트"""
            # When: 다운타임이 총시간을 초과하는 경우
            응답 = 테스트_클라이언트.post("/api/v1/sla/calculate/availability?총시간=60.0&다운타임=70.0")
            
            # Then: 400 오류 응답 확인
            assert 응답.status_code == 400
            assert "다운타임은 총 시간을 초과할 수 없습니다" in 응답.json()["detail"]

        def test_잘못된_응답시간_계산_매개변수(self, 테스트_클라이언트):
            """잘못된 응답시간 계산 매개변수 테스트"""
            # When: 목표 응답시간 내 요청수가 총요청수를 초과하는 경우
            응답 = 테스트_클라이언트.post("/api/v1/sla/calculate/response-time?총요청수=100&목표응답시간내_요청수=150")
            
            # Then: 400 오류 응답 확인
            assert 응답.status_code == 400
            assert "목표 응답시간 내 요청수는 총 요청수를 초과할 수 없습니다" in 응답.json()["detail"]