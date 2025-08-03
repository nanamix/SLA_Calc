/**
 * Redis 캐시 키 네이밍 전략 및 유틸리티 함수
 * SLA Calculator 애플리케이션용 캐시 관리 도구
 */

// 캐시 네임스페이스 정의
export enum 캐시네임스페이스 {
  메트릭 = 'metrics',
  세션 = 'sessions', 
  알림 = 'alerts',
  보고서 = 'reports',
  사용자 = 'users',
  서비스 = 'services',
  설정 = 'settings'
}

// 캐시 TTL 상수 (초 단위)
export const 캐시TTL = {
  짧음: 300,      // 5분
  보통: 1800,     // 30분
  길음: 3600,     // 1시간
  매우길음: 86400, // 24시간
  세션: 7200,     // 2시간
  메트릭: 300,    // 5분
  보고서: 3600    // 1시간
} as const;

/**
 * 캐시 키 생성 클래스
 * 일관된 키 네이밍 전략을 제공합니다
 */
export class 캐시키생성기 {
  private static readonly 키_접두사 = 'sla_calc';
  private static readonly 구분자 = ':';

  /**
   * 기본 캐시 키 생성
   * @param 네임스페이스 - 캐시 네임스페이스
   * @param 키요소들 - 키를 구성하는 요소들
   * @returns 생성된 캐시 키
   */
  static 키생성(네임스페이스: 캐시네임스페이스, ...키요소들: string[]): string {
    const 정리된요소들 = 키요소들
      .filter(요소 => 요소 && 요소.trim().length > 0)
      .map(요소 => 요소.trim().toLowerCase());
    
    return [
      this.키_접두사,
      네임스페이스,
      ...정리된요소들
    ].join(this.구분자);
  }

  /**
   * SLA 메트릭 캐시 키 생성
   * @param 서비스아이디 - 서비스 ID
   * @param 메트릭타입 - 메트릭 타입 (availability, response_time, throughput)
   * @param 시간범위 - 시간 범위 (optional)
   * @returns SLA 메트릭 캐시 키
   */
  static SLA메트릭키(서비스아이디: string, 메트릭타입: string, 시간범위?: string): string {
    const 키요소들 = [서비스아이디, 메트릭타입];
    if (시간범위) {
      키요소들.push(시간범위);
    }
    return this.키생성(캐시네임스페이스.메트릭, ...키요소들);
  }

  /**
   * 사용자 세션 캐시 키 생성
   * @param 사용자아이디 - 사용자 ID
   * @param 세션아이디 - 세션 ID (optional)
   * @returns 사용자 세션 캐시 키
   */
  static 사용자세션키(사용자아이디: string, 세션아이디?: string): string {
    const 키요소들 = [사용자아이디];
    if (세션아이디) {
      키요소들.push(세션아이디);
    }
    return this.키생성(캐시네임스페이스.세션, ...키요소들);
  }

  /**
   * 알림 설정 캐시 키 생성
   * @param 서비스아이디 - 서비스 ID
   * @param 알림타입 - 알림 타입 (optional)
   * @returns 알림 설정 캐시 키
   */
  static 알림설정키(서비스아이디: string, 알림타입?: string): string {
    const 키요소들 = [서비스아이디];
    if (알림타입) {
      키요소들.push(알림타입);
    }
    return this.키생성(캐시네임스페이스.알림, ...키요소들);
  }

  /**
   * 보고서 캐시 키 생성
   * @param 템플릿아이디 - 보고서 템플릿 ID
   * @param 생성일자 - 보고서 생성 일자 (YYYY-MM-DD 형식)
   * @returns 보고서 캐시 키
   */
  static 보고서키(템플릿아이디: string, 생성일자: string): string {
    return this.키생성(캐시네임스페이스.보고서, 템플릿아이디, 생성일자);
  }

  /**
   * 서비스 정보 캐시 키 생성
   * @param 서비스아이디 - 서비스 ID
   * @param 정보타입 - 정보 타입 (config, status, metrics 등)
   * @returns 서비스 정보 캐시 키
   */
  static 서비스정보키(서비스아이디: string, 정보타입: string): string {
    return this.키생성(캐시네임스페이스.서비스, 서비스아이디, 정보타입);
  }

  /**
   * 사용자 권한 캐시 키 생성
   * @param 사용자아이디 - 사용자 ID
   * @returns 사용자 권한 캐시 키
   */
  static 사용자권한키(사용자아이디: string): string {
    return this.키생성(캐시네임스페이스.사용자, 사용자아이디, 'permissions');
  }

  /**
   * 시스템 설정 캐시 키 생성
   * @param 설정명 - 설정 이름
   * @returns 시스템 설정 캐시 키
   */
  static 시스템설정키(설정명: string): string {
    return this.키생성(캐시네임스페이스.설정, 설정명);
  }

