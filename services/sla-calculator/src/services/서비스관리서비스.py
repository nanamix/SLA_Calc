"""
서비스 관리 비즈니스 로직
서비스 CRUD 작업 및 비즈니스 규칙 처리
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Tuple
from uuid import UUID
import uuid

from models.서비스모델 import (
    서비스ORM모델, 
    서비스생성요청, 
    서비스수정요청, 
    서비스응답,
    서비스목록응답,
    서비스검색필터
)


class 서비스관리서비스:
    """서비스 관리 비즈니스 로직 클래스"""

    def __init__(self, 데이터베이스세션: AsyncSession):
        self.세션 = 데이터베이스세션

    async def 서비스생성(self, 서비스데이터: 서비스생성요청) -> 서비스응답:
        """
        새로운 서비스를 생성합니다
        
        Args:
            서비스데이터: 서비스 생성 요청 데이터
            
        Returns:
            생성된 서비스 정보
            
        Raises:
            ValueError: 중복된 서비스 이름이 존재할 경우
        """
        # 중복 서비스 이름 확인
        await self._서비스이름_중복확인(서비스데이터.이름)
        
        # 새 서비스 ORM 객체 생성
        새서비스 = 서비스ORM모델(
            이름=서비스데이터.이름,
            설명=서비스데이터.설명,
            목표SLA=서비스데이터.목표SLA,
            서비스타입=서비스데이터.서비스타입.value,
            모니터링설정=서비스데이터.모니터링설정,
            소유자아이디=UUID(서비스데이터.소유자아이디) if 서비스데이터.소유자아이디 else None
        )
        
        try:
            self.세션.add(새서비스)
            await self.세션.commit()
            await self.세션.refresh(새서비스)
            
            return self._ORM을_응답으로_변환(새서비스)
            
        except IntegrityError as e:
            await self.세션.rollback()
            raise ValueError(f"서비스 생성 중 데이터 무결성 오류가 발생했습니다: {str(e)}")

    async def 서비스조회(self, 서비스아이디: str) -> Optional[서비스응답]:
        """
        서비스 ID로 특정 서비스를 조회합니다
        
        Args:
            서비스아이디: 조회할 서비스의 UUID
            
        Returns:
            서비스 정보 또는 None (존재하지 않을 경우)
        """
        try:
            서비스UUID = UUID(서비스아이디)
        except ValueError:
            return None
            
        쿼리 = select(서비스ORM모델).where(서비스ORM모델.아이디 == 서비스UUID)
        결과 = await self.세션.execute(쿼리)
        서비스 = 결과.scalar_one_or_none()
        
        return self._ORM을_응답으로_변환(서비스) if 서비스 else None

    async def 서비스목록조회(self, 검색필터: 서비스검색필터) -> 서비스목록응답:
        """
        필터 조건에 따라 서비스 목록을 조회합니다
        
        Args:
            검색필터: 검색 및 필터링 조건
            
        Returns:
            페이징된 서비스 목록
        """
        # 기본 쿼리 생성
        쿼리 = select(서비스ORM모델)
        개수쿼리 = select(func.count(서비스ORM모델.아이디))
        
        # 필터 조건 적용
        조건목록 = []
        
        if 검색필터.이름:
            조건목록.append(서비스ORM모델.이름.ilike(f"%{검색필터.이름}%"))
            
        if 검색필터.서비스타입:
            조건목록.append(서비스ORM모델.서비스타입 == 검색필터.서비스타입.value)
            
        if 검색필터.활성여부 is not None:
            조건목록.append(서비스ORM모델.활성여부 == 검색필터.활성여부)
            
        if 검색필터.소유자아이디:
            try:
                소유자UUID = UUID(검색필터.소유자아이디)
                조건목록.append(서비스ORM모델.소유자아이디 == 소유자UUID)
            except ValueError:
                # 잘못된 UUID 형식인 경우 빈 결과 반환
                return 서비스목록응답(서비스목록=[], 총개수=0, 페이지=검색필터.페이지, 페이지크기=검색필터.페이지크기)
        
        if 조건목록:
            쿼리 = 쿼리.where(and_(*조건목록))
            개수쿼리 = 개수쿼리.where(and_(*조건목록))
        
        # 총 개수 조회
        총개수결과 = await self.세션.execute(개수쿼리)
        총개수 = 총개수결과.scalar()
        
        # 페이징 적용
        오프셋 = (검색필터.페이지 - 1) * 검색필터.페이지크기
        쿼리 = 쿼리.offset(오프셋).limit(검색필터.페이지크기)
        쿼리 = 쿼리.order_by(서비스ORM모델.생성일시.desc())
        
        # 서비스 목록 조회
        결과 = await self.세션.execute(쿼리)
        서비스목록 = 결과.scalars().all()
        
        # 응답 변환
        서비스응답목록 = [self._ORM을_응답으로_변환(서비스) for 서비스 in 서비스목록]
        
        return 서비스목록응답(
            서비스목록=서비스응답목록,
            총개수=총개수,
            페이지=검색필터.페이지,
            페이지크기=검색필터.페이지크기
        )

    async def 서비스수정(self, 서비스아이디: str, 수정데이터: 서비스수정요청) -> Optional[서비스응답]:
        """
        기존 서비스 정보를 수정합니다
        
        Args:
            서비스아이디: 수정할 서비스의 UUID
            수정데이터: 수정할 데이터
            
        Returns:
            수정된 서비스 정보 또는 None (존재하지 않을 경우)
        """
        try:
            서비스UUID = UUID(서비스아이디)
        except ValueError:
            return None
            
        # 기존 서비스 조회
        쿼리 = select(서비스ORM모델).where(서비스ORM모델.아이디 == 서비스UUID)
        결과 = await self.세션.execute(쿼리)
        기존서비스 = 결과.scalar_one_or_none()
        
        if not 기존서비스:
            return None
        
        # 서비스 이름 중복 확인 (이름이 변경되는 경우)
        if 수정데이터.이름 and 수정데이터.이름 != 기존서비스.이름:
            await self._서비스이름_중복확인(수정데이터.이름, 제외할_서비스아이디=서비스UUID)
        
        # 수정 데이터 적용
        수정필드목록 = {}
        if 수정데이터.이름 is not None:
            수정필드목록['이름'] = 수정데이터.이름
        if 수정데이터.설명 is not None:
            수정필드목록['설명'] = 수정데이터.설명
        if 수정데이터.목표SLA is not None:
            수정필드목록['목표SLA'] = 수정데이터.목표SLA
        if 수정데이터.서비스타입 is not None:
            수정필드목록['서비스타입'] = 수정데이터.서비스타입.value
        if 수정데이터.모니터링설정 is not None:
            수정필드목록['모니터링설정'] = 수정데이터.모니터링설정
        if 수정데이터.활성여부 is not None:
            수정필드목록['활성여부'] = 수정데이터.활성여부
        
        # 변경사항이 있는 경우에만 업데이트
        if 수정필드목록:
            for 필드명, 값 in 수정필드목록.items():
                setattr(기존서비스, 필드명, 값)
            
            try:
                await self.세션.commit()
                await self.세션.refresh(기존서비스)
            except IntegrityError as e:
                await self.세션.rollback()
                raise ValueError(f"서비스 수정 중 데이터 무결성 오류가 발생했습니다: {str(e)}")
        
        return self._ORM을_응답으로_변환(기존서비스)

    async def 서비스삭제(self, 서비스아이디: str) -> bool:
        """
        서비스를 삭제합니다 (소프트 삭제 - 활성여부를 False로 변경)
        
        Args:
            서비스아이디: 삭제할 서비스의 UUID
            
        Returns:
            삭제 성공 여부
        """
        try:
            서비스UUID = UUID(서비스아이디)
        except ValueError:
            return False
            
        쿼리 = select(서비스ORM모델).where(서비스ORM모델.아이디 == 서비스UUID)
        결과 = await self.세션.execute(쿼리)
        서비스 = 결과.scalar_one_or_none()
        
        if not 서비스:
            return False
        
        # 소프트 삭제 (활성여부를 False로 변경)
        서비스.활성여부 = False
        
        try:
            await self.세션.commit()
            return True
        except Exception:
            await self.세션.rollback()
            return False

    async def _서비스이름_중복확인(self, 서비스이름: str, 제외할_서비스아이디: Optional[UUID] = None):
        """
        서비스 이름 중복을 확인합니다
        
        Args:
            서비스이름: 확인할 서비스 이름
            제외할_서비스아이디: 중복 확인에서 제외할 서비스 ID (수정 시 사용)
            
        Raises:
            ValueError: 중복된 서비스 이름이 존재할 경우
        """
        쿼리 = select(서비스ORM모델).where(
            and_(
                서비스ORM모델.이름 == 서비스이름,
                서비스ORM모델.활성여부 == True
            )
        )
        
        if 제외할_서비스아이디:
            쿼리 = 쿼리.where(서비스ORM모델.아이디 != 제외할_서비스아이디)
        
        결과 = await self.세션.execute(쿼리)
        기존서비스 = 결과.scalar_one_or_none()
        
        if 기존서비스:
            raise ValueError(f"'{서비스이름}' 이름의 서비스가 이미 존재합니다")

    def _ORM을_응답으로_변환(self, 서비스ORM: 서비스ORM모델) -> 서비스응답:
        """
        ORM 모델을 응답 스키마로 변환합니다
        
        Args:
            서비스ORM: 서비스 ORM 객체
            
        Returns:
            서비스 응답 스키마
        """
        return 서비스응답(
            아이디=str(서비스ORM.아이디),
            이름=서비스ORM.이름,
            설명=서비스ORM.설명,
            목표SLA=float(서비스ORM.목표SLA),
            서비스타입=서비스ORM.서비스타입,
            모니터링설정=서비스ORM.모니터링설정,
            활성여부=서비스ORM.활성여부,
            생성일시=서비스ORM.생성일시,
            수정일시=서비스ORM.수정일시,
            소유자아이디=str(서비스ORM.소유자아이디) if 서비스ORM.소유자아이디 else None
        )