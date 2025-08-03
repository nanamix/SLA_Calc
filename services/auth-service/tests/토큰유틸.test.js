const 토큰유틸 = require('../src/utils/토큰유틸');
const jwt = require('jsonwebtoken');

/**
 * 토큰 유틸리티 단위 테스트
 * 한글 테스트 케이스명 및 주석으로 작성
 */
describe('토큰 유틸리티 테스트', () => {
  // 테스트용 사용자 데이터
  const 테스트사용자정보 = {
    _id: '507f1f77bcf86cd799439011',
    이메일: 'test@example.com',
    이름: '테스트사용자',
    역할: 'manager',
    권한목록: ['service:read', 'sla:calculate', 'report:generate']
  };

  describe('액세스 토큰 생성 테스트', () => {
    test('유효한 사용자 정보로 액세스 토큰을 생성할 수 있어야 한다', () => {
      // When: 액세스 토큰 생성
      const 토큰 = 토큰유틸.액세스토큰생성(테스트사용자정보);

      // Then: 토큰이 생성되어야 함
      expect(토큰).toBeDefined();
      expect(typeof 토큰).toBe('string');
      expect(토큰.split('.')).toHaveLength(3); // JWT 형식 확인

      // 토큰 내용 검증
      const 디코딩결과 = jwt.decode(토큰);
      expect(디코딩결과.사용자아이디).toBe(테스트사용자정보._id);
      expect(디코딩결과.이메일).toBe(테스트사용자정보.이메일);
      expect(디코딩결과.이름).toBe(테스트사용자정보.이름);
      expect(디코딩결과.역할).toBe(테스트사용자정보.역할);
      expect(디코딩결과.권한목록).toEqual(테스트사용자정보.권한목록);
      expect(디코딩결과.토큰타입).toBe('access');
    });

    test('생성된 액세스 토큰에 만료 시간이 설정되어야 한다', () => {
      // When: 액세스 토큰 생성
      const 토큰 = 토큰유틸.액세스토큰생성(테스트사용자정보);

      // Then: 만료 시간이 설정되어야 함
      const 디코딩결과 = jwt.decode(토큰);
      expect(디코딩결과.exp).toBeDefined();
      expect(디코딩결과.iat).toBeDefined();
      expect(디코딩결과.exp).toBeGreaterThan(디코딩결과.iat);
    });
  });

  describe('리프레시 토큰 생성 테스트', () => {
    test('사용자 ID로 리프레시 토큰을 생성할 수 있어야 한다', () => {
      // When: 리프레시 토큰 생성
      const 토큰 = 토큰유틸.리프레시토큰생성(테스트사용자정보._id);

      // Then: 토큰이 생성되어야 함
      expect(토큰).toBeDefined();
      expect(typeof 토큰).toBe('string');
      expect(토큰.split('.')).toHaveLength(3); // JWT 형식 확인

      // 토큰 내용 검증
      const 디코딩결과 = jwt.decode(토큰);
      expect(디코딩결과.사용자아이디).toBe(테스트사용자정보._id);
      expect(디코딩결과.토큰타입).toBe('refresh');
      expect(디코딩결과.무작위값).toBeDefined(); // 고유성 보장을 위한 무작위값
    });

    test('동일한 사용자 ID로 생성된 리프레시 토큰들은 서로 달라야 한다', () => {
      // When: 동일한 사용자 ID로 두 개의 리프레시 토큰 생성
      const 토큰1 = 토큰유틸.리프레시토큰생성(테스트사용자정보._id);
      const 토큰2 = 토큰유틸.리프레시토큰생성(테스트사용자정보._id);

      // Then: 토큰들이 달라야 함
      expect(토큰1).not.toBe(토큰2);

      // 무작위값이 달라야 함
      const 디코딩결과1 = jwt.decode(토큰1);
      const 디코딩결과2 = jwt.decode(토큰2);
      expect(디코딩결과1.무작위값).not.toBe(디코딩결과2.무작위값);
    });
  });

  describe('토큰 검증 테스트', () => {
    let 유효한액세스토큰;
    let 유효한리프레시토큰;

    beforeEach(() => {
      유효한액세스토큰 = 토큰유틸.액세스토큰생성(테스트사용자정보);
      유효한리프레시토큰 = 토큰유틸.리프레시토큰생성(테스트사용자정보._id);
    });

    test('유효한 액세스 토큰을 검증할 수 있어야 한다', () => {
      // When: 토큰 검증
      const 검증결과 = 토큰유틸.토큰검증(유효한액세스토큰);

      // Then: 검증이 성공해야 함
      expect(검증결과).toBeDefined();
      expect(검증결과.사용자아이디).toBe(테스트사용자정보._id);
      expect(검증결과.토큰타입).toBe('access');
    });

    test('유효한 리프레시 토큰을 검증할 수 있어야 한다', () => {
      // When: 토큰 검증
      const 검증결과 = 토큰유틸.토큰검증(유효한리프레시토큰);

      // Then: 검증이 성공해야 함
      expect(검증결과).toBeDefined();
      expect(검증결과.사용자아이디).toBe(테스트사용자정보._id);
      expect(검증결과.토큰타입).toBe('refresh');
    });

    test('유효하지 않은 토큰 검증 시 null을 반환해야 한다', () => {
      // Given: 유효하지 않은 토큰들
      const 유효하지않은토큰들 = [
        'invalid.token.here',
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature',
        '',
        null,
        undefined
      ];

      유효하지않은토큰들.forEach(토큰 => {
        // When: 토큰 검증
        const 검증결과 = 토큰유틸.토큰검증(토큰);

        // Then: null을 반환해야 함
        expect(검증결과).toBeNull();
      });
    });

    test('만료된 토큰 검증 시 null을 반환해야 한다', () => {
      // Given: 만료된 토큰 생성 (과거 시간으로 설정)
      const 만료된토큰 = jwt.sign(
        {
          사용자아이디: 테스트사용자정보._id,
          토큰타입: 'access',
          exp: Math.floor(Date.now() / 1000) - 3600 // 1시간 전 만료
        },
        process.env.JWT_SECRET || 'default-secret-key'
      );

      // When: 토큰 검증
      const 검증결과 = 토큰유틸.토큰검증(만료된토큰);

      // Then: null을 반환해야 함
      expect(검증결과).toBeNull();
    });
  });

  describe('토큰 만료 시간 확인 테스트', () => {
    test('유효한 토큰의 만료 시간을 확인할 수 있어야 한다', () => {
      // Given: 유효한 토큰
      const 토큰 = 토큰유틸.액세스토큰생성(테스트사용자정보);

      // When: 만료 시간 확인
      const 만료정보 = 토큰유틸.토큰만료시간확인(토큰);

      // Then: 만료 정보가 올바르게 반환되어야 함
      expect(만료정보.유효함).toBe(true);
      expect(만료정보.만료시간).toBeInstanceOf(Date);
      expect(만료정보.남은시간초).toBeGreaterThan(0);
      expect(typeof 만료정보.곧만료됨).toBe('boolean');
    });

    test('만료된 토큰의 만료 시간 확인 시 유효하지 않음을 반환해야 한다', () => {
      // Given: 만료된 토큰
      const 만료된토큰 = jwt.sign(
        {
          사용자아이디: 테스트사용자정보._id,
          exp: Math.floor(Date.now() / 1000) - 3600 // 1시간 전 만료
        },
        process.env.JWT_SECRET || 'default-secret-key'
      );

      // When: 만료 시간 확인
      const 만료정보 = 토큰유틸.토큰만료시간확인(만료된토큰);

      // Then: 유효하지 않음을 반환해야 함
      expect(만료정보.유효함).toBe(false);
      expect(만료정보.남은시간초).toBe(0);
    });
  });

  describe('사용자 정보 추출 테스트', () => {
    test('액세스 토큰에서 사용자 정보를 추출할 수 있어야 한다', () => {
      // Given: 유효한 액세스 토큰
      const 토큰 = 토큰유틸.액세스토큰생성(테스트사용자정보);

      // When: 사용자 정보 추출
      const 사용자정보 = 토큰유틸.사용자정보추출(토큰);

      // Then: 사용자 정보가 올바르게 추출되어야 함
      expect(사용자정보).toBeDefined();
      expect(사용자정보.사용자아이디).toBe(테스트사용자정보._id);
      expect(사용자정보.이메일).toBe(테스트사용자정보.이메일);
      expect(사용자정보.이름).toBe(테스트사용자정보.이름);
      expect(사용자정보.역할).toBe(테스트사용자정보.역할);
      expect(사용자정보.권한목록).toEqual(테스트사용자정보.권한목록);
    });

    test('유효하지 않은 토큰에서 사용자 정보 추출 시 null을 반환해야 한다', () => {
      // Given: 유효하지 않은 토큰
      const 유효하지않은토큰 = 'invalid.token.here';

      // When: 사용자 정보 추출
      const 사용자정보 = 토큰유틸.사용자정보추출(유효하지않은토큰);

      // Then: null을 반환해야 함
      expect(사용자정보).toBeNull();
    });
  });

  describe('토큰 갱신 테스트', () => {
    test('유효한 리프레시 토큰으로 새 토큰을 생성할 수 있어야 한다', () => {
      // Given: 유효한 리프레시 토큰
      const 리프레시토큰 = 토큰유틸.리프레시토큰생성(테스트사용자정보._id);

      // When: 토큰 갱신
      const 새토큰정보 = 토큰유틸.토큰갱신(리프레시토큰, 테스트사용자정보);

      // Then: 새 토큰이 생성되어야 함
      expect(새토큰정보).toBeDefined();
      expect(새토큰정보.액세스토큰).toBeDefined();
      expect(새토큰정보.리프레시토큰).toBeDefined();
      expect(새토큰정보.토큰타입).toBe('Bearer');
      expect(새토큰정보.만료시간).toBeDefined();

      // 새 리프레시 토큰은 기존과 달라야 함
      expect(새토큰정보.리프레시토큰).not.toBe(리프레시토큰);
    });

    test('액세스 토큰으로 갱신 시도 시 null을 반환해야 한다', () => {
      // Given: 액세스 토큰 (리프레시 토큰이 아님)
      const 액세스토큰 = 토큰유틸.액세스토큰생성(테스트사용자정보);

      // When: 토큰 갱신 시도
      const 새토큰정보 = 토큰유틸.토큰갱신(액세스토큰, 테스트사용자정보);

      // Then: null을 반환해야 함
      expect(새토큰정보).toBeNull();
    });

    test('사용자 ID가 일치하지 않는 경우 null을 반환해야 한다', () => {
      // Given: 다른 사용자 ID로 생성된 리프레시 토큰
      const 다른사용자ID = '507f1f77bcf86cd799439012';
      const 리프레시토큰 = 토큰유틸.리프레시토큰생성(다른사용자ID);

      // When: 토큰 갱신 시도
      const 새토큰정보 = 토큰유틸.토큰갱신(리프레시토큰, 테스트사용자정보);

      // Then: null을 반환해야 함
      expect(새토큰정보).toBeNull();
    });
  });

  describe('헤더에서 토큰 추출 테스트', () => {
    test('올바른 Authorization 헤더에서 토큰을 추출할 수 있어야 한다', () => {
      // Given: 올바른 Authorization 헤더
      const 테스트토큰 = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token';
      const 인증헤더 = `Bearer ${테스트토큰}`;

      // When: 토큰 추출
      const 추출된토큰 = 토큰유틸.헤더에서토큰추출(인증헤더);

      // Then: 토큰이 올바르게 추출되어야 함
      expect(추출된토큰).toBe(테스트토큰);
    });

    test('잘못된 형식의 Authorization 헤더에서는 null을 반환해야 한다', () => {
      // Given: 잘못된 형식의 헤더들
      const 잘못된헤더들 = [
        'Basic dGVzdDp0ZXN0', // Basic 인증
        'Bearer', // 토큰 없음
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token', // Bearer 없음
        '', // 빈 문자열
        null, // null
        undefined // undefined
      ];

      잘못된헤더들.forEach(헤더 => {
        // When: 토큰 추출 시도
        const 추출된토큰 = 토큰유틸.헤더에서토큰추출(헤더);

        // Then: null을 반환해야 함
        expect(추출된토큰).toBeNull();
      });
    });
  });
});