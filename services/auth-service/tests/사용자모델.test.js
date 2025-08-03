const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');
const 사용자모델 = require('../src/models/사용자모델');

/**
 * 사용자 모델 단위 테스트
 * 한글 테스트 케이스명 및 주석으로 작성
 */
describe('사용자 모델 테스트', () => {
  // 테스트 전 데이터베이스 연결
  beforeAll(async () => {
    const 테스트DB주소 = process.env.MONGODB_TEST_URI || 'mongodb://localhost:27017/sla_calculator_auth_test';
    await mongoose.connect(테스트DB주소);
  });

  // 각 테스트 후 데이터 정리
  afterEach(async () => {
    await 사용자모델.deleteMany({});
  });

  // 테스트 후 데이터베이스 연결 해제
  afterAll(async () => {
    await mongoose.connection.close();
  });

  describe('사용자 생성 테스트', () => {
    test('유효한 데이터로 사용자를 생성할 수 있어야 한다', async () => {
      // Given: 유효한 사용자 데이터
      const 사용자데이터 = {
        이메일: 'test@example.com',
        이름: '테스트사용자',
        비밀번호: 'Test123!@#',
        역할: 'viewer'
      };

      // When: 사용자 생성
      const 새사용자 = new 사용자모델(사용자데이터);
      const 저장된사용자 = await 새사용자.save();

      // Then: 사용자가 올바르게 생성되어야 함
      expect(저장된사용자._id).toBeDefined();
      expect(저장된사용자.이메일).toBe(사용자데이터.이메일);
      expect(저장된사용자.이름).toBe(사용자데이터.이름);
      expect(저장된사용자.역할).toBe(사용자데이터.역할);
      expect(저장된사용자.활성상태).toBe(true);
      expect(저장된사용자.권한목록).toEqual(['service:read', 'sla:read', 'alert:read', 'report:read']);
    });

    test('비밀번호가 자동으로 해시화되어야 한다', async () => {
      // Given: 평문 비밀번호를 가진 사용자 데이터
      const 원본비밀번호 = 'Test123!@#';
      const 사용자데이터 = {
        이메일: 'test@example.com',
        이름: '테스트사용자',
        비밀번호: 원본비밀번호
      };

      // When: 사용자 생성
      const 새사용자 = new 사용자모델(사용자데이터);
      const 저장된사용자 = await 새사용자.save();

      // Then: 비밀번호가 해시화되어야 함
      expect(저장된사용자.비밀번호).not.toBe(원본비밀번호);
      expect(저장된사용자.비밀번호).toMatch(/^\$2[aby]\$\d+\$/); // bcrypt 해시 패턴
      
      // 원본 비밀번호로 검증이 가능해야 함
      const 비밀번호일치 = await bcrypt.compare(원본비밀번호, 저장된사용자.비밀번호);
      expect(비밀번호일치).toBe(true);
    });

    test('역할별 기본 권한이 올바르게 설정되어야 한다', async () => {
      // Given: 각 역할별 사용자 데이터
      const 관리자데이터 = {
        이메일: 'admin@example.com',
        이름: '관리자',
        비밀번호: 'Test123!@#',
        역할: 'admin'
      };

      const 매니저데이터 = {
        이메일: 'manager@example.com',
        이름: '매니저',
        비밀번호: 'Test123!@#',
        역할: 'manager'
      };

      // When: 각 역할의 사용자 생성
      const 관리자 = await new 사용자모델(관리자데이터).save();
      const 매니저 = await new 사용자모델(매니저데이터).save();

      // Then: 역할별 기본 권한이 올바르게 설정되어야 함
      expect(관리자.권한목록).toContain('system:admin');
      expect(관리자.권한목록).toContain('user:write');
      
      expect(매니저.권한목록).toContain('sla:calculate');
      expect(매니저.권한목록).toContain('report:generate');
      expect(매니저.권한목록).not.toContain('system:admin');
    });

    test('필수 필드가 누락되면 검증 오류가 발생해야 한다', async () => {
      // Given: 필수 필드가 누락된 사용자 데이터
      const 불완전한데이터 = {
        이메일: 'test@example.com'
        // 이름과 비밀번호 누락
      };

      // When & Then: 검증 오류가 발생해야 함
      const 새사용자 = new 사용자모델(불완전한데이터);
      await expect(새사용자.save()).rejects.toThrow();
    });

    test('유효하지 않은 이메일 형식은 거부되어야 한다', async () => {
      // Given: 잘못된 이메일 형식의 사용자 데이터
      const 잘못된데이터 = {
        이메일: 'invalid-email',
        이름: '테스트사용자',
        비밀번호: 'Test123!@#'
      };

      // When & Then: 검증 오류가 발생해야 함
      const 새사용자 = new 사용자모델(잘못된데이터);
      await expect(새사용자.save()).rejects.toThrow();
    });
  });

  describe('사용자 메서드 테스트', () => {
    let 테스트사용자;

    beforeEach(async () => {
      // 각 테스트마다 새로운 사용자 생성
      테스트사용자 = await new 사용자모델({
        이메일: 'test@example.com',
        이름: '테스트사용자',
        비밀번호: 'Test123!@#',
        역할: 'manager'
      }).save();
    });

    test('비밀번호 검증이 올바르게 작동해야 한다', async () => {
      // Given: 저장된 사용자와 비밀번호
      const 올바른비밀번호 = 'Test123!@#';
      const 틀린비밀번호 = 'WrongPassword';

      // When & Then: 비밀번호 검증 결과 확인
      const 올바른결과 = await 테스트사용자.비밀번호검증(올바른비밀번호);
      const 틀린결과 = await 테스트사용자.비밀번호검증(틀린비밀번호);

      expect(올바른결과).toBe(true);
      expect(틀린결과).toBe(false);
    });

    test('권한 확인이 올바르게 작동해야 한다', () => {
      // Given: 매니저 역할의 사용자
      
      // When & Then: 권한 확인 결과
      expect(테스트사용자.권한확인('sla:calculate')).toBe(true);
      expect(테스트사용자.권한확인('report:generate')).toBe(true);
      expect(테스트사용자.권한확인('system:admin')).toBe(false);
    });

    test('계정 잠금 확인이 올바르게 작동해야 한다', () => {
      // Given: 잠금되지 않은 계정
      expect(테스트사용자.계정잠금확인()).toBe(false);

      // When: 계정 잠금 설정
      테스트사용자.계정잠금일시 = new Date();

      // Then: 잠금 상태 확인
      expect(테스트사용자.계정잠금확인()).toBe(true);
    });

    test('로그인 실패 처리가 올바르게 작동해야 한다', async () => {
      // Given: 초기 로그인 실패 횟수 0
      expect(테스트사용자.로그인실패횟수).toBe(0);

      // When: 로그인 실패 처리 (5회)
      for (let i = 0; i < 5; i++) {
        await 테스트사용자.로그인실패처리();
      }

      // Then: 계정이 잠겨야 함
      expect(테스트사용자.로그인실패횟수).toBe(5);
      expect(테스트사용자.계정잠금일시).toBeDefined();
      expect(테스트사용자.계정잠금확인()).toBe(true);
    });

    test('로그인 성공 처리가 올바르게 작동해야 한다', async () => {
      // Given: 로그인 실패 기록이 있는 사용자
      테스트사용자.로그인실패횟수 = 3;
      테스트사용자.계정잠금일시 = new Date();
      await 테스트사용자.save();

      // When: 로그인 성공 처리
      await 테스트사용자.로그인성공처리();

      // Then: 실패 기록이 초기화되어야 함
      expect(테스트사용자.로그인실패횟수).toBe(0);
      expect(테스트사용자.계정잠금일시).toBeUndefined();
      expect(테스트사용자.마지막로그인일시).toBeDefined();
    });

    test('JSON 변환 시 민감한 정보가 제외되어야 한다', () => {
      // When: JSON 변환
      const 사용자JSON = 테스트사용자.toJSON();

      // Then: 민감한 정보가 제외되어야 함
      expect(사용자JSON.비밀번호).toBeUndefined();
      expect(사용자JSON.리프레시토큰).toBeUndefined();
      expect(사용자JSON.__v).toBeUndefined();
      
      // 일반 정보는 포함되어야 함
      expect(사용자JSON.이메일).toBeDefined();
      expect(사용자JSON.이름).toBeDefined();
      expect(사용자JSON.역할).toBeDefined();
    });
  });

  describe('사용자 중복 검증 테스트', () => {
    test('동일한 이메일로 중복 가입이 불가능해야 한다', async () => {
      // Given: 이미 등록된 사용자
      const 기존사용자데이터 = {
        이메일: 'duplicate@example.com',
        이름: '기존사용자',
        비밀번호: 'Test123!@#'
      };
      await new 사용자모델(기존사용자데이터).save();

      // When: 동일한 이메일로 새 사용자 생성 시도
      const 중복사용자데이터 = {
        이메일: 'duplicate@example.com',
        이름: '중복사용자',
        비밀번호: 'Test456!@#'
      };
      const 중복사용자 = new 사용자모델(중복사용자데이터);

      // Then: 중복 오류가 발생해야 함
      await expect(중복사용자.save()).rejects.toThrow();
    });
  });
});