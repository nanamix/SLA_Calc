const mongoose = require('mongoose');
const 인증서비스 = require('../src/services/인증서비스');
const 사용자모델 = require('../src/models/사용자모델');
const 토큰유틸 = require('../src/utils/토큰유틸');

/**
 * 인증 서비스 단위 테스트
 * 한글 테스트 케이스명 및 주석으로 작성
 */
describe('인증 서비스 테스트', () => {
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

  describe('회원가입 테스트', () => {
    test('유효한 데이터로 회원가입이 성공해야 한다', async () => {
      // Given: 유효한 회원가입 데이터
      const 회원가입데이터 = {
        이메일: 'newuser@example.com',
        이름: '신규사용자',
        비밀번호: 'Test123!@#',
        역할: 'viewer'
      };

      // When: 회원가입 실행
      const 결과 = await 인증서비스.회원가입(회원가입데이터);

      // Then: 회원가입이 성공해야 함
      expect(결과.성공).toBe(true);
      expect(결과.메시지).toBe('회원가입이 완료되었습니다');
      expect(결과.데이터.이메일).toBe(회원가입데이터.이메일);
      expect(결과.데이터.이름).toBe(회원가입데이터.이름);
      expect(결과.데이터.역할).toBe(회원가입데이터.역할);
      expect(결과.데이터.비밀번호).toBeUndefined(); // 비밀번호는 반환되지 않아야 함
    });

    test('중복된 이메일로 회원가입 시 오류가 발생해야 한다', async () => {
      // Given: 이미 등록된 사용자
      const 기존사용자데이터 = {
        이메일: 'existing@example.com',
        이름: '기존사용자',
        비밀번호: 'Test123!@#'
      };
      await new 사용자모델(기존사용자데이터).save();

      // When & Then: 동일한 이메일로 회원가입 시도 시 오류 발생
      const 중복회원가입데이터 = {
        이메일: 'existing@example.com',
        이름: '중복사용자',
        비밀번호: 'Test456!@#'
      };

      await expect(인증서비스.회원가입(중복회원가입데이터))
        .rejects.toThrow('이미 등록된 이메일입니다');
    });
  });

  describe('로그인 테스트', () => {
    let 테스트사용자;

    beforeEach(async () => {
      // 각 테스트마다 새로운 사용자 생성
      테스트사용자 = await new 사용자모델({
        이메일: 'testuser@example.com',
        이름: '테스트사용자',
        비밀번호: 'Test123!@#',
        역할: 'manager'
      }).save();
    });

    test('올바른 인증 정보로 로그인이 성공해야 한다', async () => {
      // Given: 올바른 로그인 데이터
      const 로그인데이터 = {
        이메일: 'testuser@example.com',
        비밀번호: 'Test123!@#'
      };

      // When: 로그인 실행
      const 결과 = await 인증서비스.로그인(로그인데이터);

      // Then: 로그인이 성공해야 함
      expect(결과.성공).toBe(true);
      expect(결과.메시지).toBe('로그인이 완료되었습니다');
      expect(결과.데이터.사용자정보.이메일).toBe(로그인데이터.이메일);
      expect(결과.데이터.토큰정보.액세스토큰).toBeDefined();
      expect(결과.데이터.토큰정보.리프레시토큰).toBeDefined();
      expect(결과.데이터.토큰정보.토큰타입).toBe('Bearer');
    });

    test('잘못된 비밀번호로 로그인 시 오류가 발생해야 한다', async () => {
      // Given: 잘못된 비밀번호
      const 잘못된로그인데이터 = {
        이메일: 'testuser@example.com',
        비밀번호: 'WrongPassword'
      };

      // When & Then: 로그인 실패 시 오류 발생
      await expect(인증서비스.로그인(잘못된로그인데이터))
        .rejects.toThrow('이메일 또는 비밀번호가 올바르지 않습니다');
    });

    test('존재하지 않는 사용자로 로그인 시 오류가 발생해야 한다', async () => {
      // Given: 존재하지 않는 사용자 데이터
      const 존재하지않는사용자데이터 = {
        이메일: 'nonexistent@example.com',
        비밀번호: 'Test123!@#'
      };

      // When & Then: 로그인 실패 시 오류 발생
      await expect(인증서비스.로그인(존재하지않는사용자데이터))
        .rejects.toThrow('이메일 또는 비밀번호가 올바르지 않습니다');
    });

    test('비활성화된 계정으로 로그인 시 오류가 발생해야 한다', async () => {
      // Given: 비활성화된 사용자
      테스트사용자.활성상태 = false;
      await 테스트사용자.save();

      const 로그인데이터 = {
        이메일: 'testuser@example.com',
        비밀번호: 'Test123!@#'
      };

      // When & Then: 로그인 실패 시 오류 발생
      await expect(인증서비스.로그인(로그인데이터))
        .rejects.toThrow('비활성화된 계정입니다');
    });

    test('계정 잠금 상태에서 로그인 시 오류가 발생해야 한다', async () => {
      // Given: 잠긴 계정
      테스트사용자.계정잠금일시 = new Date();
      await 테스트사용자.save();

      const 로그인데이터 = {
        이메일: 'testuser@example.com',
        비밀번호: 'Test123!@#'
      };

      // When & Then: 로그인 실패 시 오류 발생
      await expect(인증서비스.로그인(로그인데이터))
        .rejects.toThrow('계정이 잠겨있습니다. 잠시 후 다시 시도해주세요');
    });

    test('로그인 실패 시 실패 횟수가 증가해야 한다', async () => {
      // Given: 잘못된 비밀번호
      const 잘못된로그인데이터 = {
        이메일: 'testuser@example.com',
        비밀번호: 'WrongPassword'
      };

      // When: 로그인 실패
      try {
        await 인증서비스.로그인(잘못된로그인데이터);
      } catch (error) {
        // 오류 무시 (실패 처리 확인이 목적)
      }

      // Then: 실패 횟수가 증가해야 함
      const 업데이트된사용자 = await 사용자모델.findById(테스트사용자._id);
      expect(업데이트된사용자.로그인실패횟수).toBe(1);
    });
  });

  describe('로그아웃 테스트', () => {
    let 테스트사용자;
    let 액세스토큰;

    beforeEach(async () => {
      // 테스트용 사용자 생성 및 로그인
      테스트사용자 = await new 사용자모델({
        이메일: 'testuser@example.com',
        이름: '테스트사용자',
        비밀번호: 'Test123!@#'
      }).save();

      const 로그인결과 = await 인증서비스.로그인({
        이메일: 'testuser@example.com',
        비밀번호: 'Test123!@#'
      });

      액세스토큰 = 로그인결과.데이터.토큰정보.액세스토큰;
    });

    test('로그아웃이 성공해야 한다', async () => {
      // When: 로그아웃 실행
      const 결과 = await 인증서비스.로그아웃(테스트사용자._id, 액세스토큰);

      // Then: 로그아웃이 성공해야 함
      expect(결과.성공).toBe(true);
      expect(결과.메시지).toBe('로그아웃이 완료되었습니다');

      // 리프레시 토큰이 제거되어야 함
      const 업데이트된사용자 = await 사용자모델.findById(테스트사용자._id);
      expect(업데이트된사용자.리프레시토큰).toBeUndefined();
    });
  });

  describe('토큰 갱신 테스트', () => {
    let 테스트사용자;
    let 리프레시토큰;

    beforeEach(async () => {
      // 테스트용 사용자 생성 및 로그인
      테스트사용자 = await new 사용자모델({
        이메일: 'testuser@example.com',
        이름: '테스트사용자',
        비밀번호: 'Test123!@#'
      }).save();

      const 로그인결과 = await 인증서비스.로그인({
        이메일: 'testuser@example.com',
        비밀번호: 'Test123!@#'
      });

      리프레시토큰 = 로그인결과.데이터.토큰정보.리프레시토큰;
    });

    test('유효한 리프레시 토큰으로 토큰 갱신이 성공해야 한다', async () => {
      // When: 토큰 갱신 실행
      const 결과 = await 인증서비스.토큰갱신(리프레시토큰);

      // Then: 토큰 갱신이 성공해야 함
      expect(결과.성공).toBe(true);
      expect(결과.메시지).toBe('토큰이 갱신되었습니다');
      expect(결과.데이터.액세스토큰).toBeDefined();
      expect(결과.데이터.리프레시토큰).toBeDefined();
      expect(결과.데이터.토큰타입).toBe('Bearer');

      // 새 리프레시 토큰이 기존과 달라야 함
      expect(결과.데이터.리프레시토큰).not.toBe(리프레시토큰);
    });

    test('유효하지 않은 리프레시 토큰으로 갱신 시 오류가 발생해야 한다', async () => {
      // Given: 유효하지 않은 리프레시 토큰
      const 유효하지않은토큰 = 'invalid.refresh.token';

      // When & Then: 토큰 갱신 실패 시 오류 발생
      await expect(인증서비스.토큰갱신(유효하지않은토큰))
        .rejects.toThrow('유효하지 않은 리프레시 토큰입니다');
    });
  });

  describe('비밀번호 변경 테스트', () => {
    let 테스트사용자;

    beforeEach(async () => {
      테스트사용자 = await new 사용자모델({
        이메일: 'testuser@example.com',
        이름: '테스트사용자',
        비밀번호: 'Test123!@#'
      }).save();
    });

    test('올바른 현재 비밀번호로 비밀번호 변경이 성공해야 한다', async () => {
      // Given: 비밀번호 변경 데이터
      const 비밀번호변경데이터 = {
        현재비밀번호: 'Test123!@#',
        새비밀번호: 'NewTest456!@#'
      };

      // When: 비밀번호 변경 실행
      const 결과 = await 인증서비스.비밀번호변경(테스트사용자._id, 비밀번호변경데이터);

      // Then: 비밀번호 변경이 성공해야 함
      expect(결과.성공).toBe(true);
      expect(결과.메시지).toBe('비밀번호가 변경되었습니다. 다시 로그인해주세요');

      // 새 비밀번호로 로그인이 가능해야 함
      const 로그인결과 = await 인증서비스.로그인({
        이메일: 'testuser@example.com',
        비밀번호: 'NewTest456!@#'
      });
      expect(로그인결과.성공).toBe(true);
    });

    test('잘못된 현재 비밀번호로 변경 시 오류가 발생해야 한다', async () => {
      // Given: 잘못된 현재 비밀번호
      const 잘못된비밀번호변경데이터 = {
        현재비밀번호: 'WrongPassword',
        새비밀번호: 'NewTest456!@#'
      };

      // When & Then: 비밀번호 변경 실패 시 오류 발생
      await expect(인증서비스.비밀번호변경(테스트사용자._id, 잘못된비밀번호변경데이터))
        .rejects.toThrow('현재 비밀번호가 올바르지 않습니다');
    });

    test('현재 비밀번호와 동일한 새 비밀번호로 변경 시 오류가 발생해야 한다', async () => {
      // Given: 현재와 동일한 새 비밀번호
      const 동일한비밀번호변경데이터 = {
        현재비밀번호: 'Test123!@#',
        새비밀번호: 'Test123!@#'
      };

      // When & Then: 비밀번호 변경 실패 시 오류 발생
      await expect(인증서비스.비밀번호변경(테스트사용자._id, 동일한비밀번호변경데이터))
        .rejects.toThrow('새 비밀번호는 현재 비밀번호와 달라야 합니다');
    });
  });

  describe('프로필 관리 테스트', () => {
    let 테스트사용자;

    beforeEach(async () => {
      테스트사용자 = await new 사용자모델({
        이메일: 'testuser@example.com',
        이름: '테스트사용자',
        비밀번호: 'Test123!@#'
      }).save();
    });

    test('프로필 조회가 성공해야 한다', async () => {
      // When: 프로필 조회 실행
      const 결과 = await 인증서비스.프로필조회(테스트사용자._id);

      // Then: 프로필 조회가 성공해야 함
      expect(결과.성공).toBe(true);
      expect(결과.데이터.이메일).toBe('testuser@example.com');
      expect(결과.데이터.이름).toBe('테스트사용자');
      expect(결과.데이터.비밀번호).toBeUndefined(); // 비밀번호는 반환되지 않아야 함
    });

    test('프로필 수정이 성공해야 한다', async () => {
      // Given: 수정할 프로필 데이터
      const 수정데이터 = {
        이름: '수정된사용자'
      };

      // When: 프로필 수정 실행
      const 결과 = await 인증서비스.프로필수정(테스트사용자._id, 수정데이터);

      // Then: 프로필 수정이 성공해야 함
      expect(결과.성공).toBe(true);
      expect(결과.메시지).toBe('프로필이 수정되었습니다');
      expect(결과.데이터.이름).toBe('수정된사용자');
    });

    test('존재하지 않는 사용자 프로필 조회 시 오류가 발생해야 한다', async () => {
      // Given: 존재하지 않는 사용자 ID
      const 존재하지않는아이디 = new mongoose.Types.ObjectId();

      // When & Then: 프로필 조회 실패 시 오류 발생
      await expect(인증서비스.프로필조회(존재하지않는아이디))
        .rejects.toThrow('사용자를 찾을 수 없습니다');
    });
  });
});