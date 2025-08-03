const mongoose = require('mongoose');

/**
 * MongoDB 데이터베이스 연결 설정
 */
class 데이터베이스설정 {
  constructor() {
    this.연결상태 = false;
    this.재연결시도횟수 = 0;
    this.최대재연결시도 = 5;
  }

  /**
   * 데이터베이스 연결
   * @param {string} 연결URI - MongoDB 연결 URI (선택사항)
   * @returns {Promise<void>}
   */
  async 연결(연결URI = null) {
    try {
      const URI = 연결URI || process.env.MONGODB_URI || 'mongodb://localhost:27017/sla_calculator_auth';
      
      // MongoDB 연결 옵션 설정
      const 연결옵션 = {
        useNewUrlParser: true,
        useUnifiedTopology: true,
        maxPoolSize: 10,        // 최대 연결 풀 크기
        serverSelectionTimeoutMS: 5000, // 서버 선택 타임아웃
        socketTimeoutMS: 45000, // 소켓 타임아웃
        bufferMaxEntries: 0,    // 버퍼 비활성화
        bufferCommands: false   // 명령 버퍼링 비활성화
      };

      console.log(`데이터베이스 연결 시도: ${URI}`);
      await mongoose.connect(URI, 연결옵션);
      
      this.연결상태 = true;
      this.재연결시도횟수 = 0;
      console.log('✅ MongoDB 연결 성공');
      
      // 연결 이벤트 리스너 설정
      this.이벤트리스너설정();
      
    } catch (error) {
      console.error('❌ MongoDB 연결 실패:', error.message);
      await this.재연결시도();
    }
  }

  /**
   * 데이터베이스 연결 해제
   * @returns {Promise<void>}
   */
  async 연결해제() {
    try {
      await mongoose.connection.close();
      this.연결상태 = false;
      console.log('📴 MongoDB 연결 해제 완료');
    } catch (error) {
      console.error('❌ MongoDB 연결 해제 실패:', error.message);
    }
  }

  /**
   * 재연결 시도
   * @returns {Promise<void>}
   */
  async 재연결시도() {
    if (this.재연결시도횟수 >= this.최대재연결시도) {
      console.error(`❌ 최대 재연결 시도 횟수(${this.최대재연결시도})를 초과했습니다.`);
      process.exit(1);
    }

    this.재연결시도횟수++;
    const 대기시간 = Math.pow(2, this.재연결시도횟수) * 1000; // 지수 백오프
    
    console.log(`🔄 ${this.재연결시도횟수}번째 재연결 시도 (${대기시간/1000}초 후)`);
    
    setTimeout(async () => {
      await this.연결();
    }, 대기시간);
  }

  /**
   * 연결 상태 확인
   * @returns {boolean} 연결 상태
   */
  연결상태확인() {
    return mongoose.connection.readyState === 1;
  }

  /**
   * 데이터베이스 이벤트 리스너 설정
   */
  이벤트리스너설정() {
    // 연결 해제 이벤트
    mongoose.connection.on('disconnected', () => {
      console.log('⚠️ MongoDB 연결이 해제되었습니다');
      this.연결상태 = false;
    });

    // 연결 오류 이벤트
    mongoose.connection.on('error', (error) => {
      console.error('❌ MongoDB 연결 오류:', error.message);
      this.연결상태 = false;
    });

    // 재연결 이벤트
    mongoose.connection.on('reconnected', () => {
      console.log('🔄 MongoDB 재연결 성공');
      this.연결상태 = true;
      this.재연결시도횟수 = 0;
    });

    // 프로세스 종료 시 연결 정리
    process.on('SIGINT', async () => {
      console.log('\n🛑 프로세스 종료 신호 수신, 데이터베이스 연결 정리 중...');
      await this.연결해제();
      process.exit(0);
    });

    process.on('SIGTERM', async () => {
      console.log('\n🛑 프로세스 종료 신호 수신, 데이터베이스 연결 정리 중...');
      await this.연결해제();
      process.exit(0);
    });
  }

  /**
   * 데이터베이스 상태 정보 반환
   * @returns {Object} 상태 정보
   */
  상태정보() {
    const 연결상태맵 = {
      0: 'disconnected',
      1: 'connected',
      2: 'connecting',
      3: 'disconnecting'
    };

    return {
      상태: 연결상태맵[mongoose.connection.readyState],
      호스트: mongoose.connection.host,
      포트: mongoose.connection.port,
      데이터베이스명: mongoose.connection.name,
      재연결시도횟수: this.재연결시도횟수
    };
  }
}

// 싱글톤 인스턴스 생성
const 데이터베이스인스턴스 = new 데이터베이스설정();

module.exports = 데이터베이스인스턴스;