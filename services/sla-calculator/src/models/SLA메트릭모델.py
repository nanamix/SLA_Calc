"""
SLA 메트릭 데이터 모델 정의
SLA 계산 결과 및 메트릭 데이터 저장을 위한 모델
"""

from sqlalchemy import Column, String, DECIMAL, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid

from config.데이터베이스설정 import 베이스모델


class 메트릭타입열거형(str, Enum):
    """메트릭 타입 열거형"""
    가용성 = "availability"
    응답시간 = "response_time"
    처리량 = "throughput"
    
    def __str__(self):
        return self.value


class SLA메트릭ORM모델(베이스모델):
    """SLA 메트릭 테이블 ORM 모델"""
    __tablename__ = "SLA메트릭"

    아이디 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    서비스아이디 = Column(UUID(as_uuid=True), ForeignKey('서비스.아이디'), nullable=False)
    메트릭타입 = Column(String(20), nullable=False)
    원시값 = Column(DECIMAL(15, 6), nullable=False, comment="원시 메트릭 값")
    계산된SLA = Column(DECIMAL(5, 2), nullable=False, comment="계산된 SLA 백분율")
    목표SLA = Column(DECIMAL(5, 2), nullable=False, comment="목표 SLA 백분율")
    위반여부 = Column(Boolean, default=False, comment="SLA 위반 여부")
    측정시작시간 = Column(DateTime(timezone=True), nullable=False)
    측정종료시간 = Column(DateTime(timezone=True), nullable=False)
    타임스탬프 = Column(DateTime(timezone=True), server_default=func.now())
    
    # 관계 설정
    서비스 = relationship("서비스ORM모델", back_populates="SLA메트릭목록")
    
    # 인덱스 설정 (성능 최적화)
    __table_args__ = (
        Index('idx_sla메트릭_서비스아이디_타임스탬프', '서비스아이디', '타임스탬프'),
        Index('idx_sla메트릭_메트릭타입_타임스탬프', '메트릭타입', '타임스탬프'),
        Index('idx_sla메트릭_위반여부_타임스탬프', '위반여부', '타임스탬프'),
    )

    def __repr__(self):
        return f"<SLA메트릭(아이디={self.아이디}, 서비스아이디={self.서비스아이디}, 타입={self.메트릭타입})>"


class 원시메트릭데이터(BaseModel):
    """원시 메트릭 데이터 입력 스키마"""
    서비스아이디: str = Field(..., description="서비스 ID")
    메트릭타입: 메트릭타입열거형 = Field(..., description="메트릭 타입")
    측정시작시간: datetime = Field(..., description="측정 시작 시간")
    측정종료시간: datetime = Field(..., description="측정 종료 시간")
    
    # 가용성 메트릭용 필드
    총시간: Optional[float] = Field(None, description="총 측정 시간 (분)")
    다운타임: Optional[float] = Field(None, description="서비스 중단 시간 (분)")
    
    # 응답시간 메트릭용 필드
    총요청수: Optional[int] = Field(None, description="총 요청 수")
    목표응답시간내_요청수: Optional[int] = Field(None, description="목표 응답시간 내 처리된 요청 수")
    평균응답시간: Optional[float] = Field(None, description="평균 응답시간 (ms)")
    
    # 처리량 메트릭용 필드
    처리된요청수: Optional[int] = Field(None, description="처리된 요청 수")
    목표처리량: Optional[float] = Field(None, description="목표 처리량 (req/sec)")
    실제처리량: Optional[float] = Field(None, description="실제 처리량 (req/sec)")

    @field_validator('측정종료시간')
    @classmethod
    def 시간순서_검증(cls, v, info):
        """측정 종료시간이 시작시간보다 늦은지 검증"""
        if '측정시작시간' in info.data and v <= info.data['측정시작시간']:
            raise ValueError('측정 종료시간은 시작시간보다 늦어야 합니다')
        return v


class SLA메트릭응답(BaseModel):
    """SLA 메트릭 응답 스키마"""
    아이디: str
    서비스아이디: str
    메트릭타입: str
    원시값: float
    계산된SLA: float
    목표SLA: float
    위반여부: bool
    측정시작시간: datetime
    측정종료시간: datetime
    타임스탬프: datetime

    class Config:
        from_attributes = True


class SLA메트릭목록응답(BaseModel):
    """SLA 메트릭 목록 응답 스키마"""
    메트릭목록: List[SLA메트릭응답]
    총개수: int
    페이지: int
    페이지크기: int


class SLA메트릭검색필터(BaseModel):
    """SLA 메트릭 검색 필터"""
    서비스아이디: Optional[str] = Field(None, description="서비스 ID로 필터링")
    메트릭타입: Optional[메트릭타입열거형] = Field(None, description="메트릭 타입으로 필터링")
    위반여부: Optional[bool] = Field(None, description="SLA 위반 여부로 필터링")
    시작일시: Optional[datetime] = Field(None, description="검색 시작 일시")
    종료일시: Optional[datetime] = Field(None, description="검색 종료 일시")
    페이지: int = Field(default=1, ge=1, description="페이지 번호")
    페이지크기: int = Field(default=20, ge=1, le=100, description="페이지당 항목 수")


class SLA위반알림데이터(BaseModel):
    """SLA 위반 알림 데이터"""
    서비스아이디: str
    서비스이름: str
    메트릭타입: str
    계산된SLA: float
    목표SLA: float
    위반시간: datetime
    위반정도: float  # 목표 대비 부족한 정도