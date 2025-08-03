"""
환경 설정 관리 모듈
외부 API 연동 및 데이터베이스 설정을 관리합니다.
"""

import os
from typing import Optional
from pydantic import BaseSettings


class 환경설정(BaseSettings):
    """
    애플리케이션 환경 설정 클래스
    환경 변수를 통해 설정값을 관리합니다.
    """
    
    # 기본 애플리케이션 설정
    앱이름: str = "데이터수집서비스"
    디버그모드: bool = False
    포트번호: int = 8003
    
    # 데이터베이스 설정
    데이터베이스_URL: str = "postgresql://user:password@localhost:5432/sla_db"
    
    # Redis 설정 (Celery 브로커용)
    레디스_URL: str = "redis://localhost:6379/0"
    
    # Prometheus 설정
    프로메테우스_URL: str = "http://localhost:9090"
    프로메테우스_사용자명: Optional[str] = None
    프로메테우스_비밀번호: Optional[str] = None
    
    # Grafana 설정
    그라파나_URL: str = "http://localhost:3000"
    그라파나_API_키: Optional[str] = None
    그라파나_사용자명: Optional[str] = None
    그라파나_비밀번호: Optional[str] = None
    
    # Pingdom 설정
    핑덤_API_키: Optional[str] = None
    핑덤_사용자명: Optional[str] = None
    핑덤_비밀번호: Optional[str] = None
    
    # 데이터 수집 설정
    수집주기_초: int = 60  # 기본 1분 간격
    재시도_횟수: int = 3
    재시도_지연시간_초: int = 5
    
    # 로깅 설정
    로그레벨: str = "INFO"
    로그파일경로: str = "logs/data-collector.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 전역 설정 인스턴스
설정 = 환경설정()