  /**
   * 패턴 매칭용 키 생성 (와일드카드 포함)
   * @param 네임스페이스 - 캐시 네임스페이스
   * @param 패턴요소들 - 패턴을 구성하는 요소들 (* 와일드카드 사용 가능)
   * @returns 패턴 매칭용 키
   */
  static 패턴키생성(네임스페이스: 캐시네임스페이스, ...패턴요소들: string[]): string {
    return [
      this.키_접두사,
      네임스페이스,
      ...패턴요소들
    ].join(this.구분자);
  }
}

/**
 * 캐시 데이터 직렬화/역직렬화 유틸리티
 */
export class 캐시직렬화 {
  /**
   * 객체를 JSON 문자열로 직렬화
   * @param 데이터 - 직렬화할 데이터
   * @returns JSON 문자열
   */
  static 직렬화<T>(데이터: T): string {
    try {
      return JSON.stringify(데이터);
    } catch (오류) {
      console.error('캐시 데이터 직렬화 오류:', 오류);
      throw new Error('캐시 데이터 직렬화에 실패했습니다');
    }
  }

  /**
   * JSON 문자열을 객체로 역직렬화
   * @param 문자열데이터 - 역직렬화할 JSON 문자열
   * @returns 역직렬화된 객체
   */
  static 역직렬화<T>(문자열데이터: string): T {
    try {
      return JSON.parse(문자열데이터);
    } catch (오류) {
      console.error('캐시 데이터 역직렬화 오류:', 오류);
      throw new Error('캐시 데이터 역직렬화에 실패했습니다');
    }
  }

  /**
   * 안전한 역직렬화 (오류 시 기본값 반환)
   * @param 문자열데이터 - 역직렬화할 JSON 문자열
   * @param 기본값 - 오류 시 반환할 기본값
   * @returns 역직렬화된 객체 또는 기본값
   */
  static 안전한역직렬화<T>(문자열데이터: string, 기본값: T): T {
    try {
      return JSON.parse(문자열데이터);
    } catch (오류) {
      console.warn('캐시 데이터 역직렬화 실패, 기본값 사용:', 오류);
      return 기본값;
    }
  }
}

/**
 * 캐시 만료 시간 계산 유틸리티
 */
export class 캐시만료계산 {
  /**
   * 현재 시간으로부터 TTL 초 후의 만료 시간 계산
   * @param TTL초 - TTL 값 (초 단위)
   * @returns 만료 시간 (Unix timestamp)
   */
  static TTL만료시간계산(TTL초: number): number {
    return Math.floor(Date.now() / 1000) + TTL초;
  }

  /**
   * 특정 시간까지의 TTL 계산
   * @param 만료시간 - 만료 시간 (Date 객체)
   * @returns TTL 값 (초 단위)
   */
  static 시간까지TTL계산(만료시간: Date): number {
    const 현재시간 = new Date();
    const 차이밀리초 = 만료시간.getTime() - 현재시간.getTime();
    return Math.max(0, Math.floor(차이밀리초 / 1000));
  }

  /**
   * 다음 정시까지의 TTL 계산 (예: 다음 시간의 00분 00초)
   * @returns 다음 정시까지의 TTL (초 단위)
   */
  static 다음정시까지TTL(): number {
    const 현재시간 = new Date();
    const 다음정시 = new Date(현재시간);
    다음정시.setHours(현재시간.getHours() + 1, 0, 0, 0);
    
    return this.시간까지TTL계산(다음정시);
  }

  /**
   * 자정까지의 TTL 계산
   * @returns 자정까지의 TTL (초 단위)
   */
  static 자정까지TTL(): number {
    const 현재시간 = new Date();
    const 자정 = new Date(현재시간);
    자정.setDate(현재시간.getDate() + 1);
    자정.setHours(0, 0, 0, 0);
    
    return this.시간까지TTL계산(자정);
  }
}

/**
 * 캐시 키 패턴 상수
 */
export const 캐시키패턴 = {
  // 모든 SLA 메트릭
  모든_SLA_메트릭: 캐시키생성기.패턴키생성(캐시네임스페이스.메트릭, '*'),
  
  // 특정 서비스의 모든 메트릭
  서비스_모든_메트릭: (서비스아이디: string) => 
    캐시키생성기.패턴키생성(캐시네임스페이스.메트릭, 서비스아이디, '*'),
  
  // 모든 사용자 세션
  모든_사용자_세션: 캐시키생성기.패턴키생성(캐시네임스페이스.세션, '*'),
  
  // 특정 사용자의 모든 세션
  사용자_모든_세션: (사용자아이디: string) => 
    캐시키생성기.패턴키생성(캐시네임스페이스.세션, 사용자아이디, '*'),
  
  // 모든 알림 설정
  모든_알림_설정: 캐시키생성기.패턴키생성(캐시네임스페이스.알림, '*'),
  
  // 모든 보고서
  모든_보고서: 캐시키생성기.패턴키생성(캐시네임스페이스.보고서, '*')
} as const;