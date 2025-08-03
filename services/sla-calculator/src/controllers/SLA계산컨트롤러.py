"""
SLA 계산 API 컨트롤러
SLA 메트릭 계산 및 조회 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from config.데이터베이스설정 import 데이터베이스세션_가져오기
from services.SLA계산서비스 import SLA계산서비스
from models.SLA메트릭모델 import (
    원시메트릭데이터,
    SLA메트릭응답,
    SLA메트릭목록응답,
    SLA메트릭검색필터,
    메트릭타입열거형,
    SLA위반알림데이터
)
from utils.캐시유틸 import 캐시관리자_가져오기

logger = logging.getLogger(__name__)

# API 라우터 생성
SLA계산_라우터 = APIRouter(
    prefix="/api/v1/sla",
    tags=["SLA 계산"],
    responses={404: {"description": "리소스를 찾을 수 없습니다"}}
)


async def SLA계산서비스_의존성(
    세션: AsyncSession = Depends(데이터베이스세션_가져오기)
) -> SLA계산서비스:
    """SLA 계산 서비스 의존성 주입"""
    캐시관리자 = 캐시관리자_가져오기()
    if not 캐시관리자:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="캐시 서비스를 사용할 수 없습니다"
        )
    
    return SLA계산서비스(세션, 캐시관리자)


@SLA계산_라우터.post(
    "/metrics/calculate",
    response_model=SLA메트릭응답,
    status_code=status.HTTP_201_CREATED,
    summary="SLA 메트릭 계산",
    description="원시 메트릭 데이터를 받아 SLA를 계산하고 저장합니다"
)
async def SLA메트릭_계산(
    원시데이터: 원시메트릭데이터,
    배경작업: BackgroundTasks,
    SLA서비스: SLA계산서비스 = Depends(SLA계산서비스_의존성)
) -> SLA메트릭응답:
    """
    원시 메트릭 데이터를 받아 SLA를 계산하고 저장합니다
    
    - **서비스아이디**: 계산할 서비스의 ID
    - **메트릭타입**: 계산할 메트릭 타입 (가용성, 응답시간, 처리량)
    - **측정시간**: 메트릭 측정 시간 범위
    - **메트릭별 필수 필드**:
        - 가용성: 총시간, 다운타임
        - 응답시간: 총요청수, 목표응답시간내_요청수
        - 처리량: 실제처리량, 목표처리량
    """
    try:
        logger.info(f"SLA 메트릭 계산 요청: 서비스={원시데이터.서비스아이디}, 타입={원시데이터.메트릭타입}")
        
        # SLA 계산 및 저장
        계산결과 = await SLA서비스.메트릭계산_및_저장(원시데이터)
        
        # 백그라운드에서 SLA 위반 감지 및 알림 처리
        배경작업.add_task(
            _SLA위반_감지_및_알림,
            원시데이터.서비스아이디,
            SLA서비스
        )
        
        logger.info(f"SLA 메트릭 계산 완료: ID={계산결과.아이디}, SLA={계산결과.계산된SLA}%")
        
        return 계산결과
        
    except ValueError as e:
        logger.warning(f"SLA 메트릭 계산 실패 (잘못된 데이터): {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"잘못된 메트릭 데이터입니다: {str(e)}"
        )
    except Exception as e:
        logger.error(f"SLA 메트릭 계산 중 오류 발생: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SLA 메트릭 계산 중 오류가 발생했습니다"
        )


@SLA계산_라우터.get(
    "/metrics/service/{서비스아이디}",
    response_model=List[SLA메트릭응답],
    summary="서비스 최신 SLA 조회",
    description="특정 서비스의 최신 SLA 메트릭을 조회합니다"
)
async def 서비스_최신SLA_조회(
    서비스아이디: str,
    메트릭타입: Optional[메트릭타입열거형] = Query(None, description="특정 메트릭 타입만 조회"),
    SLA서비스: SLA계산서비스 = Depends(SLA계산서비스_의존성)
) -> List[SLA메트릭응답]:
    """
    특정 서비스의 최신 SLA 메트릭을 조회합니다
    
    - **서비스아이디**: 조회할 서비스의 ID
    - **메트릭타입**: 특정 메트릭 타입만 조회 (선택사항)
    """
    try:
        logger.info(f"서비스 최신 SLA 조회: 서비스={서비스아이디}, 타입={메트릭타입}")
        
        메트릭목록 = await SLA서비스.서비스_최신SLA조회(서비스아이디, 메트릭타입)
        
        if not 메트릭목록:
            logger.info(f"SLA 메트릭 없음: 서비스={서비스아이디}")
            return []
        
        logger.info(f"서비스 최신 SLA 조회 완료: 서비스={서비스아이디}, 메트릭수={len(메트릭목록)}")
        
        return 메트릭목록
        
    except Exception as e:
        logger.error(f"서비스 최신 SLA 조회 중 오류 발생: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SLA 메트릭 조회 중 오류가 발생했습니다"
        )


@SLA계산_라우터.get(
    "/violations/service/{서비스아이디}",
    response_model=List[SLA위반알림데이터],
    summary="SLA 위반 감지",
    description="특정 서비스의 SLA 위반을 감지합니다"
)
async def SLA위반_감지(
    서비스아이디: str,
    시간범위_분: int = Query(60, ge=1, le=1440, description="검사할 시간 범위 (분, 1-1440)"),
    SLA서비스: SLA계산서비스 = Depends(SLA계산서비스_의존성)
) -> List[SLA위반알림데이터]:
    """
    특정 서비스의 SLA 위반을 감지합니다
    
    - **서비스아이디**: 검사할 서비스의 ID
    - **시간범위_분**: 검사할 시간 범위 (분 단위, 기본값: 60분)
    """
    try:
        logger.info(f"SLA 위반 감지 요청: 서비스={서비스아이디}, 시간범위={시간범위_분}분")
        
        위반목록 = await SLA서비스.SLA위반_감지(서비스아이디, 시간범위_분)
        
        logger.info(f"SLA 위반 감지 완료: 서비스={서비스아이디}, 위반건수={len(위반목록)}")
        
        return 위반목록
        
    except Exception as e:
        logger.error(f"SLA 위반 감지 중 오류 발생: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SLA 위반 감지 중 오류가 발생했습니다"
        )


@SLA계산_라우터.post(
    "/calculate/availability",
    response_model=dict,
    summary="가용성 계산",
    description="가용성 SLA를 계산합니다 (계산만 수행, 저장하지 않음)"
)
async def 가용성_계산(
    총시간: float = Query(..., gt=0, description="총 측정 시간 (분)"),
    다운타임: float = Query(..., ge=0, description="서비스 중단 시간 (분)"),
    SLA서비스: SLA계산서비스 = Depends(SLA계산서비스_의존성)
) -> dict:
    """
    가용성 SLA를 계산합니다 (계산만 수행, 저장하지 않음)
    
    - **총시간**: 전체 측정 시간 (분 단위)
    - **다운타임**: 서비스 중단 시간 (분 단위)
    """
    try:
        if 다운타임 > 총시간:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="다운타임은 총 시간을 초과할 수 없습니다"
            )
        
        원시값, 가용성백분율 = await SLA서비스.가용성계산(총시간, 다운타임)
        
        return {
            "메트릭타입": "가용성",
            "총시간_분": 총시간,
            "다운타임_분": 다운타임,
            "가용시간_분": 총시간 - 다운타임,
            "가용성백분율": 가용성백분율,
            "계산공식": "(총시간 - 다운타임) / 총시간 × 100"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"가용성 계산 중 오류 발생: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="가용성 계산 중 오류가 발생했습니다"
        )


@SLA계산_라우터.post(
    "/calculate/response-time",
    response_model=dict,
    summary="응답시간 계산",
    description="응답시간 SLA를 계산합니다 (계산만 수행, 저장하지 않음)"
)
async def 응답시간_계산(
    총요청수: int = Query(..., gt=0, description="총 요청 수"),
    목표응답시간내_요청수: int = Query(..., ge=0, description="목표 응답시간 내 처리된 요청 수"),
    SLA서비스: SLA계산서비스 = Depends(SLA계산서비스_의존성)
) -> dict:
    """
    응답시간 SLA를 계산합니다 (계산만 수행, 저장하지 않음)
    
    - **총요청수**: 전체 요청 수
    - **목표응답시간내_요청수**: 목표 응답시간 내 처리된 요청 수
    """
    try:
        if 목표응답시간내_요청수 > 총요청수:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="목표 응답시간 내 요청수는 총 요청수를 초과할 수 없습니다"
            )
        
        원시값, 응답시간SLA백분율 = await SLA서비스.응답시간계산(총요청수, 목표응답시간내_요청수)
        
        return {
            "메트릭타입": "응답시간",
            "총요청수": 총요청수,
            "목표응답시간내_요청수": 목표응답시간내_요청수,
            "목표응답시간초과_요청수": 총요청수 - 목표응답시간내_요청수,
            "응답시간SLA백분율": 응답시간SLA백분율,
            "계산공식": "목표 응답시간 내 요청수 / 총 요청수 × 100"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"응답시간 계산 중 오류 발생: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="응답시간 계산 중 오류가 발생했습니다"
        )


@SLA계산_라우터.post(
    "/calculate/throughput",
    response_model=dict,
    summary="처리량 계산",
    description="처리량 SLA를 계산합니다 (계산만 수행, 저장하지 않음)"
)
async def 처리량_계산(
    실제처리량: float = Query(..., ge=0, description="실제 처리량 (req/sec)"),
    목표처리량: float = Query(..., gt=0, description="목표 처리량 (req/sec)"),
    SLA서비스: SLA계산서비스 = Depends(SLA계산서비스_의존성)
) -> dict:
    """
    처리량 SLA를 계산합니다 (계산만 수행, 저장하지 않음)
    
    - **실제처리량**: 실제 처리량 (req/sec)
    - **목표처리량**: 목표 처리량 (req/sec)
    """
    try:
        원시값, 처리량SLA백분율 = await SLA서비스.처리량계산(실제처리량, 목표처리량)
        
        return {
            "메트릭타입": "처리량",
            "실제처리량": 실제처리량,
            "목표처리량": 목표처리량,
            "처리량차이": 실제처리량 - 목표처리량,
            "처리량SLA백분율": 처리량SLA백분율,
            "계산공식": "min(실제처리량 / 목표처리량 × 100, 100)"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"처리량 계산 중 오류 발생: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="처리량 계산 중 오류가 발생했습니다"
        )


async def _SLA위반_감지_및_알림(서비스아이디: str, SLA서비스: SLA계산서비스):
    """
    백그라운드에서 SLA 위반을 감지하고 알림을 처리합니다
    
    Args:
        서비스아이디: 검사할 서비스 ID
        SLA서비스: SLA 계산 서비스 인스턴스
    """
    try:
        # 최근 5분간의 SLA 위반 감지
        위반목록 = await SLA서비스.SLA위반_감지(서비스아이디, 5)
        
        if 위반목록:
            logger.warning(f"SLA 위반 감지됨: 서비스={서비스아이디}, 위반건수={len(위반목록)}")
            
            # TODO: 실제 알림 서비스와 연동
            # - 이메일 발송
            # - Slack 메시지 전송
            # - 메시지 큐에 알림 이벤트 발행
            
        else:
            logger.debug(f"SLA 위반 없음: 서비스={서비스아이디}")
            
    except Exception as e:
        logger.error(f"백그라운드 SLA 위반 감지 중 오류 발생: 서비스={서비스아이디}, 오류={e}")