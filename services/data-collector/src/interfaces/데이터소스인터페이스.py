"""
데이터 소스 연동을 위한 기본 인터페이스
모든 외부 모니터링 도구 클라이언트는 이 인터페이스를 구현해야 합니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel


class 메트릭데이터(BaseModel):
    """
    수집된 메트릭 데이터를 표준화하는 모델
    """
    서비스명: str
    메트릭타입: str  # 'availability', 'response_time', 'throughput'
    값: float
    타임스탬프: datetime
    단위: str
    태그: Optional[Dict[str, str]] = None
    원본데이터: Optional[Dict[str, Any]] = None


class 데이터소스연결정보(BaseModel):
    """
    데이터 소스 연결에 필요한 정보
    """
    이름: str
    타입: str  # 'prometheus', 'grafana', 'pingdom', 'custom'
    엔드포인트: str
    인증정보: Optional[Dict[str, str]] = None
    설정옵션: Optional[Dict[str, Any]] = None


class 데이터소스인터페이스(ABC):
    """
    외부 모니터링 도구 연동을 위한 추상 기본 클래스
    모든 데이터 소스 클라이언트는 이 인터페이스를 구현해야 합니다.
    """
    
    def __init__(self, 연결정보: 데이터소스연결정보):
        """
        데이터 소스 클라이언트 초기화
        
        Args:
            연결정보: 데이터 소스 연결에 필요한 정보
        """
        self.연결정보 = 연결정보
        self.연결상태 = False
    
    @abstractmethod
    async def 연결테스트(self) -> bool:
        """
        데이터 소스와의 연결 상태를 테스트합니다.
        
        Returns:
            bool: 연결 성공 여부
        """
        pass
    
    @abstractmethod
    async def 메트릭수집(
        self, 
        서비스명: str, 
        메트릭타입: str,
        시작시간: datetime,
        종료시간: datetime
    ) -> List[메트릭데이터]:
        """
        지정된 기간의 메트릭 데이터를 수집합니다.
        
        Args:
            서비스명: 수집할 서비스 이름
            메트릭타입: 메트릭 유형 ('availability', 'response_time', 'throughput')
            시작시간: 수집 시작 시간
            종료시간: 수집 종료 시간
            
        Returns:
            List[메트릭데이터]: 수집된 메트릭 데이터 목록
        """
        pass
    
    @abstractmethod
    async def 사용가능한서비스목록조회(self) -> List[str]:
        """
        데이터 소스에서 사용 가능한 서비스 목록을 조회합니다.
        
        Returns:
            List[str]: 서비스 이름 목록
        """
        pass
    
    @abstractmethod
    def 데이터정규화(self, 원본데이터: Any) -> 메트릭데이터:
        """
        원본 데이터를 표준 메트릭 데이터 형식으로 정규화합니다.
        
        Args:
            원본데이터: 외부 시스템에서 받은 원본 데이터
            
        Returns:
            메트릭데이터: 정규화된 메트릭 데이터
        """
        pass
    
    def 연결상태확인(self) -> bool:
        """
        현재 연결 상태를 반환합니다.
        
        Returns:
            bool: 연결 상태
        """
        return self.연결상태