const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

/**
 * 사용자 스키마 정의
 * 사용자 정보, 권한, 인증 관련 데이터를 관리
 */
const 사용자스키마 = new mongoose.Schema({
  이메일: {
    type: String,
    required: [true, '이메일은 필수 입력 항목입니다'],
    unique: true,
    lowercase: true,
    trim: true,
    match: [/^\w+([.-]?\w+)*@\w+([.-]?\w+)*(\.\w{2,3})+$/, '유효한 이메일 주소를 입력해주세요']
  },
  
  이름: {
    type: String,
    required: [true, '이름은 필수 입력 항목입니다'],
    trim: true,
    minlength: [2, '이름은 최소 2자 이상이어야 합니다'],
    maxlength: [50, '이름은 최대 50자까지 입력 가능합니다']
  },
  
  비밀번호: {
    type: String,
    required: [true, '비밀번호는 필수 입력 항목입니다'],
    minlength: [8, '비밀번호는 최소 8자 이상이어야 합니다'],
    select: false // 기본적으로 조회 시 제외
  },
  
  역할: {
    type: String,
    enum: {
      values: ['admin', 'manager', 'viewer'],
      message: '역할은 admin, manager, viewer 중 하나여야 합니다'
    },
    default: 'viewer'
  },
  
  권한목록: [{
    type: String,
    enum: [
      'service:read',    // 서비스 조회
      'service:write',   // 서비스 생성/수정
      'service:delete',  // 서비스 삭제
      'sla:read',        // SLA 데이터 조회
      'sla:calculate',   // SLA 계산 실행
      'alert:read',      // 알림 설정 조회
      'alert:write',     // 알림 설정 변경
      'report:read',     // 보고서 조회
      'report:generate', // 보고서 생성
      'user:read',       // 사용자 조회
      'user:write',      // 사용자 관리
      'system:admin'     // 시스템 관리
    ]
  }],
  
  활성상태: {
    type: Boolean,
    default: true
  },
  
  생성일시: {
    type: Date,
    default: Date.now
  },
  
  수정일시: {
    type: Date,
    default: Date.now
  },
  
  마지막로그인일시: {
    type: Date
  },
  
  로그인실패횟수: {
    type: Number,
    default: 0
  },
  
  계정잠금일시: {
    type: Date
  },
  
  비밀번호변경일시: {
    type: Date,
    default: Date.now
  },
  
  리프레시토큰: {
    type: String,
    select: false
  }
}, {
  timestamps: { createdAt: '생성일시', updatedAt: '수정일시' }
});

/**
 * 비밀번호 암호화 미들웨어
 * 사용자 생성 또는 비밀번호 변경 시 자동으로 해시화
 */
사용자스키마.pre('save', async function(next) {
  // 비밀번호가 변경되지 않았으면 건너뛰기
  if (!this.isModified('비밀번호')) return next();
  
  try {
    // 비밀번호 해시화
    const 솔트라운드 = parseInt(process.env.BCRYPT_ROUNDS) || 12;
    this.비밀번호 = await bcrypt.hash(this.비밀번호, 솔트라운드);
    this.비밀번호변경일시 = new Date();
    next();
  } catch (error) {
    next(error);
  }
});

/**
 * 역할별 기본 권한 설정
 */
사용자스키마.pre('save', function(next) {
  if (this.isNew || this.isModified('역할')) {
    this.권한목록 = this.역할별기본권한가져오기(this.역할);
  }
  next();
});

/**
 * 비밀번호 검증 메서드
 * @param {string} 입력비밀번호 - 검증할 비밀번호
 * @returns {Promise<boolean>} 비밀번호 일치 여부
 */
사용자스키마.methods.비밀번호검증 = async function(입력비밀번호) {
  return await bcrypt.compare(입력비밀번호, this.비밀번호);
};

/**
 * 권한 확인 메서드
 * @param {string} 필요권한 - 확인할 권한
 * @returns {boolean} 권한 보유 여부
 */
사용자스키마.methods.권한확인 = function(필요권한) {
  return this.권한목록.includes(필요권한) || this.권한목록.includes('system:admin');
};

/**
 * 계정 잠금 확인 메서드
 * @returns {boolean} 계정 잠금 상태
 */
사용자스키마.methods.계정잠금확인 = function() {
  if (!this.계정잠금일시) return false;
  
  // 30분 후 자동 해제
  const 잠금해제시간 = new Date(this.계정잠금일시.getTime() + 30 * 60 * 1000);
  return new Date() < 잠금해제시간;
};

/**
 * 로그인 실패 처리 메서드
 */
사용자스키마.methods.로그인실패처리 = async function() {
  this.로그인실패횟수 += 1;
  
  // 5회 실패 시 계정 잠금
  if (this.로그인실패횟수 >= 5) {
    this.계정잠금일시 = new Date();
  }
  
  await this.save();
};

/**
 * 로그인 성공 처리 메서드
 */
사용자스키마.methods.로그인성공처리 = async function() {
  this.마지막로그인일시 = new Date();
  this.로그인실패횟수 = 0;
  this.계정잠금일시 = undefined;
  await this.save();
};

/**
 * 역할별 기본 권한 반환 메서드
 * @param {string} 역할 - 사용자 역할
 * @returns {Array<string>} 권한 목록
 */
사용자스키마.methods.역할별기본권한가져오기 = function(역할) {
  const 권한맵 = {
    'viewer': [
      'service:read',
      'sla:read',
      'alert:read',
      'report:read'
    ],
    'manager': [
      'service:read',
      'service:write',
      'sla:read',
      'sla:calculate',
      'alert:read',
      'alert:write',
      'report:read',
      'report:generate'
    ],
    'admin': [
      'service:read',
      'service:write',
      'service:delete',
      'sla:read',
      'sla:calculate',
      'alert:read',
      'alert:write',
      'report:read',
      'report:generate',
      'user:read',
      'user:write',
      'system:admin'
    ]
  };
  
  return 권한맵[역할] || 권한맵['viewer'];
};

/**
 * JSON 변환 시 민감한 정보 제외
 */
사용자스키마.methods.toJSON = function() {
  const 사용자객체 = this.toObject();
  delete 사용자객체.비밀번호;
  delete 사용자객체.리프레시토큰;
  delete 사용자객체.__v;
  return 사용자객체;
};

/**
 * 사용자 모델 생성 및 내보내기
 */
const 사용자모델 = mongoose.model('사용자', 사용자스키마);

module.exports = 사용자모델;