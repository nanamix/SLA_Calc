const express = require('express');
const rateLimit = require('express-rate-limit');
const 인증컨트롤러 = require('../controllers/인증컨트롤러');
const { 인증확인 } = require('../middleware/인증미들웨어');

const 라우터 = express.Router();

/**
 * 인증 관련 API 라우터
 * 기본 경로: /api/auth
 */

// 로그인 시도 제한 (5분 동안 최대 5회)
const 로그인제한 = rateLimit({
  windowMs: 5 * 60 * 1000, // 5분
  max: 5, // 최대 5회 시도
  message: {
    성공: false,
    메시지: '로그인 시도가 너무 많습니다. 5분 후 다시 시도해주세요',
    오류코드: 'TOO_MANY_LOGIN_ATTEMPTS'
  },
  standardHeaders: true,
  legacyHeaders: false,
  // IP별로 제한 적용
  keyGenerator: (req) => req.ip,
  // 성공 시 카운터 리셋
  skipSuccessfulRequests: true
});

// 회원가입 제한 (1시간 동안 최대 3회)
const 회원가입제한 = rateLimit({
  windowMs: 60 * 60 * 1000, // 1시간
  max: 3, // 최대 3회 시도
  message: {
    성공: false,
    메시지: '회원가입 시도가 너무 많습니다. 1시간 후 다시 시도해주세요',
    오류코드: 'TOO_MANY_REGISTER_ATTEMPTS'
  },
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req) => req.ip
});

// 비밀번호 변경 제한 (1시간 동안 최대 3회)
const 비밀번호변경제한 = rateLimit({
  windowMs: 60 * 60 * 1000, // 1시간
  max: 3, // 최대 3회 시도
  message: {
    성공: false,
    메시지: '비밀번호 변경 시도가 너무 많습니다. 1시간 후 다시 시도해주세요',
    오류코드: 'TOO_MANY_PASSWORD_CHANGE_ATTEMPTS'
  },
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req) => req.사용자?._id || req.ip
});

/**
 * 공개 API 엔드포인트 (인증 불필요)
 */

// POST /api/auth/register - 회원가입
라우터.post('/register', 회원가입제한, 인증컨트롤러.회원가입);

// POST /api/auth/login - 로그인
라우터.post('/login', 로그인제한, 인증컨트롤러.로그인);

// POST /api/auth/refresh - 토큰 갱신
라우터.post('/refresh', 인증컨트롤러.토큰갱신);

/**
 * 보호된 API 엔드포인트 (인증 필요)
 */

// POST /api/auth/logout - 로그아웃
라우터.post('/logout', 인증확인, 인증컨트롤러.로그아웃);

// PUT /api/auth/password - 비밀번호 변경
라우터.put('/password', 인증확인, 비밀번호변경제한, 인증컨트롤러.비밀번호변경);

// GET /api/auth/profile - 프로필 조회
라우터.get('/profile', 인증확인, 인증컨트롤러.프로필조회);

// PUT /api/auth/profile - 프로필 수정
라우터.put('/profile', 인증확인, 인증컨트롤러.프로필수정);

// POST /api/auth/verify - 토큰 검증 (다른 서비스에서 사용)
라우터.post('/verify', 인증확인, 인증컨트롤러.토큰검증);

/**
 * API 문서화를 위한 라우터 정보
 */
라우터.get('/', (req, res) => {
  res.json({
    서비스명: 'SLA Calculator 인증 서비스',
    버전: '1.0.0',
    설명: '사용자 인증 및 권한 관리를 담당하는 마이크로서비스',
    엔드포인트: {
      공개API: {
        'POST /api/auth/register': '회원가입',
        'POST /api/auth/login': '로그인',
        'POST /api/auth/refresh': '토큰 갱신'
      },
      보호된API: {
        'POST /api/auth/logout': '로그아웃',
        'PUT /api/auth/password': '비밀번호 변경',
        'GET /api/auth/profile': '프로필 조회',
        'PUT /api/auth/profile': '프로필 수정',
        'POST /api/auth/verify': '토큰 검증'
      }
    },
    상태: '정상 운영 중',
    마지막업데이트: new Date().toISOString()
  });
});

module.exports = 라우터;