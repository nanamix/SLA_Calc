const 사용자모델 = require('../models/사용자모델');
const 토큰유틸 = require('../utils/토큰유틸');

/**
 * 인증 관련 비즈니스 로직을 처리하는 서비스 클래스
 */
class 인증서비스 {
  
  /**
   * 사용자 회원가입
   * @param {Object} 회원가입데이터 - 회원가입 정보
   * @returns {Promise<Object>} 생성된 사용자 정보
   */
  async 회원가입(회원가입데이터) {
    try {
      const { 이메일, 이름, 비밀번호, 역할 = 'viewer' } = 회원가입데이터;

      // 이메일 중복 확인
      const 기존사용자 = await 사용자모델.findOne({ 이메일 });
      if (기존사용자) {
        throw new Error('이미 등록된 이메일입니다');
      }

      // 새 사용자 생성
      const 새사용자 = new 사용자모델({
        이메일,
        이름,
        비밀번호,
        역할
      });

      await 새사용자.save();

      // 비밀번호 제외하고 반환
      const 사용자정보 = 새사용자.toJSON();
      
      console.log(`✅ 새 사용자 등록: ${이메일} (${역할})`);
      
      return {
        성공: true,
        메시지: '회원가입이 완료되었습니다',
        데이터: 사용자정보
      };

    } catch (error) {
      console.error('회원가입 오류:', error.message);
      throw new Error(error.message || '회원가입 처리 중 오류가 발생했습니다');
    }
  }

  /**
   * 사용자 로그인
   * @param {Object} 로그인데이터 - 로그인 정보
   * @returns {Promise<Object>} 인증 토큰 및 사용자 정보
   */
  async 로그인(로그인데이터) {
    try {
      const { 이메일, 비밀번호 } = 로그인데이터;

      // 사용자 조회 (비밀번호 포함)
      const 사용자 = await 사용자모델.findOne({ 이메일 }).select('+비밀번호');
      if (!사용자) {
        throw new Error('이메일 또는 비밀번호가 올바르지 않습니다');
      }

      // 계정 활성 상태 확인
      if (!사용자.활성상태) {
        throw new Error('비활성화된 계정입니다');
      }

      // 계정 잠금 상태 확인
      if (사용자.계정잠금확인()) {
        throw new Error('계정이 잠겨있습니다. 잠시 후 다시 시도해주세요');
      }

      // 비밀번호 검증
      const 비밀번호일치 = await 사용자.비밀번호검증(비밀번호);
      if (!비밀번호일치) {
        // 로그인 실패 처리
        await 사용자.로그인실패처리();
        throw new Error('이메일 또는 비밀번호가 올바르지 않습니다');
      }

      // 로그인 성공 처리
      await 사용자.로그인성공처리();

      // 토큰 생성
      const 액세스토큰 = 토큰유틸.액세스토큰생성(사용자);
      const 리프레시토큰 = 토큰유틸.리프레시토큰생성(사용자._id);

      // 리프레시 토큰을 데이터베이스에 저장
      사용자.리프레시토큰 = 리프레시토큰;
      await 사용자.save();

      console.log(`✅ 사용자 로그인: ${이메일}`);

      return {
        성공: true,
        메시지: '로그인이 완료되었습니다',
        데이터: {
          사용자정보: 사용자.toJSON(),
          토큰정보: {
            액세스토큰,
            리프레시토큰,
            토큰타입: 'Bearer',
            만료시간: 토큰유틸.JWT_EXPIRES_IN
          }
        }
      };

    } catch (error) {
      console.error('로그인 오류:', error.message);
      throw new Error(error.message || '로그인 처리 중 오류가 발생했습니다');
    }
  }

  /**
   * 사용자 로그아웃
   * @param {string} 사용자아이디 - 로그아웃할 사용자 ID
   * @param {string} 액세스토큰 - 현재 액세스 토큰
   * @returns {Promise<Object>} 로그아웃 결과
   */
  async 로그아웃(사용자아이디, 액세스토큰) {
    try {
      // 사용자의 리프레시 토큰 제거
      await 사용자모델.findByIdAndUpdate(사용자아이디, {
        $unset: { 리프레시토큰: 1 }
      });

      // 액세스 토큰을 블랙리스트에 추가
      await 토큰유틸.블랙리스트추가(액세스토큰);

      console.log(`✅ 사용자 로그아웃: ${사용자아이디}`);

      return {
        성공: true,
        메시지: '로그아웃이 완료되었습니다'
      };

    } catch (error) {
      console.error('로그아웃 오류:', error.message);
      throw new Error('로그아웃 처리 중 오류가 발생했습니다');
    }
  }

