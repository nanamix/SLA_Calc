"""
Prometheus 모니터링 시스템과 연동하는 클라이언트
PromQL 쿼리를 통해 메트릭 데이터를 수집합니다.
"""

import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from urllib.parse import urljoin

from ..interfaces.데이터소스인터페이스 import 데이터소스인터페이스, 메트릭데이터, 데이터소스연결정보


class 프로메테우스클라이언트(데이터소스인터페이스):
    """
    Prometheus API를 통해 메트릭 데이터를 수집하는 클라이언트
    """
    
    def __init__(self, 연결정보: 데이터소스연결정보):
        """
        Prometheus 클라이언트 초기화
        
        Args:
            연결정보: Prometheus 서버 연결 정보
        """
        super().__init__(연결정보)
        self.로거 = logging.getLogger(__name__)
        self.세션: Optional[aiohttp.ClientSession] = None
        
        # Prometheus 특화 설정
        self.API_경로 = "/api/v1"
        self.쿼리_엔드포인트 = f"{self.API_경로}/query"
        self.범위쿼리_엔드포인트 = f"{self.API_경로}/query_range"
        
        # 기본 PromQL 쿼리 템플릿
        self.쿼리템플릿 = {
            'availability': 'up{{job="{서비스명}"}}',
            'response_time': 'http_request_duration_seconds{{job="{서비스명}"}}',
            'throughput': 'rate(http_requests_total{{job="{서비스명}"}}[5m])'
        }
    
    async def _세션생성(self) -> aiohttp.ClientSession:
        """
        HTTP 세션을 생성하고 인증 정보를 설정합니다.
        
        Returns:
            aiohttp.ClientSession: 설정된 HTTP 세션
        """
        if self.세션 is None or self.세션.closed:
            # 인증 정보 설정
            인증정보 = None
            if self.연결정보.인증정보:
                사용자명 = self.연결정보.인증정보.get('사용자명')
                비밀번호 = self.연결정보.인증정보.get('비밀번호')
                if 사용자명 and 비밀번호:
                    인증정보 = aiohttp.BasicAuth(사용자명, 비밀번호)
            
            # 타임아웃 설정
            타임아웃 = aiohttp.ClientTimeout(total=30)
            
            self.세션 = aiohttp.ClientSession(
                auth=인증정보,
                timeout=타임아웃,
                headers={'Content-Type': 'application/json'}
            )
        
        return self.세션
    
    async def 연결테스트(self) -> bool:
        """
        Prometheus 서버와의 연결 상태를 테스트합니다.
        
        Returns:
            bool: 연결 성공 여부
        """
        try:
            세션 = await self._세션생성()
            테스트_URL = urljoin(self.연결정보.엔드포인트, f"{self.API_경로}/label/__name__/values")
            
            async with 세션.get(테스트_URL) as 응답:
                if 응답.status == 200:
                    self.연결상태 = True
                    self.로거.info(f"Prometheus 서버 연결 성공: {self.연결정보.엔드포인트}")
                    return True
                else:
                    self.로거.error(f"Prometheus 서버 연결 실패: HTTP {응답.status}")
                    return False
                    
        except Exception as 오류:
            self.로거.error(f"Prometheus 연결 테스트 중 오류 발생: {str(오류)}")
            self.연결상태 = False
            return False
    
    async def 메트릭수집(
        self, 
        서비스명: str, 
        메트릭타입: str,
        시작시간: datetime,
        종료시간: datetime
    ) -> List[메트릭데이터]:
        """
        지정된 기간의 메트릭 데이터를 Prometheus에서 수집합니다.
        
        Args:
            서비스명: 수집할 서비스 이름
            메트릭타입: 메트릭 유형
            시작시간: 수집 시작 시간
            종료시간: 수집 종료 시간
            
        Returns:
            List[메트릭데이터]: 수집된 메트릭 데이터 목록
        """
        if not self.연결상태:
            await self.연결테스트()
        
        if not self.연결상태:
            raise ConnectionError("Prometheus 서버에 연결할 수 없습니다.")
        
        # PromQL 쿼리 생성
        쿼리 = self._쿼리생성(서비스명, 메트릭타입)
        if not 쿼리:
            raise ValueError(f"지원하지 않는 메트릭 타입: {메트릭타입}")
        
        try:
            세션 = await self._세션생성()
            쿼리_URL = urljoin(self.연결정보.엔드포인트, self.범위쿼리_엔드포인트)
            
            # 쿼리 파라미터 설정
            파라미터 = {
                'query': 쿼리,
                'start': 시작시간.timestamp(),
                'end': 종료시간.timestamp(),
                'step': '60s'  # 1분 간격
            }
            
            async with 세션.get(쿼리_URL, params=파라미터) as 응답:
                if 응답.status == 200:
                    응답데이터 = await 응답.json()
                    return self._응답데이터파싱(응답데이터, 서비스명, 메트릭타입)
                else:
                    오류메시지 = await 응답.text()
                    self.로거.error(f"Prometheus 쿼리 실패: HTTP {응답.status}, {오류메시지}")
                    return []
                    
        except Exception as 오류:
            self.로거.error(f"메트릭 수집 중 오류 발생: {str(오류)}")
            return []
    
    def _쿼리생성(self, 서비스명: str, 메트릭타입: str) -> Optional[str]:
        """
        메트릭 타입에 따른 PromQL 쿼리를 생성합니다.
        
        Args:
            서비스명: 서비스 이름
            메트릭타입: 메트릭 유형
            
        Returns:
            Optional[str]: 생성된 PromQL 쿼리
        """
        쿼리템플릿 = self.쿼리템플릿.get(메트릭타입)
        if 쿼리템플릿:
            return 쿼리템플릿.format(서비스명=서비스명)
        return None
    
    def _응답데이터파싱(
        self, 
        응답데이터: Dict[str, Any], 
        서비스명: str, 
        메트릭타입: str
    ) -> List[메트릭데이터]:
        """
        Prometheus API 응답 데이터를 파싱하여 메트릭 데이터로 변환합니다.
        
        Args:
            응답데이터: Prometheus API 응답 데이터
            서비스명: 서비스 이름
            메트릭타입: 메트릭 유형
            
        Returns:
            List[메트릭데이터]: 파싱된 메트릭 데이터 목록
        """
        메트릭목록 = []
        
        try:
            if 응답데이터.get('status') != 'success':
                self.로거.error(f"Prometheus 쿼리 실패: {응답데이터.get('error', '알 수 없는 오류')}")
                return 메트릭목록
            
            결과데이터 = 응답데이터.get('data', {}).get('result', [])
            
            for 시리즈 in 결과데이터:
                메트릭이름 = 시리즈.get('metric', {}).get('__name__', 'unknown')
                값목록 = 시리즈.get('values', [])
                
                for 타임스탬프, 값 in 값목록:
                    try:
                        메트릭데이터객체 = self.데이터정규화({
                            'metric_name': 메트릭이름,
                            'value': float(값),
                            'timestamp': float(타임스탬프),
                            'service': 서비스명,
                            'metric_type': 메트릭타입,
                            'labels': 시리즈.get('metric', {})
                        })
                        메트릭목록.append(메트릭데이터객체)
                        
                    except (ValueError, TypeError) as 오류:
                        self.로거.warning(f"메트릭 데이터 파싱 오류: {str(오류)}")
                        continue
            
            self.로거.info(f"{서비스명}의 {메트릭타입} 메트릭 {len(메트릭목록)}개 수집 완료")
            
        except Exception as 오류:
            self.로거.error(f"응답 데이터 파싱 중 오류 발생: {str(오류)}")
        
        return 메트릭목록
    
    async def 사용가능한서비스목록조회(self) -> List[str]:
        """
        Prometheus에서 사용 가능한 서비스 목록을 조회합니다.
        
        Returns:
            List[str]: 서비스 이름 목록
        """
        if not self.연결상태:
            await self.연결테스트()
        
        if not self.연결상태:
            return []
        
        try:
            세션 = await self._세션생성()
            라벨_URL = urljoin(self.연결정보.엔드포인트, f"{self.API_경로}/label/job/values")
            
            async with 세션.get(라벨_URL) as 응답:
                if 응답.status == 200:
                    응답데이터 = await 응답.json()
                    if 응답데이터.get('status') == 'success':
                        서비스목록 = 응답데이터.get('data', [])
                        self.로거.info(f"사용 가능한 서비스 {len(서비스목록)}개 발견")
                        return 서비스목록
                    
        except Exception as 오류:
            self.로거.error(f"서비스 목록 조회 중 오류 발생: {str(오류)}")
        
        return []
    
    def 데이터정규화(self, 원본데이터: Dict[str, Any]) -> 메트릭데이터:
        """
        Prometheus 원본 데이터를 표준 메트릭 데이터 형식으로 정규화합니다.
        
        Args:
            원본데이터: Prometheus에서 받은 원본 데이터
            
        Returns:
            메트릭데이터: 정규화된 메트릭 데이터
        """
        # 타임스탬프를 datetime 객체로 변환
        타임스탬프 = datetime.fromtimestamp(원본데이터['timestamp'])
        
        # 메트릭 타입에 따른 단위 설정
        단위매핑 = {
            'availability': '%',
            'response_time': 'seconds',
            'throughput': 'requests/sec'
        }
        
        메트릭타입 = 원본데이터['metric_type']
        단위 = 단위매핑.get(메트릭타입, 'unknown')
        
        # 가용성 메트릭의 경우 백분율로 변환 (0 또는 1 값을 0% 또는 100%로)
        값 = 원본데이터['value']
        if 메트릭타입 == 'availability':
            값 = 값 * 100  # 0 또는 1을 0% 또는 100%로 변환
        
        return 메트릭데이터(
            서비스명=원본데이터['service'],
            메트릭타입=메트릭타입,
            값=값,
            타임스탬프=타임스탬프,
            단위=단위,
            태그=원본데이터.get('labels', {}),
            원본데이터=원본데이터
        )
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        await self._세션생성()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.세션 and not self.세션.closed:
            await self.세션.close()