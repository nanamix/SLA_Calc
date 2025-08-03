"""
서비스 API 통합 테스트
REST API 엔드포인트 테스트
"""

import pytest
from httpx import AsyncClient


class Test서비스API:
    """서비스 API 엔드포인트 테스트 클래스"""

    @pytest.mark.asyncio
    async def test_서비스_생성_API_성공(self, 테스트_클라이언트: AsyncClient, 샘플_서비스_데이터):
        """서비스 생성 API 성공 테스트"""
        응답 = await 테스트_클라이언트.post("/api/v1/services/", json=샘플_서비스_데이터)
        
        assert 응답.status_code == 201
        응답데이터 = 응답.json()
        
        assert 응답데이터["이름"] == 샘플_서비스_데이터["이름"]
        assert 응답데이터["설명"] == 샘플_서비스_데이터["설명"]
        assert 응답데이터["목표SLA"] == 샘플_서비스_데이터["목표SLA"]
        assert 응답데이터["서비스타입"] == 샘플_서비스_데이터["서비스타입"]
        assert "아이디" in 응답데이터
        assert "생성일시" in 응답데이터

    @pytest.mark.asyncio
    async def test_서비스_생성_API_필수필드_누락(self, 테스트_클라이언트: AsyncClient):
        """서비스 생성 API 필수 필드 누락 테스트"""
        잘못된_데이터 = {"설명": "설명만 있음"}
        
        응답 = await 테스트_클라이언트.post("/api/v1/services/", json=잘못된_데이터)
        
        assert 응답.status_code == 422  # Validation Error

    @pytest.mark.asyncio
    async def test_서비스_생성_API_잘못된_SLA값(self, 테스트_클라이언트: AsyncClient):
        """서비스 생성 API 잘못된 SLA 값 테스트"""
        잘못된_데이터 = {
            "이름": "테스트 서비스",
            "목표SLA": 150.0  # 100 초과
        }
        
        응답 = await 테스트_클라이언트.post("/api/v1/services/", json=잘못된_데이터)
        
        assert 응답.status_code == 422

    @pytest.mark.asyncio
    async def test_서비스_조회_API_성공(self, 테스트_클라이언트: AsyncClient, 샘플_서비스_데이터):
        """서비스 조회 API 성공 테스트"""
        # 먼저 서비스 생성
        생성응답 = await 테스트_클라이언트.post("/api/v1/services/", json=샘플_서비스_데이터)
        생성된서비스 = 생성응답.json()
        서비스아이디 = 생성된서비스["아이디"]
        
        # 서비스 조회
        조회응답 = await 테스트_클라이언트.get(f"/api/v1/services/{서비스아이디}")
        
        assert 조회응답.status_code == 200
        조회데이터 = 조회응답.json()
        
        assert 조회데이터["아이디"] == 서비스아이디
        assert 조회데이터["이름"] == 샘플_서비스_데이터["이름"]

    @pytest.mark.asyncio
    async def test_서비스_조회_API_존재하지않음(self, 테스트_클라이언트: AsyncClient):
        """존재하지 않는 서비스 조회 API 테스트"""
        존재하지않는_아이디 = "550e8400-e29b-41d4-a716-446655440000"
        
        응답 = await 테스트_클라이언트.get(f"/api/v1/services/{존재하지않는_아이디}")
        
        assert 응답.status_code == 404
        assert "찾을 수 없습니다" in 응답.json()["detail"]

    @pytest.mark.asyncio
    async def test_서비스_목록_조회_API_기본(self, 테스트_클라이언트: AsyncClient, 여러_서비스_데이터):
        """서비스 목록 조회 API 기본 테스트"""
        # 여러 서비스 생성
        for 서비스데이터 in 여러_서비스_데이터:
            await 테스트_클라이언트.post("/api/v1/services/", json=서비스데이터)
        
        # 서비스 목록 조회
        응답 = await 테스트_클라이언트.get("/api/v1/services/")
        
        assert 응답.status_code == 200
        응답데이터 = 응답.json()
        
        assert 응답데이터["총개수"] == len(여러_서비스_데이터)
        assert len(응답데이터["서비스목록"]) == len(여러_서비스_데이터)
        assert 응답데이터["페이지"] == 1
        assert 응답데이터["페이지크기"] == 20

    @pytest.mark.asyncio
    async def test_서비스_목록_조회_API_필터링(self, 테스트_클라이언트: AsyncClient, 여러_서비스_데이터):
        """서비스 목록 조회 API 필터링 테스트"""
        # 여러 서비스 생성
        for 서비스데이터 in 여러_서비스_데이터:
            await 테스트_클라이언트.post("/api/v1/services/", json=서비스데이터)
        
        # 이름으로 검색
        응답 = await 테스트_클라이언트.get("/api/v1/services/?이름=웹")
        
        assert 응답.status_code == 200
        응답데이터 = 응답.json()
        
        assert 응답데이터["총개수"] == 1
        assert "웹" in 응답데이터["서비스목록"][0]["이름"]

    @pytest.mark.asyncio
    async def test_서비스_목록_조회_API_페이징(self, 테스트_클라이언트: AsyncClient, 여러_서비스_데이터):
        """서비스 목록 조회 API 페이징 테스트"""
        # 여러 서비스 생성
        for 서비스데이터 in 여러_서비스_데이터:
            await 테스트_클라이언트.post("/api/v1/services/", json=서비스데이터)
        
        # 첫 번째 페이지 (페이지 크기 2)
        응답 = await 테스트_클라이언트.get("/api/v1/services/?페이지=1&페이지크기=2")
        
        assert 응답.status_code == 200
        응답데이터 = 응답.json()
        
        assert 응답데이터["총개수"] == 3
        assert len(응답데이터["서비스목록"]) == 2
        assert 응답데이터["페이지"] == 1

    @pytest.mark.asyncio
    async def test_서비스_수정_API_성공(self, 테스트_클라이언트: AsyncClient, 샘플_서비스_데이터):
        """서비스 수정 API 성공 테스트"""
        # 먼저 서비스 생성
        생성응답 = await 테스트_클라이언트.post("/api/v1/services/", json=샘플_서비스_데이터)
        생성된서비스 = 생성응답.json()
        서비스아이디 = 생성된서비스["아이디"]
        
        # 서비스 수정
        수정데이터 = {
            "이름": "수정된 서비스 이름",
            "목표SLA": 98.5,
            "활성여부": False
        }
        
        수정응답 = await 테스트_클라이언트.put(f"/api/v1/services/{서비스아이디}", json=수정데이터)
        
        assert 수정응답.status_code == 200
        수정된데이터 = 수정응답.json()
        
        assert 수정된데이터["이름"] == "수정된 서비스 이름"
        assert 수정된데이터["목표SLA"] == 98.5
        assert 수정된데이터["활성여부"] is False

    @pytest.mark.asyncio
    async def test_서비스_수정_API_존재하지않음(self, 테스트_클라이언트: AsyncClient):
        """존재하지 않는 서비스 수정 API 테스트"""
        존재하지않는_아이디 = "550e8400-e29b-41d4-a716-446655440000"
        수정데이터 = {"이름": "수정된 이름"}
        
        응답 = await 테스트_클라이언트.put(f"/api/v1/services/{존재하지않는_아이디}", json=수정데이터)
        
        assert 응답.status_code == 404

    @pytest.mark.asyncio
    async def test_서비스_삭제_API_성공(self, 테스트_클라이언트: AsyncClient, 샘플_서비스_데이터):
        """서비스 삭제 API 성공 테스트"""
        # 먼저 서비스 생성
        생성응답 = await 테스트_클라이언트.post("/api/v1/services/", json=샘플_서비스_데이터)
        생성된서비스 = 생성응답.json()
        서비스아이디 = 생성된서비스["아이디"]
        
        # 서비스 삭제
        삭제응답 = await 테스트_클라이언트.delete(f"/api/v1/services/{서비스아이디}")
        
        assert 삭제응답.status_code == 204
        
        # 삭제 후 조회 시 활성여부가 False인지 확인
        조회응답 = await 테스트_클라이언트.get(f"/api/v1/services/{서비스아이디}")
        조회데이터 = 조회응답.json()
        
        assert 조회데이터["활성여부"] is False

    @pytest.mark.asyncio
    async def test_서비스_삭제_API_존재하지않음(self, 테스트_클라이언트: AsyncClient):
        """존재하지 않는 서비스 삭제 API 테스트"""
        존재하지않는_아이디 = "550e8400-e29b-41d4-a716-446655440000"
        
        응답 = await 테스트_클라이언트.delete(f"/api/v1/services/{존재하지않는_아이디}")
        
        assert 응답.status_code == 404

    @pytest.mark.asyncio
    async def test_서비스_상태확인_API_성공(self, 테스트_클라이언트: AsyncClient, 샘플_서비스_데이터):
        """서비스 상태 확인 API 성공 테스트"""
        # 먼저 서비스 생성
        생성응답 = await 테스트_클라이언트.post("/api/v1/services/", json=샘플_서비스_데이터)
        생성된서비스 = 생성응답.json()
        서비스아이디 = 생성된서비스["아이디"]
        
        # 서비스 상태 확인
        상태응답 = await 테스트_클라이언트.get(f"/api/v1/services/{서비스아이디}/health")
        
        assert 상태응답.status_code == 200
        상태데이터 = 상태응답.json()
        
        assert 상태데이터["서비스아이디"] == 서비스아이디
        assert 상태데이터["서비스이름"] == 샘플_서비스_데이터["이름"]
        assert 상태데이터["활성여부"] is True
        assert 상태데이터["상태"] == "정상"

    @pytest.mark.asyncio
    async def test_루트_엔드포인트(self, 테스트_클라이언트: AsyncClient):
        """루트 엔드포인트 테스트"""
        응답 = await 테스트_클라이언트.get("/")
        
        assert 응답.status_code == 200
        응답데이터 = 응답.json()
        
        assert "SLA Calculator API가 정상적으로 실행 중입니다" in 응답데이터["message"]

    @pytest.mark.asyncio
    async def test_헬스체크_엔드포인트(self, 테스트_클라이언트: AsyncClient):
        """헬스체크 엔드포인트 테스트"""
        응답 = await 테스트_클라이언트.get("/health")
        
        assert 응답.status_code == 200
        응답데이터 = 응답.json()
        
        assert 응답데이터["status"] == "healthy"
        assert 응답데이터["service"] == "sla-calculator"