  /**
   * 토큰 갱신
   * @param {string} 리프레시토큰 - 리프레시 토큰
   * @returns {Promise<Object>} 새로운 토큰 정보
   */
  async 토큰갱신(리프레시토큰) {
    try {
      // 리프레시 토큰 검증
      const 토큰정보 = 토큰유틸.토큰검증(리프레시토큰);
      if (!토큰정보 || 토큰정보.토큰타입 !== 'refresh') {
        throw new Error('유효하지 않은 리프레시 토큰입니다');
      }

      // 사용자 조회 및 리프레시 토큰 일치 확인
      const 사용자 = await 사용자모델.findById(토큰정보.사용자아이디).select('+리프레시토큰');
      if (!사용자 || 사용자.리프레시토큰 !== 리프레시토큰) {
        throw new Error('유효하지 않은 리프레시 토큰입니다');
      }

      // 계정 상태 확인
      if (!사용자.활성상태) {
        throw new Error('비활성화된 계정입니다');
      }

      if (사용자.계정잠금확인()) {
        throw new Error('계정이 잠겨있습니다');
      }

      // 새로운 토큰 생성
      const 새토큰정보 = 토큰유틸.토큰갱신(리프레시토큰, 사용자);
      if (!새토큰정보) {
        throw new Error('토큰 갱신에 실패했습니다');
      }

      // 새 리프레시 토큰을 데이터베이스에 저장
      사용자.리프레시토큰 = 새토큰정보.리프레시토큰;
      await 사용자.save();

      console.log(`✅ 토큰 갱신: ${사용자.이메일}`);

      return {
        성공: true,
        메시지: '토큰이 갱신되었습니다',
        데이터: 새토큰정보
      };

    } catch (error) {
      console.error('토큰 갱신 오류:', error.message);
      throw new Error(error.message || '토큰 갱신 중 오류가 발생했습니다');
    }
  }

  /**
   * 비밀번호 변경
   * @param {string} 사용자아이디 - 사용자 ID
   * @param {Object} 비밀번호데이터 - 비밀번호 변경 정보
   * @returns {Promise<Object>} 변경 결과
   */
  async 비밀번호변경(사용자아이디, 비밀번호데이터) {
    try {
      const { 현재비밀번호, 새비밀번호 } = 비밀번호데이터;

      // 사용자 조회 (비밀번호 포함)
      const 사용자 = await 사용자모델.findById(사용자아이디).select('+비밀번호');
      if (!사용자) {
        throw new Error('사용자를 찾을 수 없습니다');
      }

      // 현재 비밀번호 확인
      const 비밀번호일치 = await 사용자.비밀번호검증(현재비밀번호);
      if (!비밀번호일치) {
        throw new Error('현재 비밀번호가 올바르지 않습니다');
      }

      // 새 비밀번호와 현재 비밀번호가 같은지 확인
      const 동일비밀번호 = await 사용자.비밀번호검증(새비밀번호);
      if (동일비밀번호) {
        throw new Error('새 비밀번호는 현재 비밀번호와 달라야 합니다');
      }

      // 비밀번호 변경
      사용자.비밀번호 = 새비밀번호;
      await 사용자.save();

      // 모든 리프레시 토큰 무효화 (보안상 다시 로그인 필요)
      사용자.리프레시토큰 = undefined;
      await 사용자.save();

      console.log(`✅ 비밀번호 변경: ${사용자.이메일}`);

      return {
        성공: true,
        메시지: '비밀번호가 변경되었습니다. 다시 로그인해주세요'
      };

    } catch (error) {
      console.error('비밀번호 변경 오류:', error.message);
      throw new Error(error.message || '비밀번호 변경 중 오류가 발생했습니다');
    }
  }

  /**
   * 사용자 프로필 조회
   * @param {string} 사용자아이디 - 사용자 ID
   * @returns {Promise<Object>} 사용자 프로필 정보
   */
  async 프로필조회(사용자아이디) {
    try {
      const 사용자 = await 사용자모델.findById(사용자아이디);
      if (!사용자) {
        throw new Error('사용자를 찾을 수 없습니다');
      }

      return {
        성공: true,
        데이터: 사용자.toJSON()
      };

    } catch (error) {
      console.error('프로필 조회 오류:', error.message);
      throw new Error(error.message || '프로필 조회 중 오류가 발생했습니다');
    }
  }

  /**
   * 사용자 프로필 수정
   * @param {string} 사용자아이디 - 사용자 ID
   * @param {Object} 수정데이터 - 수정할 정보
   * @returns {Promise<Object>} 수정된 사용자 정보
   */
  async 프로필수정(사용자아이디, 수정데이터) {
    try {
      const { 이름 } = 수정데이터;

      const 사용자 = await 사용자모델.findByIdAndUpdate(
        사용자아이디,
        { 이름, 수정일시: new Date() },
        { new: true, runValidators: true }
      );

      if (!사용자) {
        throw new Error('사용자를 찾을 수 없습니다');
      }

      console.log(`✅ 프로필 수정: ${사용자.이메일}`);

      return {
        성공: true,
        메시지: '프로필이 수정되었습니다',
        데이터: 사용자.toJSON()
      };

    } catch (error) {
      console.error('프로필 수정 오류:', error.message);
      throw new Error(error.message || '프로필 수정 중 오류가 발생했습니다');
    }
  }
}

// 싱글톤 인스턴스 생성
const 인증서비스인스턴스 = new 인증서비스();

module.exports = 인증서비스인스턴스;