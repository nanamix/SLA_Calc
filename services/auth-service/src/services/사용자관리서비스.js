const 사용자모델 = require('../models/사용자모델');

/**
 * 사용자 관리 관련 비즈니스 로직을 처리하는 서비스 클래스
 * 관리자 권한이 필요한 사용자 관리 기능을 제공
 */
class 사용자관리서비스 {

  /**
   * 전체 사용자 목록 조회
   * @param {Object} 조회옵션 - 페이징 및 필터링 옵션
   * @returns {Promise<Object>} 사용자 목록 및 페이징 정보
   */
  async 사용자목록조회(조회옵션 = {}) {
    try {
      const {
        페이지 = 1,
        페이지크기 = 10,
        검색어 = '',
        역할필터 = '',
        활성상태필터 = ''
      } = 조회옵션;

      // 검색 조건 구성
      const 검색조건 = {};
      
      if (검색어) {
        검색조건.$or = [
          { 이름: { $regex: 검색어, $options: 'i' } },
          { 이메일: { $regex: 검색어, $options: 'i' } }
        ];
      }
      
      if (역할필터) {
        검색조건.역할 = 역할필터;
      }
      
      if (활성상태필터 !== '') {
        검색조건.활성상태 = 활성상태필터 === 'true';
      }

      // 페이징 계산
      const 건너뛸개수 = (페이지 - 1) * 페이지크기;

      // 사용자 목록 조회
      const [사용자목록, 전체개수] = await Promise.all([
        사용자모델
          .find(검색조건)
          .sort({ 생성일시: -1 })
          .skip(건너뛸개수)
          .limit(페이지크기)
          .lean(),
        사용자모델.countDocuments(검색조건)
      ]);

      // 페이징 정보 계산
      const 전체페이지수 = Math.ceil(전체개수 / 페이지크기);

      return {
        성공: true,
        데이터: {
          사용자목록,
          페이징정보: {
            현재페이지: 페이지,
            페이지크기,
            전체개수,
            전체페이지수,
            이전페이지있음: 페이지 > 1,
            다음페이지있음: 페이지 < 전체페이지수
          }
        }
      };

    } catch (error) {
      console.error('사용자 목록 조회 오류:', error.message);
      throw new Error('사용자 목록 조회 중 오류가 발생했습니다');
    }
  }

