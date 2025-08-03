"""
서비스 모델 단위 테스트
Pydantic 스키마 및 검증 로직 테스트
"""

import pytest
from pydantic import ValidationError

from models.서비스모델 import (
    서비스생성요청,
    서비스수정요청,
    서비스타입열거형
)


class Test서비스생성요청:
    """서비스 생성 요청 스키마 테스트"""

    def test_유효한_서비스생성요청_생성(self):
        """유효한 서비스 생성 요청 데이터로 객체 생성 테스트"""
        요청데이터 = {
            "이름": "테스트 서비스",
            "설명": "테스트용 서비스입니다",
            "목표SLA": 99.9,
            "서비스타입": "web",
            "모니터링설정": {"엔드포인트": "https://api.test.com"},
            "소유자아이디": "550e8400-e29b-41d4-a716-446655440000"
        }
        
        서비스요청 = 서비스생성요청(**요청데이터)
        
        assert 서비스요청.이름 == "테스트 서비스"
        assert 서비스요청.설명 == "테스트용 서비스입니다"
        assert 서비스요청.목표SLA == 99.9
        assert 서비스요청.서비스타입 == 서비스타입열거형.웹
        assert 서비스요청.모니터링설정 == {"엔드포인트": "https://api.test.com"}

    def test_필수필드_누락시_검증오류(self):
        """필수 필드가 누락된 경우 검증 오류 발생 테스트"""
        with pytest.raises(ValidationError) as 예외정보:
            서비스생성요청(설명="설명만 있음")
        
        오류목록 = 예외정보.value.errors()
        필수필드목록 = [오류['loc'][0] for 오류 in 오류목록]
        
        assert '이름' in 필수필드목록
        assert '목표SLA' in 필수필드목록

    def test_잘못된_SLA값_검증오류(self):
        """잘못된 SLA 값에 대한 검증 오류 테스트"""
        # 음수 SLA 값
        with pytest.raises(ValidationError) as 예외정보:
            서비스생성요청(이름="테스트", 목표SLA=-1.0)
        
        오류메시지들 = [str(오류) for 오류 in 예외정보.value.errors()]
        print(f"음수 SLA 오류 메시지들: {오류메시지들}")
        assert any("목표 SLA는 0과 100 사이의 값이어야 합니다" in 메시지 for 메시지 in 오류메시지들)
        
        # 100 초과 SLA 값
        with pytest.raises(ValidationError) as 예외정보:
            서비스생성요청(이름="테스트", 목표SLA=101.0)
        
        오류메시지들 = [str(오류) for 오류 in 예외정보.value.errors()]
        print(f"초과 SLA 오류 메시지들: {오류메시지들}")
        assert any("목표 SLA는 0과 100 사이의 값이어야 합니다" in 메시지 for 메시지 in 오류메시지들)

    def test_빈_서비스이름_검증오류(self):
        """빈 서비스 이름에 대한 검증 오류 테스트"""
        with pytest.raises(ValidationError) as 예외정보:
            서비스생성요청(이름="", 목표SLA=99.0)
        
        오류메시지들 = [str(오류) for 오류 in 예외정보.value.errors()]
        print(f"빈 이름 오류 메시지들: {오류메시지들}")
        assert any("서비스 이름은 필수입니다" in 메시지 for 메시지 in 오류메시지들)
        
        # 공백만 있는 이름
        with pytest.raises(ValidationError) as 예외정보:
            서비스생성요청(이름="   ", 목표SLA=99.0)
        
        오류메시지들 = [str(오류) for 오류 in 예외정보.value.errors()]
        print(f"공백 이름 오류 메시지들: {오류메시지들}")
        assert any("서비스 이름은 필수입니다" in 메시지 for 메시지 in 오류메시지들)

    def test_서비스이름_공백_제거(self):
        """서비스 이름의 앞뒤 공백 제거 테스트"""
        서비스요청 = 서비스생성요청(이름="  테스트 서비스  ", 목표SLA=99.0)
        assert 서비스요청.이름 == "테스트 서비스"

    def test_SLA값_반올림(self):
        """SLA 값 소수점 둘째자리 반올림 테스트"""
        서비스요청 = 서비스생성요청(이름="테스트", 목표SLA=99.999)
        assert 서비스요청.목표SLA == 100.0
        
        서비스요청2 = 서비스생성요청(이름="테스트2", 목표SLA=99.994)
        assert 서비스요청2.목표SLA == 99.99

    def test_기본값_설정(self):
        """기본값 설정 테스트"""
        서비스요청 = 서비스생성요청(이름="테스트", 목표SLA=99.0)
        
        assert 서비스요청.서비스타입 == 서비스타입열거형.웹
        assert 서비스요청.모니터링설정 == {}
        assert 서비스요청.소유자아이디 is None

    def test_잘못된_서비스타입_검증오류(self):
        """잘못된 서비스 타입에 대한 검증 오류 테스트"""
        with pytest.raises(ValidationError):
            서비스생성요청(이름="테스트", 목표SLA=99.0, 서비스타입="invalid_type")


class Test서비스수정요청:
    """서비스 수정 요청 스키마 테스트"""

    def test_부분_수정_요청(self):
        """일부 필드만 수정하는 요청 테스트"""
        수정요청 = 서비스수정요청(이름="수정된 이름", 목표SLA=98.5)
        
        assert 수정요청.이름 == "수정된 이름"
        assert 수정요청.목표SLA == 98.5
        assert 수정요청.설명 is None
        assert 수정요청.서비스타입 is None

    def test_빈_수정_요청(self):
        """아무 필드도 수정하지 않는 요청 테스트"""
        수정요청 = 서비스수정요청()
        
        assert 수정요청.이름 is None
        assert 수정요청.설명 is None
        assert 수정요청.목표SLA is None
        assert 수정요청.서비스타입 is None

    def test_잘못된_SLA값_수정_검증오류(self):
        """수정 시 잘못된 SLA 값에 대한 검증 오류 테스트"""
        with pytest.raises(ValidationError):
            서비스수정요청(목표SLA=-5.0)
        
        with pytest.raises(ValidationError):
            서비스수정요청(목표SLA=150.0)

    def test_빈_이름_수정_검증오류(self):
        """수정 시 빈 이름에 대한 검증 오류 테스트"""
        with pytest.raises(ValidationError):
            서비스수정요청(이름="")
        
        with pytest.raises(ValidationError):
            서비스수정요청(이름="   ")

    def test_활성여부_수정(self):
        """활성 여부 수정 테스트"""
        수정요청 = 서비스수정요청(활성여부=False)
        assert 수정요청.활성여부 is False
        
        수정요청2 = 서비스수정요청(활성여부=True)
        assert 수정요청2.활성여부 is True


class Test서비스타입열거형:
    """서비스 타입 열거형 테스트"""

    def test_모든_서비스타입_값(self):
        """모든 서비스 타입 값 확인 테스트"""
        assert 서비스타입열거형.웹.value == "web"
        assert 서비스타입열거형.API.value == "api"
        assert 서비스타입열거형.데이터베이스.value == "database"
        assert 서비스타입열거형.인프라.value == "infrastructure"

    def test_서비스타입_문자열_변환(self):
        """서비스 타입의 문자열 변환 테스트"""
        assert str(서비스타입열거형.웹) == "web"
        assert str(서비스타입열거형.API) == "api"