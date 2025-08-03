"""
서비스 데이터 모델 정의
SQLAlchemy ORM 모델 및 Pydantic 스키마
"""

from sqlalchemy import Column, String, Text, DECIMAL, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import uuid

from config.데이터베이스설정 import 베이스모델


class 서비스타입열거형(str, Enum):
    """서비스 타입 열거형"""
    웹 = "web"
    API = "api"
    데이터베이스 = "database"
    인프라 = "infrastructure"
    
    def __str__(self):
        return self.value


class 서비스ORM모델(베이스모델):
    """서비스 테이블 ORM 모델"""
    __tablename__ = "서비스"

    아이디 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    이름 = Column(String(100), nullable=False)
    설명 = Column(Text)
    목표SLA = Column(DECIMAL(5, 2), nullable=False)
    서비스타입 = Column(String(20), default="web", nullable=False)
    모니터링설정 = Column(JSON, default={})
    활성여부 = Column(Boolean, default=True)
    생성일시 = Column(DateTime(timezone=True), server_default=func.now())
    수정일시 = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    소유자아이디 = Column(UUID(as_uuid=True))
    
    # 관계 설정
    SLA메트릭목록 = relationship("SLA메트릭ORM모델", back_populates="서비스")

    def __repr__(self):
        return f"<서비스(아이디={self.아이디}, 이름='{self.이름}')>"


class 서비스생성요청(BaseModel):
    """서비스 생성 요청 스키마"""
    이름: str = Field(..., max_length=100, description="서비스 이름")
    설명: Optional[str] = Field(None, description="서비스 설명")
    목표SLA: float = Field(..., description="목표 SLA 백분율 (0-100)")
    서비스타입: 서비스타입열거형 = Field(default=서비스타입열거형.웹, description="서비스 타입")
    모니터링설정: Optional[Dict[str, Any]] = Field(default={}, description="모니터링 설정")
    소유자아이디: Optional[str] = Field(None, description="서비스 소유자 ID")

    @field_validator('목표SLA')
    @classmethod
    def SLA값_검증(cls, v):
        """목표 SLA 값 유효성 검증"""
        if not 0 <= v <= 100:
            raise ValueError('목표 SLA는 0과 100 사이의 값이어야 합니다')
        return round(v, 2)

    @field_validator('이름')
    @classmethod
    def 이름_검증(cls, v):
        """서비스 이름 유효성 검증"""
        if not v or not v.strip():
            raise ValueError('서비스 이름은 필수입니다')
        return v.strip()


class 서비스수정요청(BaseModel):
    """서비스 수정 요청 스키마"""
    이름: Optional[str] = Field(None, max_length=100, description="서비스 이름")
    설명: Optional[str] = Field(None, description="서비스 설명")
    목표SLA: Optional[float] = Field(None, description="목표 SLA 백분율")
    서비스타입: Optional[서비스타입열거형] = Field(None, description="서비스 타입")
    모니터링설정: Optional[Dict[str, Any]] = Field(None, description="모니터링 설정")
    활성여부: Optional[bool] = Field(None, description="서비스 활성 상태")

    @field_validator('목표SLA')
    @classmethod
    def SLA값_검증(cls, v):
        """목표 SLA 값 유효성 검증"""
        if v is not None and not 0 <= v <= 100:
            raise ValueError('목표 SLA는 0과 100 사이의 값이어야 합니다')
        return round(v, 2) if v is not None else v

    @field_validator('이름')
    @classmethod
    def 이름_검증(cls, v):
        """서비스 이름 유효성 검증"""
        if v is not None and (not v or not v.strip()):
            raise ValueError('서비스 이름은 비어있을 수 없습니다')
        return v.strip() if v else v


class 서비스응답(BaseModel):
    """서비스 응답 스키마"""
    아이디: str
    이름: str
    설명: Optional[str]
    목표SLA: float
    서비스타입: str
    모니터링설정: Dict[str, Any]
    활성여부: bool
    생성일시: datetime
    수정일시: datetime
    소유자아이디: Optional[str]

    class Config:
        from_attributes = True


class 서비스목록응답(BaseModel):
    """서비스 목록 응답 스키마"""
    서비스목록: List[서비스응답]
    총개수: int
    페이지: int
    페이지크기: int




class 서비스검색필터(BaseModel):
    """서비스 검색 필터"""
    이름: Optional[str] = Field(None, description="서비스 이름으로 검색")
    서비스타입: Optional[서비스타입열거형] = Field(None, description="서비스 타입으로 필터링")
    활성여부: Optional[bool] = Field(None, description="활성 상태로 필터링")
    소유자아이디: Optional[str] = Field(None, description="소유자 ID로 필터링")
    페이지: int = Field(default=1, ge=1, description="페이지 번호")
    페이지크기: int = Field(default=20, ge=1, le=100, description="페이지당 항목 수")