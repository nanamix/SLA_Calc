"""
Grafana 대시보드 시스템과 연동하는 클라이언트
Grafana API를 통해 대시보드 데이터와 메트릭을 수집합니다.
"""

import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from urllib.parse import urljoin

from ..interfaces.데이터소스인터페이스 import 데이터소스인터페이스, 메트릭데이터, 데이터소스연결정보


class 그라파나클라이언트(데이터소스인터페이스):
    """
    Grafana API를 통해 대시보드 데이터를 수집하는 클라이언트
    """
    
    def __init__(self, 연결정보: 데이터소스연결정보):
        """
        Grafana 클라이언트 초기화
        
        Args:
            연결정보: Grafana 서버 연결 정보
        """
        super().__init__(연결정보)
        self.로거 = logging.getLogger(__name__)
        self.세션: Optional[aiohttp.ClientSession] = None
        
        # Grafana API 엔드포인트
        self.API_경로 = "/api"
        self.대시보드_엔드포인트 = f"{self.API_경로}/dashboards"
        self.데이터소스_엔드포인트 = f"{self.API_경로}/datasources"
        self.쿼리_엔드포인트 = f"{self.API_경로}/ds/query"
        
        # 기본 헤더 설정
        self.기본헤더 = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    async def _세션생성(self) -> aiohttp.ClientSession:
        """
        HTTP 세션을 생성하고 인증 정보를 설정합니다.
        
        Returns:
            aiohttp.ClientSession: 설정된 HTTP 세션
        """
        if self.세션 is None or self.세션.closed:
            헤더 = self.기본헤더.copy()
            
            # API 키 또는 기본 인증 설정
            if self.연결정보.인증정보:
                API_키 = self.연결정보.인증정보.get('API_키')
                if API_키:
                    헤더['Authorization'] = f'Bearer {API_키}'
                else:
                    사용자명 = self.연결정보.인증정보.get('사용자명')
                    비밀번호 = self.연결정보.인증정보.get('비밀번호')
                    if 사용자명 and 비밀번호:
                        import base64
                        인증문자열 = base64.b64encode(f'{사용자명}:{비밀번호}'.encode()).decode()
                        헤더['Authorization'] = f'Basic {인증문자열}'
            
            # 타임아웃 설정
            타임아웃 = aiohttp.ClientTimeout(total=30)
            
            self.세션 = aiohttp.ClientSession(
                timeout=타임아웃,
                headers=헤더
            )
        
        return self.세션
    
    async def 연결테스트(self) -> bool:
        """
        Grafana 서버와의 연결 상태를 테스트합니다.
        
        Returns:
            bool: 연결 성공 여부
        """
        try:
            세션 = await self._세션생성()
            테스트_URL = urljoin(self.연결정보.엔드포인트, f"{self.API_경로}/health")
            
            async with 세션.get(테스트_URL) as 응답:
                if 응답.status == 200:
                    self.연결상태 = True
                    self.로거.info(f"Grafana 서버 연결 성공: {self.연결정보.엔드포인트}")
                    return True
                else:
                    self.로거.error(f"Grafana 서버 연결 실패: HTTP {응답.status}")
                    return False
                    
        except Exception as 오류:
            self.로거.error(f"Grafana 연결 테스트 중 오류 발생: {str(오류)}")
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
        지정된 기간의 메트릭 데이터를 Grafana에서 수집합니다.
        
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
            raise ConnectionError("Grafana 서버에 연결할 수 없습니다.")
        
        try:
            # 먼저 관련 대시보드를 찾습니다
            대시보드목록 = await self._서비스관련대시보드검색(서비스명)
            
            if not 대시보드목록:
                self.로거.warning(f"{서비스명}과 관련된 대시보드를 찾을 수 없습니다.")
                return []
            
            메트릭목록 = []
            
            # 각 대시보드에서 메트릭 데이터 수집
            for 대시보드 in 대시보드목록:
                대시보드메트릭 = await self._대시보드메트릭수집(
                    대시보드, 서비스명, 메트릭타입, 시작시간, 종료시간
                )
                메트릭목록.extend(대시보드메트릭)
            
            self.로거.info(f"{서비스명}의 {메트릭타입} 메트릭 {len(메트릭목록)}개 수집 완료")
            return 메트릭목록
            
        except Exception as 오류:
            self.로거.error(f"메트릭 수집 중 오류 발생: {str(오류)}")
            return []
    
    async def _서비스관련대시보드검색(self, 서비스명: str) -> List[Dict[str, Any]]:
        """
        서비스와 관련된 대시보드를 검색합니다.
        
        Args:
            서비스명: 검색할 서비스 이름
            
        Returns:
            List[Dict[str, Any]]: 관련 대시보드 목록
        """
        try:
            세션 = await self._세션생성()
            검색_URL = urljoin(self.연결정보.엔드포인트, f"{self.API_경로}/search")
            
            # 서비스명으로 대시보드 검색
            파라미터 = {
                'query': 서비스명,
                'type': 'dash-db'
            }
            
            async with 세션.get(검색_URL, params=파라미터) as 응답:
                if 응답.status == 200:
                    대시보드목록 = await 응답.json()
                    self.로거.info(f"{서비스명} 관련 대시보드 {len(대시보드목록)}개 발견")
                    return 대시보드목록
                else:
                    self.로거.error(f"대시보드 검색 실패: HTTP {응답.status}")
                    return []
                    
        except Exception as 오류:
            self.로거.error(f"대시보드 검색 중 오류 발생: {str(오류)}")
            return []
    
    async def _대시보드메트릭수집(
        self,
        대시보드: Dict[str, Any],
        서비스명: str,
        메트릭타입: str,
        시작시간: datetime,
        종료시간: datetime
    ) -> List[메트릭데이터]:
        """
        특정 대시보드에서 메트릭 데이터를 수집합니다.
        
        Args:
            대시보드: 대시보드 정보
            서비스명: 서비스 이름
            메트릭타입: 메트릭 유형
            시작시간: 수집 시작 시간
            종료시간: 수집 종료 시간
            
        Returns:
            List[메트릭데이터]: 수집된 메트릭 데이터 목록
        """
        try:
            세션 = await self._세션생성()
            대시보드_UID = 대시보드.get('uid')
            
            if not 대시보드_UID:
                return []
            
            # 대시보드 상세 정보 조회
            대시보드_URL = urljoin(
                self.연결정보.엔드포인트, 
                f"{self.대시보드_엔드포인트}/uid/{대시보드_UID}"
            )
            
            async with 세션.get(대시보드_URL) as 응답:
                if 응답.status != 200:
                    return []
                
                대시보드상세 = await 응답.json()
                패널목록 = 대시보드상세.get('dashboard', {}).get('panels', [])
                
                메트릭목록 = []
                
                # 각 패널에서 관련 메트릭 추출
                for 패널 in 패널목록:
                    if self._패널이메트릭타입과일치(패널, 메트릭타입):
                        패널메트릭 = await self._패널메트릭수집(
                            패널, 서비스명, 메트릭타입, 시작시간, 종료시간
                        )
                        메트릭목록.extend(패널메트릭)
                
                return 메트릭목록
                
        except Exception as 오류:
            self.로거.error(f"대시보드 메트릭 수집 중 오류 발생: {str(오류)}")
            return []
    
    def _패널이메트릭타입과일치(self, 패널: Dict[str, Any], 메트릭타입: str) -> bool:
        """
        패널이 요청된 메트릭 타입과 일치하는지 확인합니다.
        
        Args:
            패널: 대시보드 패널 정보
            메트릭타입: 확인할 메트릭 타입
            
        Returns:
            bool: 일치 여부
        """
        패널제목 = 패널.get('title', '').lower()
        
        # 메트릭 타입별 키워드 매칭
        키워드매핑 = {
            'availability': ['uptime', 'availability', '가용성', 'up'],
            'response_time': ['response', 'latency', '응답시간', 'duration'],
            'throughput': ['throughput', 'requests', 'rps', '처리량', 'rate']
        }
        
        키워드목록 = 키워드매핑.get(메트릭타입, [])
        return any(키워드 in 패널제목 for 키워드 in 키워드목록)
    
    async def _패널메트릭수집(
        self,
        패널: Dict[str, Any],
        서비스명: str,
        메트릭타입: str,
        시작시간: datetime,
        종료시간: datetime
    ) -> List[메트릭데이터]:
        """
        특정 패널에서 메트릭 데이터를 수집합니다.
        
        Args:
            패널: 패널 정보
            서비스명: 서비스 이름
            메트릭타입: 메트릭 유형
            시작시간: 수집 시작 시간
            종료시간: 수집 종료 시간
            
        Returns:
            List[메트릭데이터]: 수집된 메트릭 데이터 목록
        """
        # 실제 구현에서는 패널의 쿼리를 실행하여 데이터를 수집합니다.
        # 여기서는 간단한 예시 데이터를 반환합니다.
        
        메트릭목록 = []
        
        try:
            # 패널의 타겟(쿼리) 정보 추출
            타겟목록 = 패널.get('targets', [])
            
            for 타겟 in 타겟목록:
                if not 타겟.get('hide', False):  # 숨겨지지 않은 쿼리만 처리
                    # 간단한 모의 데이터 생성 (실제로는 Grafana API를 통해 쿼리 실행)
                    현재시간 = 시작시간
                    while 현재시간 <= 종료시간:
                        메트릭데이터객체 = self.데이터정규화({
                            'panel_title': 패널.get('title', 'Unknown'),
                            'value': self._모의값생성(메트릭타입),
                            'timestamp': 현재시간.timestamp(),
                            'service': 서비스명,
                            'metric_type': 메트릭타입,
                            'target': 타겟
                        })
                        메트릭목록.append(메트릭데이터객체)
                        현재시간 += timedelta(minutes=1)
            
        except Exception as 오류:
            self.로거.error(f"패널 메트릭 수집 중 오류 발생: {str(오류)}")
        
        return 메트릭목록
    
    def _모의값생성(self, 메트릭타입: str) -> float:
        """
        테스트용 모의 메트릭 값을 생성합니다.
        
        Args:
            메트릭타입: 메트릭 유형
            
        Returns:
            float: 모의 메트릭 값
        """
        import random
        
        if 메트릭타입 == 'availability':
            return random.choice([99.9, 99.95, 100.0])  # 가용성 백분율
        elif 메트릭타입 == 'response_time':
            return random.uniform(0.1, 2.0)  # 응답시간 (초)
        elif 메트릭타입 == 'throughput':
            return random.uniform(100, 1000)  # 처리량 (requests/sec)
        else:
            return random.uniform(0, 100)
    
    async def 사용가능한서비스목록조회(self) -> List[str]:
        """
        Grafana에서 사용 가능한 서비스 목록을 조회합니다.
        
        Returns:
            List[str]: 서비스 이름 목록
        """
        if not self.연결상태:
            await self.연결테스트()
        
        if not self.연결상태:
            return []
        
        try:
            세션 = await self._세션생성()
            검색_URL = urljoin(self.연결정보.엔드포인트, f"{self.API_경로}/search")
            
            # 모든 대시보드 검색
            파라미터 = {'type': 'dash-db'}
            
            async with 세션.get(검색_URL, params=파라미터) as 응답:
                if 응답.status == 200:
                    대시보드목록 = await 응답.json()
                    
                    # 대시보드 제목에서 서비스명 추출
                    서비스목록 = set()
                    for 대시보드 in 대시보드목록:
                        제목 = 대시보드.get('title', '')
                        # 간단한 서비스명 추출 로직 (실제로는 더 정교한 파싱 필요)
                        if '-' in 제목:
                            서비스명 = 제목.split('-')[0].strip()
                            서비스목록.add(서비스명)
                    
                    서비스목록_리스트 = list(서비스목록)
                    self.로거.info(f"사용 가능한 서비스 {len(서비스목록_리스트)}개 발견")
                    return 서비스목록_리스트
                    
        except Exception as 오류:
            self.로거.error(f"서비스 목록 조회 중 오류 발생: {str(오류)}")
        
        return []
    
    def 데이터정규화(self, 원본데이터: Dict[str, Any]) -> 메트릭데이터:
        """
        Grafana 원본 데이터를 표준 메트릭 데이터 형식으로 정규화합니다.
        
        Args:
            원본데이터: Grafana에서 받은 원본 데이터
            
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
        
        return 메트릭데이터(
            서비스명=원본데이터['service'],
            메트릭타입=메트릭타입,
            값=원본데이터['value'],
            타임스탬프=타임스탬프,
            단위=단위,
            태그={'panel_title': 원본데이터.get('panel_title', '')},
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