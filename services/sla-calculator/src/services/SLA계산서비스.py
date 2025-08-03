"""
SLA 계산 엔진 서비스
가용성, 응답시간, 처리량 메트릭 계산 및 SLA 위반 감지
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import asyncio
import logging

from models.SLA메트릭모델 import (
    SLA메트릭ORM모델, 
    원시메트릭데이터, 
    SLA메트릭응답,
    메트릭타입열거형,
    SLA위반알림데이터
)
from models.서비스모델 import 서비스ORM모델
from utils.캐시유틸 import 캐시관리자


logger = logging.getLogger(__name__)


class SLA계산서비스:
    """SLA 메트릭 계산 및 관리 서비스"""

    def __init__(self, 데이터베이스세션: AsyncSession, 캐시관리자: 캐시관리자):
        self.세션 = 데이터베이스세션
        self.캐시 = 캐시관리자
        self.캐시만료시간 = 300  # 5분

    async def 메트릭계산_및_저장(self, 원시데이터: 원시메트릭데이터) -> SLA메트릭응답:
        """
        원시 메트릭 데이터를 받아 SLA를 계산하고 저장합니다
        
        Args:
            원시데이터: 원시 메트릭 데이터
            
        Returns:
            계산된 SLA 메트릭 정보
            
        Raises:
            ValueError: 잘못된 메트릭 데이터 또는 서비스가 존재하지 않을 경우
        """
        # 서비스 존재 여부 확인 및 목표 SLA 조회
        서비스정보 = await self._서비스정보_조회(원시데이터.서비스아이디)
        if not 서비스정보:
            raise ValueError(f"서비스 ID '{원시데이터.서비스아이디}'를 찾을 수 없습니다")

        # 메트릭 타입별 SLA 계산
        계산결과 = await self._메트릭타입별_SLA계산(원시데이터, 서비스정보.목표SLA)
        
        # SLA 메트릭 저장
        SLA메트릭 = SLA메트릭ORM모델(
            서비스아이디=서비스정보.아이디,
            메트릭타입=원시데이터.메트릭타입.value,
            원시값=계산결과['원시값'],
            계산된SLA=계산결과['계산된SLA'],
            목표SLA=서비스정보.목표SLA,
            위반여부=계산결과['위반여부'],
            측정시작시간=원시데이터.측정시작시간,
            측정종료시간=원시데이터.측정종료시간
        )
        
        self.세션.add(SLA메트릭)
        await self.세션.commit()
        await self.세션.refresh(SLA메트릭)
        
        # 캐시 무효화 (최신 데이터 반영)
        await self._서비스_SLA캐시_무효화(원시데이터.서비스아이디)
        
        # SLA 위반 시 알림 데이터 생성
        if 계산결과['위반여부']:
            await self._SLA위반_알림처리(SLA메트릭, 서비스정보.이름)
        
        logger.info(f"SLA 메트릭 계산 완료: 서비스={서비스정보.이름}, 타입={원시데이터.메트릭타입}, SLA={계산결과['계산된SLA']}%")
        
        return self._ORM을_응답으로_변환(SLA메트릭)

    async def 가용성계산(self, 총시간: float, 다운타임: float) -> Tuple[float, float]:
        """
        서비스 가용성을 계산합니다
        
        Args:
            총시간: 전체 측정 시간 (분 단위)
            다운타임: 서비스 중단 시간 (분 단위)
            
        Returns:
            (원시값, 가용성백분율) 튜플
            
        Raises:
            ValueError: 잘못된 입력값
        """
        if 총시간 <= 0:
            raise ValueError("총 시간은 0보다 커야 합니다")
        if 다운타임 < 0:
            raise ValueError("다운타임은 0 이상이어야 합니다")
        if 다운타임 > 총시간:
            raise ValueError("다운타임은 총 시간을 초과할 수 없습니다")
        
        # 가용성 계산: (총시간 - 다운타임) / 총시간 * 100
        가용시간 = 총시간 - 다운타임
        가용성백분율 = (가용시간 / 총시간) * 100
        
        # 소수점 둘째자리까지 반올림
        가용성백분율 = float(Decimal(str(가용성백분율)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        
        logger.debug(f"가용성 계산: 총시간={총시간}분, 다운타임={다운타임}분, 가용성={가용성백분율}%")
        
        return 다운타임, 가용성백분율

    async def 응답시간계산(self, 총요청수: int, 목표응답시간내_요청수: int) -> Tuple[float, float]:
        """
        응답시간 SLA를 계산합니다
        
        Args:
            총요청수: 전체 요청 수
            목표응답시간내_요청수: 목표 응답시간 내 처리된 요청 수
            
        Returns:
            (원시값, 응답시간SLA백분율) 튜플
            
        Raises:
            ValueError: 잘못된 입력값
        """
        if 총요청수 <= 0:
            raise ValueError("총 요청수는 0보다 커야 합니다")
        if 목표응답시간내_요청수 < 0:
            raise ValueError("목표 응답시간 내 요청수는 0 이상이어야 합니다")
        if 목표응답시간내_요청수 > 총요청수:
            raise ValueError("목표 응답시간 내 요청수는 총 요청수를 초과할 수 없습니다")
        
        # 응답시간 SLA 계산: 목표 응답시간 내 요청수 / 총 요청수 * 100
        응답시간SLA백분율 = (목표응답시간내_요청수 / 총요청수) * 100
        
        # 소수점 둘째자리까지 반올림
        응답시간SLA백분율 = float(Decimal(str(응답시간SLA백분율)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        
        logger.debug(f"응답시간 SLA 계산: 총요청={총요청수}, 목표내요청={목표응답시간내_요청수}, SLA={응답시간SLA백분율}%")
        
        return float(목표응답시간내_요청수), 응답시간SLA백분율

    async def 처리량계산(self, 실제처리량: float, 목표처리량: float) -> Tuple[float, float]:
        """
        처리량 SLA를 계산합니다
        
        Args:
            실제처리량: 실제 처리량 (req/sec)
            목표처리량: 목표 처리량 (req/sec)
            
        Returns:
            (원시값, 처리량SLA백분율) 튜플
            
        Raises:
            ValueError: 잘못된 입력값
        """
        if 목표처리량 <= 0:
            raise ValueError("목표 처리량은 0보다 커야 합니다")
        if 실제처리량 < 0:
            raise ValueError("실제 처리량은 0 이상이어야 합니다")
        
        # 처리량 SLA 계산: min(실제처리량 / 목표처리량 * 100, 100)
        # 100%를 초과하지 않도록 제한
        처리량SLA백분율 = min((실제처리량 / 목표처리량) * 100, 100.0)
        
        # 소수점 둘째자리까지 반올림
        처리량SLA백분율 = float(Decimal(str(처리량SLA백분율)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        
        logger.debug(f"처리량 SLA 계산: 실제처리량={실제처리량}, 목표처리량={목표처리량}, SLA={처리량SLA백분율}%")
        
        return 실제처리량, 처리량SLA백분율

    async def 서비스_최신SLA조회(self, 서비스아이디: str, 메트릭타입: Optional[메트릭타입열거형] = None) -> List[SLA메트릭응답]:
        """
        서비스의 최신 SLA 메트릭을 조회합니다 (캐시 활용)
        
        Args:
            서비스아이디: 서비스 ID
            메트릭타입: 특정 메트릭 타입 (None이면 모든 타입)
            
        Returns:
            최신 SLA 메트릭 목록
        """
        캐시키 = f"sla_metrics:{서비스아이디}:{메트릭타입.value if 메트릭타입 else 'all'}"
        
        # 캐시에서 조회 시도
        캐시된결과 = await self.캐시.get(캐시키)
        if 캐시된결과:
            logger.debug(f"캐시에서 SLA 메트릭 조회: {캐시키}")
            return [SLA메트릭응답(**메트릭) for 메트릭 in 캐시된결과]
        
        # 데이터베이스에서 조회
        쿼리 = select(SLA메트릭ORM모델).where(SLA메트릭ORM모델.서비스아이디 == 서비스아이디)
        
        if 메트릭타입:
            쿼리 = 쿼리.where(SLA메트릭ORM모델.메트릭타입 == 메트릭타입.value)
        
        # 각 메트릭 타입별로 최신 데이터만 조회
        if 메트릭타입:
            쿼리 = 쿼리.order_by(desc(SLA메트릭ORM모델.타임스탬프)).limit(1)
        else:
            # 서브쿼리를 사용하여 각 메트릭 타입별 최신 데이터 조회
            서브쿼리 = select(
                SLA메트릭ORM모델.메트릭타입,
                func.max(SLA메트릭ORM모델.타임스탬프).label('최신타임스탬프')
            ).where(
                SLA메트릭ORM모델.서비스아이디 == 서비스아이디
            ).group_by(SLA메트릭ORM모델.메트릭타입).subquery()
            
            쿼리 = select(SLA메트릭ORM모델).join(
                서브쿼리,
                and_(
                    SLA메트릭ORM모델.메트릭타입 == 서브쿼리.c.메트릭타입,
                    SLA메트릭ORM모델.타임스탬프 == 서브쿼리.c.최신타임스탬프
                )
            ).where(SLA메트릭ORM모델.서비스아이디 == 서비스아이디)
        
        결과 = await self.세션.execute(쿼리)
        메트릭목록 = 결과.scalars().all()
        
        # 응답 변환
        응답목록 = [self._ORM을_응답으로_변환(메트릭) for 메트릭 in 메트릭목록]
        
        # 캐시에 저장
        캐시데이터 = [메트릭.dict() for 메트릭 in 응답목록]
        await self.캐시.set(캐시키, 캐시데이터, expire=self.캐시만료시간)
        
        logger.debug(f"데이터베이스에서 SLA 메트릭 조회 및 캐시 저장: {캐시키}")
        
        return 응답목록

    async def SLA위반_감지(self, 서비스아이디: str, 시간범위_분: int = 60) -> List[SLA위반알림데이터]:
        """
        지정된 시간 범위 내의 SLA 위반을 감지합니다
        
        Args:
            서비스아이디: 서비스 ID
            시간범위_분: 검사할 시간 범위 (분 단위)
            
        Returns:
            SLA 위반 알림 데이터 목록
        """
        시작시간 = datetime.utcnow() - timedelta(minutes=시간범위_분)
        
        쿼리 = select(SLA메트릭ORM모델, 서비스ORM모델.이름).join(
            서비스ORM모델, SLA메트릭ORM모델.서비스아이디 == 서비스ORM모델.아이디
        ).where(
            and_(
                SLA메트릭ORM모델.서비스아이디 == 서비스아이디,
                SLA메트릭ORM모델.위반여부 == True,
                SLA메트릭ORM모델.타임스탬프 >= 시작시간
            )
        ).order_by(desc(SLA메트릭ORM모델.타임스탬프))
        
        결과 = await self.세션.execute(쿼리)
        위반목록 = 결과.all()
        
        알림목록 = []
        for 메트릭, 서비스이름 in 위반목록:
            위반정도 = float(메트릭.목표SLA - 메트릭.계산된SLA)
            
            알림데이터 = SLA위반알림데이터(
                서비스아이디=str(메트릭.서비스아이디),
                서비스이름=서비스이름,
                메트릭타입=메트릭.메트릭타입,
                계산된SLA=float(메트릭.계산된SLA),
                목표SLA=float(메트릭.목표SLA),
                위반시간=메트릭.타임스탬프,
                위반정도=위반정도
            )
            알림목록.append(알림데이터)
        
        logger.info(f"SLA 위반 감지 완료: 서비스={서비스아이디}, 위반건수={len(알림목록)}")
        
        return 알림목록

    async def _메트릭타입별_SLA계산(self, 원시데이터: 원시메트릭데이터, 목표SLA: Decimal) -> Dict[str, Any]:
        """메트릭 타입별로 SLA를 계산합니다"""
        
        if 원시데이터.메트릭타입 == 메트릭타입열거형.가용성:
            if 원시데이터.총시간 is None or 원시데이터.다운타임 is None:
                raise ValueError("가용성 계산을 위해서는 총시간과 다운타임이 필요합니다")
            
            원시값, 계산된SLA = await self.가용성계산(원시데이터.총시간, 원시데이터.다운타임)
            
        elif 원시데이터.메트릭타입 == 메트릭타입열거형.응답시간:
            if 원시데이터.총요청수 is None or 원시데이터.목표응답시간내_요청수 is None:
                raise ValueError("응답시간 계산을 위해서는 총요청수와 목표응답시간내_요청수가 필요합니다")
            
            원시값, 계산된SLA = await self.응답시간계산(원시데이터.총요청수, 원시데이터.목표응답시간내_요청수)
            
        elif 원시데이터.메트릭타입 == 메트릭타입열거형.처리량:
            if 원시데이터.실제처리량 is None or 원시데이터.목표처리량 is None:
                raise ValueError("처리량 계산을 위해서는 실제처리량과 목표처리량이 필요합니다")
            
            원시값, 계산된SLA = await self.처리량계산(원시데이터.실제처리량, 원시데이터.목표처리량)
            
        else:
            raise ValueError(f"지원하지 않는 메트릭 타입입니다: {원시데이터.메트릭타입}")
        
        위반여부 = 계산된SLA < float(목표SLA)
        
        return {
            '원시값': Decimal(str(원시값)),
            '계산된SLA': Decimal(str(계산된SLA)),
            '위반여부': 위반여부
        }

    async def _서비스정보_조회(self, 서비스아이디: str) -> Optional[서비스ORM모델]:
        """서비스 정보를 조회합니다"""
        try:
            from uuid import UUID
            서비스UUID = UUID(서비스아이디)
        except ValueError:
            return None
        
        쿼리 = select(서비스ORM모델).where(서비스ORM모델.아이디 == 서비스UUID)
        결과 = await self.세션.execute(쿼리)
        return 결과.scalar_one_or_none()

    async def _서비스_SLA캐시_무효화(self, 서비스아이디: str):
        """서비스의 SLA 관련 캐시를 무효화합니다"""
        캐시키목록 = [
            f"sla_metrics:{서비스아이디}:all",
            f"sla_metrics:{서비스아이디}:availability",
            f"sla_metrics:{서비스아이디}:response_time",
            f"sla_metrics:{서비스아이디}:throughput"
        ]
        
        for 캐시키 in 캐시키목록:
            await self.캐시.delete(캐시키)

    async def _SLA위반_알림처리(self, SLA메트릭: SLA메트릭ORM모델, 서비스이름: str):
        """SLA 위반 시 알림 처리 (비동기)"""
        try:
            위반정도 = float(SLA메트릭.목표SLA - SLA메트릭.계산된SLA)
            
            알림데이터 = SLA위반알림데이터(
                서비스아이디=str(SLA메트릭.서비스아이디),
                서비스이름=서비스이름,
                메트릭타입=SLA메트릭.메트릭타입,
                계산된SLA=float(SLA메트릭.계산된SLA),
                목표SLA=float(SLA메트릭.목표SLA),
                위반시간=SLA메트릭.타임스탬프,
                위반정도=위반정도
            )
            
            # 알림 큐에 메시지 발송 (실제 구현에서는 메시지 큐 사용)
            logger.warning(f"SLA 위반 감지: {알림데이터.dict()}")
            
            # TODO: 실제 알림 서비스와 연동 (메시지 큐 또는 직접 호출)
            
        except Exception as e:
            logger.error(f"SLA 위반 알림 처리 중 오류 발생: {e}")

    def _ORM을_응답으로_변환(self, SLA메트릭ORM: SLA메트릭ORM모델) -> SLA메트릭응답:
        """ORM 모델을 응답 스키마로 변환합니다"""
        return SLA메트릭응답(
            아이디=str(SLA메트릭ORM.아이디),
            서비스아이디=str(SLA메트릭ORM.서비스아이디),
            메트릭타입=SLA메트릭ORM.메트릭타입,
            원시값=float(SLA메트릭ORM.원시값),
            계산된SLA=float(SLA메트릭ORM.계산된SLA),
            목표SLA=float(SLA메트릭ORM.목표SLA),
            위반여부=SLA메트릭ORM.위반여부,
            측정시작시간=SLA메트릭ORM.측정시작시간,
            측정종료시간=SLA메트릭ORM.측정종료시간,
            타임스탬프=SLA메트릭ORM.타임스탬프
        )