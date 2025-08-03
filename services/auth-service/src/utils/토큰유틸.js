const jwt = require('jsonwebtoken');
const crypto = require('crypto');

/**
 * JWT 토큰 관리 유틸리티 클래스
 * 액세스 토큰과 리프레시 토큰의 생성, 검증, 갱신을 담당
 */
class 토큰유틸 {
  constructor() {
    this.JWT_SECRET = process.env.JWT_SECRET || 'default-secret-key';
    this.JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '24h';
    this.JWT_REFRESH_EXPIRES_IN = process.env.JWT_REFRESH_EXPIRES_IN || '7d';
  }

  /**
   * 액세스 토큰 생성
   * @param {Object} 사용자정보 - 토큰에 포함할 사용자 정보
   * @returns {string} JWT 액세스 토큰
   */
  액세스토큰생성(사용자정보) {
    const 페이로드 = {
      사용자아이디: 사용자정보._id,
      이메일: 사용자정보.이메일,
      이름: 사용자정보.이름,
      역할: 사용자정보.역할,
      권한목록: 사용자정보.권한목록,
      토큰타입: 'access'
    };

    return jwt.sign(페이로드, this.JWT_SECRET, {
      expiresIn: this.JWT_EXPIRES_IN,
      issuer: 'sla-calculator-auth',
      audience: 'sla-calculator-app'
    });
  }

  /**
   * 리프레시 토큰 생성
   * @param {string} 사용자아이디 - 사용자 ID
   * @returns {string} JWT 리프레시 토큰
   */
  리프레시토큰생성(사용자아이디) {
    const 페이로드 = {
      사용자아이디: 사용자아이디,
      토큰타입: 'refresh',
      무작위값: crypto.randomBytes(16).toString('hex') // 토큰 고유성 보장
    };

    return jwt.sign(페이로드, this.JWT_SECRET, {
      expiresIn: this.JWT_REFRESH_EXPIRES_IN,
      issuer: 'sla-calculator-auth',
      audience: 'sla-calculator-app'
    });
  }

  /**
   * 토큰 검증
   * @param {string} 토큰 - 검증할 JWT 토큰
   * @returns {Object|null} 디코딩된 토큰 정보 또는 null
   */
  토큰검증(토큰) {
    try {
      const 디코딩결과 = jwt.verify(토큰, this.JWT_SECRET, {
        issuer: 'sla-calculator-auth',
        audience: 'sla-calculator-app'
      });

      return 디코딩결과;
    } catch (error) {
      console.error('토큰 검증 실패:', error.message);
      return null;
    }
  }

  /**
   * 토큰 만료 시간 확인
   * @param {string} 토큰 - 확인할 JWT 토큰
   * @returns {Object} 만료 정보
   */
  토큰만료시간확인(토큰) {
    try {
      const 디코딩결과 = jwt.decode(토큰);
      
      if (!디코딩결과 || !디코딩결과.exp) {
        return { 유효함: false, 메시지: '유효하지 않은 토큰입니다' };
      }

      const 현재시간 = Math.floor(Date.now() / 1000);
      const 만료시간 = 디코딩결과.exp;
      const 남은시간 = 만료시간 - 현재시간;

      return {
        유효함: 남은시간 > 0,
        만료시간: new Date(만료시간 * 1000),
        남은시간초: Math.max(0, 남은시간),
        곧만료됨: 남은시간 > 0 && 남은시간 < 300 // 5분 이내 만료
      };
    } catch (error) {
      return { 유효함: false, 메시지: '토큰 파싱 실패' };
    }
  }

  /**
   * 토큰에서 사용자 정보 추출
   * @param {string} 토큰 - JWT 토큰
   * @returns {Object|null} 사용자 정보 또는 null
   */
  사용자정보추출(토큰) {
    const 검증결과 = this.토큰검증(토큰);
    
    if (!검증결과) {
      return null;
    }

    return {
      사용자아이디: 검증결과.사용자아이디,
      이메일: 검증결과.이메일,
      이름: 검증결과.이름,
      역할: 검증결과.역할,
      권한목록: 검증결과.권한목록
    };
  }

  /**
   * 토큰 갱신
   * @param {string} 리프레시토큰 - 리프레시 토큰
   * @param {Object} 사용자정보 - 새 토큰에 포함할 사용자 정보
   * @returns {Object|null} 새로운 토큰 정보 또는 null
   */
  토큰갱신(리프레시토큰, 사용자정보) {
    const 검증결과 = this.토큰검증(리프레시토큰);
    
    if (!검증결과 || 검증결과.토큰타입 !== 'refresh') {
      return null;
    }

    // 사용자 ID 일치 확인
    if (검증결과.사용자아이디 !== 사용자정보._id.toString()) {
      return null;
    }

    // 새로운 토큰 생성
    const 새액세스토큰 = this.액세스토큰생성(사용자정보);
    const 새리프레시토큰 = this.리프레시토큰생성(사용자정보._id);

    return {
      액세스토큰: 새액세스토큰,
      리프레시토큰: 새리프레시토큰,
      토큰타입: 'Bearer',
      만료시간: this.JWT_EXPIRES_IN
    };
  }

  /**
   * Authorization 헤더에서 토큰 추출
   * @param {string} 인증헤더 - Authorization 헤더 값
   * @returns {string|null} 추출된 토큰 또는 null
   */
  헤더에서토큰추출(인증헤더) {
    if (!인증헤더) {
      return null;
    }

    const 토큰부분 = 인증헤더.split(' ');
    
    if (토큰부분.length !== 2 || 토큰부분[0] !== 'Bearer') {
      return null;
    }

    return 토큰부분[1];
  }

  /**
   * 토큰 블랙리스트 확인 (Redis 연동 시 구현)
   * @param {string} 토큰 - 확인할 토큰
   * @returns {Promise<boolean>} 블랙리스트 포함 여부
   */
  async 블랙리스트확인(토큰) {
    // TODO: Redis 연동 시 구현
    // 현재는 항상 false 반환 (블랙리스트 없음)
    return false;
  }

  /**
   * 토큰을 블랙리스트에 추가 (로그아웃 시 사용)
   * @param {string} 토큰 - 블랙리스트에 추가할 토큰
   * @returns {Promise<boolean>} 추가 성공 여부
   */
  async 블랙리스트추가(토큰) {
    // TODO: Redis 연동 시 구현
    // 현재는 항상 true 반환 (성공으로 간주)
    return true;
  }
}

// 싱글톤 인스턴스 생성
const 토큰유틸인스턴스 = new 토큰유틸();

module.exports = 토큰유틸인스턴스;