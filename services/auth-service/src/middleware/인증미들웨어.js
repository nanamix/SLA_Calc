const 토큰유틸 = require('../utils/토큰유틸');
const 사용자모델 = require('../models/사용자모델');

/**
 * JWT 토큰 기반 인증 미들웨어
 * 요청 헤더의 토큰을 검증하고 사용자 정보를 req.사용자에 설정
 */
const 인증확인 = async (req, res, next) => {
  try {
    // Authorization 헤더에서 토큰 추출
    const 인증헤더 = req.headers.authorization;
    const 토큰 = 토큰유틸.헤더에서토큰추출(인증헤더);

    if (!토큰) {
      return res.status(401).json({
        성공: false,
        메시지: '인증 토큰이 제공되지 않았습니다',
        오류코드: 'TOKEN_MISSING'
      });
    }

    // 토큰 블랙리스트 확인
    const 블랙리스트포함 = await 토큰유틸.블랙리스트확인(토큰);
    if (블랙리스트포함) {
      return res.status(401).json({
        성공: false,
        메시지: '무효한 토큰입니다',
        오류코드: 'TOKEN_BLACKLISTED'
      });
    }

    // 토큰 검증
    const 토큰정보 = 토큰유틸.토큰검증(토큰);
    if (!토큰정보) {
      return res.status(401).json({
        성공: false,
        메시지: '유효하지 않은 토큰입니다',
        오류코드: 'TOKEN_INVALID'
      });
    }

    // 액세스 토큰인지 확인
    if (토큰정보.토큰타입 !== 'access') {
      return res.status(401).json({
        성공: false,
        메시지: '잘못된 토큰 타입입니다',
        오류코드: 'TOKEN_TYPE_INVALID'
      });
    }

    // 데이터베이스에서 사용자 정보 조회
    const 사용자 = await 사용자모델.findById(토큰정보.사용자아이디);
    if (!사용자) {
      return res.status(401).json({
        성공: false,
        메시지: '사용자를 찾을 수 없습니다',
        오류코드: 'USER_NOT_FOUND'
      });
    }

    // 사용자 계정 활성 상태 확인
    if (!사용자.활성상태) {
      return res.status(401).json({
        성공: false,
        메시지: '비활성화된 계정입니다',
        오류코드: 'ACCOUNT_DISABLED'
      });
    }

    // 계정 잠금 상태 확인
    if (사용자.계정잠금확인()) {
      return res.status(401).json({
        성공: false,
        메시지: '계정이 잠겨있습니다. 잠시 후 다시 시도해주세요',
        오류코드: 'ACCOUNT_LOCKED'
      });
    }

    // 요청 객체에 사용자 정보 설정
    req.사용자 = 사용자;
    req.토큰정보 = 토큰정보;

    next();
  } catch (error) {
    console.error('인증 미들웨어 오류:', error);
    return res.status(500).json({
      성공: false,
      메시지: '인증 처리 중 오류가 발생했습니다',
      오류코드: 'AUTH_ERROR'
    });
  }
};

/**
 * 권한 확인 미들웨어 생성 함수
 * @param {string|Array<string>} 필요권한 - 필요한 권한 (문자열 또는 배열)
 * @returns {Function} 권한 확인 미들웨어 함수
 */
const 권한확인 = (필요권한) => {
  return (req, res, next) => {
    try {
      // 인증 확인이 선행되어야 함
      if (!req.사용자) {
        return res.status(401).json({
          성공: false,
          메시지: '인증이 필요합니다',
          오류코드: 'AUTH_REQUIRED'
        });
      }

      // 필요권한을 배열로 변환
      const 권한배열 = Array.isArray(필요권한) ? 필요권한 : [필요권한];
      
      // 사용자가 필요한 권한 중 하나라도 가지고 있는지 확인
      const 권한보유 = 권한배열.some(권한 => req.사용자.권한확인(권한));
      
      if (!권한보유) {
        return res.status(403).json({
          성공: false,
          메시지: '접근 권한이 없습니다',
          오류코드: 'PERMISSION_DENIED',
          필요권한: 권한배열,
          보유권한: req.사용자.권한목록
        });
      }

      next();
    } catch (error) {
      console.error('권한 확인 미들웨어 오류:', error);
      return res.status(500).json({
        성공: false,
        메시지: '권한 확인 중 오류가 발생했습니다',
        오류코드: 'PERMISSION_ERROR'
      });
    }
  };
};

/**
 * 역할 기반 접근 제어 미들웨어
 * @param {string|Array<string>} 허용역할 - 허용된 역할 (문자열 또는 배열)
 * @returns {Function} 역할 확인 미들웨어 함수
 */
const 역할확인 = (허용역할) => {
  return (req, res, next) => {
    try {
      // 인증 확인이 선행되어야 함
      if (!req.사용자) {
        return res.status(401).json({
          성공: false,
          메시지: '인증이 필요합니다',
          오류코드: 'AUTH_REQUIRED'
        });
      }

      // 허용역할을 배열로 변환
      const 역할배열 = Array.isArray(허용역할) ? 허용역할 : [허용역할];
      
      // 사용자 역할이 허용된 역할에 포함되는지 확인
      if (!역할배열.includes(req.사용자.역할)) {
        return res.status(403).json({
          성공: false,
          메시지: '접근 권한이 없습니다',
          오류코드: 'ROLE_DENIED',
          필요역할: 역할배열,
          현재역할: req.사용자.역할
        });
      }

      next();
    } catch (error) {
      console.error('역할 확인 미들웨어 오류:', error);
      return res.status(500).json({
        성공: false,
        메시지: '역할 확인 중 오류가 발생했습니다',
        오류코드: 'ROLE_ERROR'
      });
    }
  };
};

/**
 * 선택적 인증 미들웨어
 * 토큰이 있으면 검증하고, 없어도 통과시킴
 */
const 선택적인증 = async (req, res, next) => {
  try {
    const 인증헤더 = req.headers.authorization;
    const 토큰 = 토큰유틸.헤더에서토큰추출(인증헤더);

    // 토큰이 없으면 그냥 통과
    if (!토큰) {
      return next();
    }

    // 토큰이 있으면 검증 시도
    const 토큰정보 = 토큰유틸.토큰검증(토큰);
    if (토큰정보 && 토큰정보.토큰타입 === 'access') {
      const 사용자 = await 사용자모델.findById(토큰정보.사용자아이디);
      if (사용자 && 사용자.활성상태 && !사용자.계정잠금확인()) {
        req.사용자 = 사용자;
        req.토큰정보 = 토큰정보;
      }
    }

    next();
  } catch (error) {
    // 선택적 인증에서는 오류가 발생해도 통과
    console.warn('선택적 인증 중 오류 (무시됨):', error.message);
    next();
  }
};

module.exports = {
  인증확인,
  권한확인,
  역할확인,
  선택적인증
};