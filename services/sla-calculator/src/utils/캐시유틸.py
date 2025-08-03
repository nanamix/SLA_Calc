"""
Redis 캐시 관리 유틸리티
SLA 계산 결과 캐싱 및 성능 최적화
"""

import redis.asyncio as redis
import json
import logging
from typing import Any, Optional, Union, Dict, List
from datetime import datetime, timedelta
import pickle
import hashlib

logger = logging.getLogger(__name__)


class 캐시관리자:
    """Redis 기반 캐시 관리 클래스"""

    def __init__(self, redis_url: str = "redis://localhost:6379", 기본만료시간: int = 300):
        """
        캐시 관리자 초기화
        
        Args:
            redis_url: Redis 연결 URL
            기본만료시간: 기본 캐시 만료 시간 (초)
        """
        self.redis_url = redis_url
        self.기본만료시간 = 기본만료시간
        self.redis_client: Optional[redis.Redis] = None

    async def 연결(self):
        """Redis 서버에 연결합니다"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,  # 바이너리 데이터 지원을 위해 False
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # 연결 테스트
            await self.redis_client.ping()
            logger.info(f"Redis 연결 성공: {self.redis_url}")
            
        except Exception as e:
            logger.error(f"Redis 연결 실패: {e}")
            raise

    async def 연결해제(self):
        """Redis 연결을 해제합니다"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis 연결 해제 완료")

    async def set(self, 키: str, 값: Any, expire: Optional[int] = None) -> bool:
        """
        캐시에 데이터를 저장합니다
        
        Args:
            키: 캐시 키
            값: 저장할 값 (JSON 직렬화 가능한 객체)
            expire: 만료 시간 (초, None이면 기본값 사용)
            
        Returns:
            저장 성공 여부
        """
        if not self.redis_client:
            logger.warning("Redis 클라이언트가 연결되지 않았습니다")
            return False

        try:
            만료시간 = expire if expire is not None else self.기본만료시간
            
            # 데이터 직렬화
            직렬화된값 = await self._데이터_직렬화(값)
            
            # Redis에 저장
            결과 = await self.redis_client.setex(키, 만료시간, 직렬화된값)
            
            logger.debug(f"캐시 저장 성공: 키={키}, 만료시간={만료시간}초")
            return bool(결과)
            
        except Exception as e:
            logger.error(f"캐시 저장 실패: 키={키}, 오류={e}")
            return False

    async def get(self, 키: str) -> Optional[Any]:
        """
        캐시에서 데이터를 조회합니다
        
        Args:
            키: 캐시 키
            
        Returns:
            캐시된 값 또는 None (존재하지 않거나 만료된 경우)
        """
        if not self.redis_client:
            logger.warning("Redis 클라이언트가 연결되지 않았습니다")
            return None

        try:
            직렬화된값 = await self.redis_client.get(키)
            
            if 직렬화된값 is None:
                logger.debug(f"캐시 미스: 키={키}")
                return None
            
            # 데이터 역직렬화
            값 = await self._데이터_역직렬화(직렬화된값)
            
            logger.debug(f"캐시 히트: 키={키}")
            return 값
            
        except Exception as e:
            logger.error(f"캐시 조회 실패: 키={키}, 오류={e}")
            return None

    async def delete(self, 키: str) -> bool:
        """
        캐시에서 데이터를 삭제합니다
        
        Args:
            키: 삭제할 캐시 키
            
        Returns:
            삭제 성공 여부
        """
        if not self.redis_client:
            logger.warning("Redis 클라이언트가 연결되지 않았습니다")
            return False

        try:
            삭제된개수 = await self.redis_client.delete(키)
            
            if 삭제된개수 > 0:
                logger.debug(f"캐시 삭제 성공: 키={키}")
                return True
            else:
                logger.debug(f"캐시 삭제 대상 없음: 키={키}")
                return False
                
        except Exception as e:
            logger.error(f"캐시 삭제 실패: 키={키}, 오류={e}")
            return False

    async def exists(self, 키: str) -> bool:
        """
        캐시 키가 존재하는지 확인합니다
        
        Args:
            키: 확인할 캐시 키
            
        Returns:
            키 존재 여부
        """
        if not self.redis_client:
            return False

        try:
            존재여부 = await self.redis_client.exists(키)
            return bool(존재여부)
            
        except Exception as e:
            logger.error(f"캐시 존재 확인 실패: 키={키}, 오류={e}")
            return False

    async def expire(self, 키: str, 만료시간: int) -> bool:
        """
        기존 캐시 키의 만료 시간을 설정합니다
        
        Args:
            키: 캐시 키
            만료시간: 만료 시간 (초)
            
        Returns:
            설정 성공 여부
        """
        if not self.redis_client:
            return False

        try:
            결과 = await self.redis_client.expire(키, 만료시간)
            
            if 결과:
                logger.debug(f"캐시 만료시간 설정 성공: 키={키}, 만료시간={만료시간}초")
            else:
                logger.debug(f"캐시 만료시간 설정 실패 (키 없음): 키={키}")
                
            return bool(결과)
            
        except Exception as e:
            logger.error(f"캐시 만료시간 설정 실패: 키={키}, 오류={e}")
            return False

    async def 패턴삭제(self, 패턴: str) -> int:
        """
        패턴에 매칭되는 모든 캐시 키를 삭제합니다
        
        Args:
            패턴: 삭제할 키 패턴 (예: "sla_metrics:*")
            
        Returns:
            삭제된 키의 개수
        """
        if not self.redis_client:
            return 0

        try:
            # 패턴에 매칭되는 키 목록 조회
            키목록 = []
            async for 키 in self.redis_client.scan_iter(match=패턴):
                키목록.append(키.decode('utf-8') if isinstance(키, bytes) else 키)
            
            if not 키목록:
                logger.debug(f"패턴 매칭 키 없음: 패턴={패턴}")
                return 0
            
            # 키 일괄 삭제
            삭제된개수 = await self.redis_client.delete(*키목록)
            
            logger.info(f"패턴 캐시 삭제 완료: 패턴={패턴}, 삭제개수={삭제된개수}")
            return 삭제된개수
            
        except Exception as e:
            logger.error(f"패턴 캐시 삭제 실패: 패턴={패턴}, 오류={e}")
            return 0

    async def 캐시통계조회(self) -> Dict[str, Any]:
        """
        캐시 사용 통계를 조회합니다
        
        Returns:
            캐시 통계 정보
        """
        if not self.redis_client:
            return {}

        try:
            정보 = await self.redis_client.info()
            
            통계 = {
                "연결된_클라이언트수": 정보.get("connected_clients", 0),
                "사용된_메모리": 정보.get("used_memory_human", "0B"),
                "총_키개수": await self.redis_client.dbsize(),
                "히트율": 정보.get("keyspace_hits", 0) / max(정보.get("keyspace_hits", 0) + 정보.get("keyspace_misses", 0), 1) * 100,
                "업타임_초": 정보.get("uptime_in_seconds", 0)
            }
            
            logger.debug(f"캐시 통계: {통계}")
            return 통계
            
        except Exception as e:
            logger.error(f"캐시 통계 조회 실패: {e}")
            return {}

    async def _데이터_직렬화(self, 데이터: Any) -> bytes:
        """
        데이터를 직렬화합니다 (JSON 우선, 실패 시 pickle 사용)
        
        Args:
            데이터: 직렬화할 데이터
            
        Returns:
            직렬화된 바이트 데이터
        """
        try:
            # JSON 직렬화 시도 (더 빠르고 호환성 좋음)
            json_str = json.dumps(데이터, ensure_ascii=False, default=str)
            return f"json:{json_str}".encode('utf-8')
            
        except (TypeError, ValueError):
            # JSON 직렬화 실패 시 pickle 사용
            pickle_data = pickle.dumps(데이터)
            return b"pickle:" + pickle_data

    async def _데이터_역직렬화(self, 직렬화된데이터: bytes) -> Any:
        """
        직렬화된 데이터를 역직렬화합니다
        
        Args:
            직렬화된데이터: 직렬화된 바이트 데이터
            
        Returns:
            역직렬화된 원본 데이터
        """
        if 직렬화된데이터.startswith(b"json:"):
            # JSON 역직렬화
            json_str = 직렬화된데이터[5:].decode('utf-8')
            return json.loads(json_str)
            
        elif 직렬화된데이터.startswith(b"pickle:"):
            # pickle 역직렬화
            pickle_data = 직렬화된데이터[7:]
            return pickle.loads(pickle_data)
            
        else:
            # 레거시 데이터 (JSON으로 가정)
            try:
                return json.loads(직렬화된데이터.decode('utf-8'))
            except:
                return pickle.loads(직렬화된데이터)

    def 캐시키_생성(self, 접두사: str, **매개변수) -> str:
        """
        일관된 캐시 키를 생성합니다
        
        Args:
            접두사: 캐시 키 접두사
            **매개변수: 키 생성에 사용할 매개변수들
            
        Returns:
            생성된 캐시 키
        """
        # 매개변수를 정렬하여 일관된 키 생성
        정렬된매개변수 = sorted(매개변수.items())
        매개변수문자열 = ":".join([f"{키}={값}" for 키, 값 in 정렬된매개변수])
        
        if 매개변수문자열:
            캐시키 = f"{접두사}:{매개변수문자열}"
        else:
            캐시키 = 접두사
        
        # 키가 너무 긴 경우 해시 사용
        if len(캐시키) > 200:
            해시값 = hashlib.md5(캐시키.encode('utf-8')).hexdigest()
            캐시키 = f"{접두사}:hash:{해시값}"
        
        return 캐시키


# 전역 캐시 관리자 인스턴스
_전역캐시관리자: Optional[캐시관리자] = None


async def 캐시관리자_초기화(redis_url: str = "redis://localhost:6379") -> 캐시관리자:
    """
    전역 캐시 관리자를 초기화합니다
    
    Args:
        redis_url: Redis 연결 URL
        
    Returns:
        초기화된 캐시 관리자
    """
    global _전역캐시관리자
    
    if _전역캐시관리자 is None:
        _전역캐시관리자 = 캐시관리자(redis_url)
        await _전역캐시관리자.연결()
    
    return _전역캐시관리자


def 캐시관리자_가져오기() -> Optional[캐시관리자]:
    """
    전역 캐시 관리자를 반환합니다
    
    Returns:
        캐시 관리자 인스턴스 또는 None
    """
    return _전역캐시관리자


async def 캐시관리자_종료():
    """전역 캐시 관리자를 종료합니다"""
    global _전역캐시관리자
    
    if _전역캐시관리자:
        await _전역캐시관리자.연결해제()
        _전역캐시관리자 = None