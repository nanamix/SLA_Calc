"""
Fixture 테스트
"""

import pytest


@pytest.fixture
def 샘플_서비스_데이터():
    """테스트용 샘플 서비스 데이터"""
    return {
        "이름": "테스트 웹 서비스",
        "설명": "테스트용 웹 서비스입니다",
        "목표SLA": 99.9,
        "서비스타입": "web"
    }


def test_샘플_서비스_데이터_fixture(샘플_서비스_데이터):
    """샘플 서비스 데이터 fixture 테스트"""
    assert 샘플_서비스_데이터["이름"] == "테스트 웹 서비스"
    assert 샘플_서비스_데이터["목표SLA"] == 99.9


def test_simple_fixture(simple_fixture):
    """Simple fixture 테스트"""
    assert simple_fixture == "test"