  /**
   * 특정 사용자 상세 정보 조회
   * @param {string} 사용자아이디 - 조회할 사용자 ID
   * @returns {Promise<Object>} 사용자 상세 정보
   */
  async 사용자상세조회(사용자아이디) {
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
      console.error('사용자 상세 조회 오류:', error.message);
      throw new Error(error.message || '사용자 상세 조회 중 오류가 발생했습니다');
    }
  }

  /**
   * 새 사용자 생성 (관리자용)
   * @param {Object} 사용자데이터 - 생성할 사용자 정보
   * @returns {Promise<Object>} 생성된 사용자 정보
   */
  async 사용자생성(사용자데이터) {
    try {
      const { 이메일, 이름, 비밀번호, 역할, 권한목록 } = 사용자데이터;

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
        역할,
        권한목록: 권한목록 || undefined // undefined면 역할별 기본 권한 사용
      });

      await 새사용자.save();

      console.log(`✅ 관리자가 새 사용자 생성: ${이메일} (${역할})`);

      return {
        성공: true,
        메시지: '사용자가 생성되었습니다',
        데이터: 새사용자.toJSON()
      };

    } catch (error) {
      console.error('사용자 생성 오류:', error.message);
      throw new Error(error.message || '사용자 생성 중 오류가 발생했습니다');
    }
  }

  /**
   * 사용자 정보 수정 (관리자용)
   * @param {string} 사용자아이디 - 수정할 사용자 ID
   * @param {Object} 수정데이터 - 수정할 정보
   * @returns {Promise<Object>} 수정된 사용자 정보
   */
  async 사용자수정(사용자아이디, 수정데이터) {
    try {
      const { 이름, 역할, 권한목록, 활성상태 } = 수정데이터;

      // 수정할 데이터 구성
      const 업데이트데이터 = {
        수정일시: new Date()
      };

      if (이름 !== undefined) 업데이트데이터.이름 = 이름;
      if (역할 !== undefined) 업데이트데이터.역할 = 역할;
      if (권한목록 !== undefined) 업데이트데이터.권한목록 = 권한목록;
      if (활성상태 !== undefined) 업데이트데이터.활성상태 = 활성상태;

      const 수정된사용자 = await 사용자모델.findByIdAndUpdate(
        사용자아이디,
        업데이트데이터,
        { new: true, runValidators: true }
      );

      if (!수정된사용자) {
        throw new Error('사용자를 찾을 수 없습니다');
      }

      console.log(`✅ 사용자 정보 수정: ${수정된사용자.이메일}`);

      return {
        성공: true,
        메시지: '사용자 정보가 수정되었습니다',
        데이터: 수정된사용자.toJSON()
      };

    } catch (error) {
      console.error('사용자 수정 오류:', error.message);
      throw new Error(error.message || '사용자 수정 중 오류가 발생했습니다');
    }
  }

  /**
   * 사용자 삭제 (관리자용)
   * @param {string} 사용자아이디 - 삭제할 사용자 ID
   * @returns {Promise<Object>} 삭제 결과
   */
  async 사용자삭제(사용자아이디) {
    try {
      const 삭제된사용자 = await 사용자모델.findByIdAndDelete(사용자아이디);
      
      if (!삭제된사용자) {
        throw new Error('사용자를 찾을 수 없습니다');
      }

      console.log(`✅ 사용자 삭제: ${삭제된사용자.이메일}`);

      return {
        성공: true,
        메시지: '사용자가 삭제되었습니다'
      };

    } catch (error) {
      console.error('사용자 삭제 오류:', error.message);
      throw new Error(error.message || '사용자 삭제 중 오류가 발생했습니다');
    }
  }

  /**
   * 사용자 계정 활성화/비활성화
   * @param {string} 사용자아이디 - 대상 사용자 ID
   * @param {boolean} 활성상태 - 설정할 활성 상태
   * @returns {Promise<Object>} 변경 결과
   */
  async 계정상태변경(사용자아이디, 활성상태) {
    try {
      const 수정된사용자 = await 사용자모델.findByIdAndUpdate(
        사용자아이디,
        { 활성상태, 수정일시: new Date() },
        { new: true }
      );

      if (!수정된사용자) {
        throw new Error('사용자를 찾을 수 없습니다');
      }

      const 상태메시지 = 활성상태 ? '활성화' : '비활성화';
      console.log(`✅ 계정 ${상태메시지}: ${수정된사용자.이메일}`);

      return {
        성공: true,
        메시지: `계정이 ${상태메시지}되었습니다`,
        데이터: 수정된사용자.toJSON()
      };

    } catch (error) {
      console.error('계정 상태 변경 오류:', error.message);
      throw new Error(error.message || '계정 상태 변경 중 오류가 발생했습니다');
    }
  }

  /**
   * 사용자 계정 잠금 해제
   * @param {string} 사용자아이디 - 잠금 해제할 사용자 ID
   * @returns {Promise<Object>} 해제 결과
   */
  async 계정잠금해제(사용자아이디) {
    try {
      const 수정된사용자 = await 사용자모델.findByIdAndUpdate(
        사용자아이디,
        {
          로그인실패횟수: 0,
          $unset: { 계정잠금일시: 1 },
          수정일시: new Date()
        },
        { new: true }
      );

      if (!수정된사용자) {
        throw new Error('사용자를 찾을 수 없습니다');
      }

      console.log(`✅ 계정 잠금 해제: ${수정된사용자.이메일}`);

      return {
        성공: true,
        메시지: '계정 잠금이 해제되었습니다',
        데이터: 수정된사용자.toJSON()
      };

    } catch (error) {
      console.error('계정 잠금 해제 오류:', error.message);
      throw new Error(error.message || '계정 잠금 해제 중 오류가 발생했습니다');
    }
  }

  /**
   * 사용자 비밀번호 재설정 (관리자용)
   * @param {string} 사용자아이디 - 대상 사용자 ID
   * @param {string} 새비밀번호 - 새 비밀번호
   * @returns {Promise<Object>} 재설정 결과
   */
  async 비밀번호재설정(사용자아이디, 새비밀번호) {
    try {
      const 사용자 = await 사용자모델.findById(사용자아이디);
      
      if (!사용자) {
        throw new Error('사용자를 찾을 수 없습니다');
      }

      // 비밀번호 변경 (pre save 미들웨어에서 자동 해시화)
      사용자.비밀번호 = 새비밀번호;
      사용자.리프레시토큰 = undefined; // 모든 세션 무효화
      await 사용자.save();

      console.log(`✅ 관리자가 비밀번호 재설정: ${사용자.이메일}`);

      return {
        성공: true,
        메시지: '비밀번호가 재설정되었습니다'
      };

    } catch (error) {
      console.error('비밀번호 재설정 오류:', error.message);
      throw new Error(error.message || '비밀번호 재설정 중 오류가 발생했습니다');
    }
  }

  /**
   * 사용자 통계 정보 조회
   * @returns {Promise<Object>} 사용자 통계 정보
   */
  async 사용자통계조회() {
    try {
      const [
        전체사용자수,
        활성사용자수,
        역할별통계,
        최근가입자수
      ] = await Promise.all([
        사용자모델.countDocuments(),
        사용자모델.countDocuments({ 활성상태: true }),
        사용자모델.aggregate([
          { $group: { _id: '$역할', 개수: { $sum: 1 } } }
        ]),
        사용자모델.countDocuments({
          생성일시: { $gte: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) }
        })
      ]);

      // 역할별 통계를 객체로 변환
      const 역할별개수 = {};
      역할별통계.forEach(항목 => {
        역할별개수[항목._id] = 항목.개수;
      });

      return {
        성공: true,
        데이터: {
          전체사용자수,
          활성사용자수,
          비활성사용자수: 전체사용자수 - 활성사용자수,
          역할별개수,
          최근가입자수
        }
      };

    } catch (error) {
      console.error('사용자 통계 조회 오류:', error.message);
      throw new Error('사용자 통계 조회 중 오류가 발생했습니다');
    }
  }
}

// 싱글톤 인스턴스 생성
const 사용자관리서비스인스턴스 = new 사용자관리서비스();

module.exports = 사용자관리서비스인스턴스;