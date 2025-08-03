const express = require('express');
const 사용자관리컨트롤러 = require('../controllers/사용자관리컨트롤러');
const { 인증확인, 권한확인, 역할확인 } = require('../middleware/인증미들웨어');

const 라우터 = express.Router();

/**
 * 사용자 관리 관련 API 라우터
 * 기본 경로: /api/users
 * 모든 엔드포인트는 인증이 필요하며, 대부분 관리자 권한이 필요함
 */

/**
 * 사용자 조회 관련 API
 */

// GET /api/users/stats - 사용자 통계 조회 (관리자 또는 매니저)
라우터.get('/stats', 
  인증확인, 
  역할확인(['admin', 'manager']), 
  사용자관리컨트롤러.사용자통계조회
);

// GET /api/users - 사용자 목록 조회 (사용자 읽기 권한 필요)
라우터.get('/', 
  인증확인, 
  권한확인('user:read'), 
  사용자관리컨트롤러.사용자목록조회
);

// GET /api/users/:id - 사용자 상세 조회 (사용자 읽기 권한 필요)
라우터.get('/:id', 
  인증확인, 
  권한확인('user:read'), 
  사용자관리컨트롤러.사용자상세조회
);

/**
 * 사용자 생성/수정/삭제 관련 API
 */

// POST /api/users - 사용자 생성 (사용자 쓰기 권한 필요)
라우터.post('/', 
  인증확인, 
  권한확인('user:write'), 
  사용자관리컨트롤러.사용자생성
);

// PUT /api/users/:id - 사용자 수정 (사용자 쓰기 권한 필요)
라우터.put('/:id', 
  인증확인, 
  권한확인('user:write'), 
  사용자관리컨트롤러.사용자수정
);

// DELETE /api/users/:id - 사용자 삭제 (관리자 권한 필요)
라우터.delete('/:id', 
  인증확인, 
  역할확인('admin'), 
  사용자관리컨트롤러.사용자삭제
);

/**
 * 사용자 계정 관리 관련 API
 */

// PATCH /api/users/:id/status - 계정 상태 변경 (사용자 쓰기 권한 필요)
라우터.patch('/:id/status', 
  인증확인, 
  권한확인('user:write'), 
  사용자관리컨트롤러.계정상태변경
);

// PATCH /api/users/:id/unlock - 계정 잠금 해제 (사용자 쓰기 권한 필요)
라우터.patch('/:id/unlock', 
  인증확인, 
  권한확인('user:write'), 
  사용자관리컨트롤러.계정잠금해제
);

// PATCH /api/users/:id/reset-password - 비밀번호 재설정 (관리자 권한 필요)
라우터.patch('/:id/reset-password', 
  인증확인, 
  역할확인('admin'), 
  사용자관리컨트롤러.비밀번호재설정
);

/**
 * API 문서화를 위한 라우터 정보
 */
라우터.get('/', (req, res) => {
  res.json({
    서비스명: 'SLA Calculator 사용자 관리 서비스',
    버전: '1.0.0',
    설명: '사용자 계정 관리를 담당하는 API',
    엔드포인트: {
      조회API: {
        'GET /api/users/stats': '사용자 통계 조회 (admin, manager)',
        'GET /api/users': '사용자 목록 조회 (user:read)',
        'GET /api/users/:id': '사용자 상세 조회 (user:read)'
      },
      관리API: {
        'POST /api/users': '사용자 생성 (user:write)',
        'PUT /api/users/:id': '사용자 수정 (user:write)',
        'DELETE /api/users/:id': '사용자 삭제 (admin)',
        'PATCH /api/users/:id/status': '계정 상태 변경 (user:write)',
        'PATCH /api/users/:id/unlock': '계정 잠금 해제 (user:write)',
        'PATCH /api/users/:id/reset-password': '비밀번호 재설정 (admin)'
      }
    },
    권한체계: {
      역할: ['admin', 'manager', 'viewer'],
      권한: [
        'user:read - 사용자 정보 조회',
        'user:write - 사용자 정보 관리',
        'system:admin - 시스템 관리자 권한'
      ]
    },
    상태: '정상 운영 중',
    마지막업데이트: new Date().toISOString()
  });
});

/**
 * 에러 핸들링 미들웨어
 */
라우터.use((error, req, res, next) => {
  console.error('사용자 관리 라우터 오류:', error);
  
  res.status(500).json({
    성공: false,
    메시지: '사용자 관리 처리 중 오류가 발생했습니다',
    오류코드: 'USER_MANAGEMENT_ERROR'
  });
});

module.exports = 라우터;