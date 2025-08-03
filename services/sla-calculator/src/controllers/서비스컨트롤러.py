"""
서비스 관리 API 컨트롤러
서비스 CRUD 작업을 위한 REST API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from config.데이터베이스설정 import 데이터베이스세션_가져오기
from services.서비스관리서비스 import 서비스관리서비스
from models.서비스모델 import (
    서비스생성요청,
    서비스수정요청,
    서비스응답,
    서비스목록응답,
    서비스검색필터,
    서비스타입열거형
)

# 라우터 생성
서비스_라우터 = APIRouter()


@서비스_라우터.post("/", response_model=서비스응답, status_code=status.HTTP_201_CREATED)
async def 서비스_생성(
    서비스데이터: 서비스생성요청,
    세션: AsyncSession = Depends(데이터베이스세션_가져오기)
):
    """
    새로운 서비스를 생성합니다
    
    - **이름**: 서비스 이름 (필수, 1-100자)
    - **설명**: 서비스 설명 (선택사항)
    - **목표SLA**: 목표 SLA 백분율 (필수, 0-100)
    - **서비스타입**: 서비스 타입 (web, api, database, infrastructure)
    - **모니터링설정**: 모니터링 관련 설정 (JSON 객체)
    - **소유자아이디**: 서비스 소유자 ID (선택사항)
    """
    try:
        서비스관리 = 서비스관리서비스(세션)
        새서비스 = await 서비스관리.서비스생성(서비스데이터)
        return 새서비스
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"서비스 생성 실패: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"서버 내부 오류: {str(e)}"
        )


@서비스_라우터.get("/{서비스아이디}", response_model=서비스응답)
async def 서비스_조회(
    서비스아이디: str,
    세션: AsyncSession = Depends(데이터베이스세션_가져오기)
):
    """
    서비스 ID로 특정 서비스 정보를 조회합니다
    
    - **서비스아이디**: 조회할 서비스의 UUID
    """
    try:
        서비스관리 = 서비스관리서비스(세션)
        서비스정보 = await 서비스관리.서비스조회(서비스아이디)
        
        if not 서비스정보:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"서비스를 찾을 수 없습니다: {서비스아이디}"
            )
        
        return 서비스정보
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"서버 내부 오류: {str(e)}"
        )


@서비스_라우터.get("/", response_model=서비스목록응답)
async def 서비스_목록_조회(
    이름: Optional[str] = Query(None, description="서비스 이름으로 검색"),
    서비스타입: Optional[서비스타입열거형] = Query(None, description="서비스 타입으로 필터링"),
    활성여부: Optional[bool] = Query(None, description="활성 상태로 필터링"),
    소유자아이디: Optional[str] = Query(None, description="소유자 ID로 필터링"),
    페이지: int = Query(1, ge=1, description="페이지 번호"),
    페이지크기: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    세션: AsyncSession = Depends(데이터베이스세션_가져오기)
):
    """
    서비스 목록을 조회합니다 (페이징 및 필터링 지원)
    
    - **이름**: 서비스 이름으로 부분 검색
    - **서비스타입**: 서비스 타입으로 필터링 (web, api, database, infrastructure)
    - **활성여부**: 활성 상태로 필터링 (true/false)
    - **소유자아이디**: 소유자 ID로 필터링
    - **페이지**: 페이지 번호 (기본값: 1)
    - **페이지크기**: 페이지당 항목 수 (기본값: 20, 최대: 100)
    """
    try:
        검색필터 = 서비스검색필터(
            이름=이름,
            서비스타입=서비스타입,
            활성여부=활성여부,
            소유자아이디=소유자아이디,
            페이지=페이지,
            페이지크기=페이지크기
        )
        
        서비스관리 = 서비스관리서비스(세션)
        서비스목록 = await 서비스관리.서비스목록조회(검색필터)
        
        return 서비스목록
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"서버 내부 오류: {str(e)}"
        )


@서비스_라우터.put("/{서비스아이디}", response_model=서비스응답)
async def 서비스_수정(
    서비스아이디: str,
    수정데이터: 서비스수정요청,
    세션: AsyncSession = Depends(데이터베이스세션_가져오기)
):
    """
    기존 서비스 정보를 수정합니다
    
    - **서비스아이디**: 수정할 서비스의 UUID
    - **수정데이터**: 수정할 필드들 (모든 필드는 선택사항)
    """
    try:
        서비스관리 = 서비스관리서비스(세션)
        수정된서비스 = await 서비스관리.서비스수정(서비스아이디, 수정데이터)
        
        if not 수정된서비스:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"서비스를 찾을 수 없습니다: {서비스아이디}"
            )
        
        return 수정된서비스
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"서비스 수정 실패: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"서버 내부 오류: {str(e)}"
        )


@서비스_라우터.delete("/{서비스아이디}", status_code=status.HTTP_204_NO_CONTENT)
async def 서비스_삭제(
    서비스아이디: str,
    세션: AsyncSession = Depends(데이터베이스세션_가져오기)
):
    """
    서비스를 삭제합니다 (소프트 삭제 - 활성여부를 False로 변경)
    
    - **서비스아이디**: 삭제할 서비스의 UUID
    """
    try:
        서비스관리 = 서비스관리서비스(세션)
        삭제성공 = await 서비스관리.서비스삭제(서비스아이디)
        
        if not 삭제성공:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"서비스를 찾을 수 없습니다: {서비스아이디}"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"서버 내부 오류: {str(e)}"
        )


@서비스_라우터.get("/{서비스아이디}/health")
async def 서비스_상태_확인(
    서비스아이디: str,
    세션: AsyncSession = Depends(데이터베이스세션_가져오기)
):
    """
    서비스의 현재 상태를 확인합니다
    
    - **서비스아이디**: 상태를 확인할 서비스의 UUID
    """
    try:
        서비스관리 = 서비스관리서비스(세션)
        서비스정보 = await 서비스관리.서비스조회(서비스아이디)
        
        if not 서비스정보:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"서비스를 찾을 수 없습니다: {서비스아이디}"
            )
        
        return {
            "서비스아이디": 서비스정보.아이디,
            "서비스이름": 서비스정보.이름,
            "활성여부": 서비스정보.활성여부,
            "목표SLA": 서비스정보.목표SLA,
            "마지막수정일시": 서비스정보.수정일시,
            "상태": "정상" if 서비스정보.활성여부 else "비활성"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"서버 내부 오류: {str(e)}"
        )