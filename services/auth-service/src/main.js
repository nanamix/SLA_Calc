require('dotenv').config();
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');

// 내부 모듈 import
const 데이터베이스설정 = require('./config/데이터베이스설정');
const 인증라우터 = require('./routes/인증라우터');
const 사용자관리라우터 = require('./routes/사용자관리라우터');

/**
 * SLA Calculator 인증 서비스
 * JWT 기반 사용자 인증 및 권한 관리를 담당하는 마이크로서비스
 */
class 인증서비스앱 {
  constructor() {
    this.앱 = express();
    this.포트 = process.env.PORT || 3001;
    this.환경 = process.env.NODE_ENV || 'development';
    
    this.미들웨어설정();
    this.라우터설정();
    this.오류처리설정();
  }

  /**
   * Express 미들웨어 설정
   */
  미들웨어설정() {
    // 보안 헤더 설정
    this.앱.use(helmet({
      contentSecurityPolicy: {
        directives: {
          defaultSrc: ["'self'"],
          styleSrc: ["'self'", "'unsafe-inline'"],
          scriptSrc: ["'self'"],
          imgSrc: ["'self'", "data:", "https:"]
        }
      },
      hsts: {
        maxAge: 31536000,
        includeSubDomains: true,
        preload: true
      }
    }));

    // CORS 설정
    const 허용된도메인 = process.env.ALLOWED_ORIGINS 
      ? process.env.ALLOWED_ORIGINS.split(',')
      : ['http://localhost:3000', 'http://localhost:8080'];

    this.앱.use(cors({
      origin: (origin, callback) => {
        // 개발 환경에서는 origin이 없을 수 있음 (Postman 등)
        if (!origin && this.환경 === 'development') {
          return callback(null, true);
        }
        
        if (허용된도메인.includes(origin)) {
          callback(null, true);
        } else {
          callback(new Error('CORS 정책에 의해 차단된 요청입니다'));
        }
      },
      credentials: true,
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
    }));

    // 전역 Rate Limiting
    const 전역제한 = rateLimit({
      windowMs: 15 * 60 * 1000, // 15분
      max: this.환경 === 'production' ? 100 : 1000, // 프로덕션에서는 더 엄격하게
      message: {
        성공: false,
        메시지: '요청이 너무 많습니다. 잠시 후 다시 시도해주세요',
        오류코드: 'RATE_LIMIT_EXCEEDED'
      },
      standardHeaders: true,
      legacyHeaders: false
    });
    this.앱.use(전역제한);

    // JSON 파싱 설정
    this.앱.use(express.json({ 
      limit: '10mb',
      strict: true
    }));

    // URL 인코딩 파싱 설정
    this.앱.use(express.urlencoded({ 
      extended: true, 
      limit: '10mb' 
    }));

    // 요청 로깅 미들웨어 (개발 환경)
    if (this.환경 === 'development') {
      this.앱.use((req, res, next) => {
        const 시작시간 = Date.now();
        
        res.on('finish', () => {
          const 소요시간 = Date.now() - 시작시간;
          console.log(`${req.method} ${req.path} - ${res.statusCode} (${소요시간}ms)`);
        });
        
        next();
      });
    }
  }

  /**
   * API 라우터 설정
   */
  라우터설정() {
    // 헬스체크 엔드포인트
    this.앱.get('/health', (req, res) => {
      res.json({
        상태: '정상',
        서비스: 'auth-service',
        버전: '1.0.0',
        시간: new Date().toISOString(),
        데이터베이스: 데이터베이스설정.연결상태확인() ? '연결됨' : '연결안됨',
        환경: this.환경
      });
    });

    // API 라우터 등록
    this.앱.use('/api/auth', 인증라우터);
    this.앱.use('/api/users', 사용자관리라우터);

    // 루트 경로
    this.앱.get('/', (req, res) => {
      res.json({
        메시지: 'SLA Calculator 인증 서비스에 오신 것을 환영합니다',
        버전: '1.0.0',
        문서: '/api/auth',
        헬스체크: '/health',
        환경: this.환경
      });
    });

    // 404 처리
    this.앱.use('*', (req, res) => {
      res.status(404).json({
        성공: false,
        메시지: '요청하신 API 엔드포인트를 찾을 수 없습니다',
        경로: req.originalUrl,
        메서드: req.method
      });
    });
  }

  /**
   * 전역 오류 처리 설정
   */
  오류처리설정() {
    // 전역 오류 처리 미들웨어
    this.앱.use((error, req, res, next) => {
      console.error('전역 오류 처리:', error);

      // CORS 오류 처리
      if (error.message.includes('CORS')) {
        return res.status(403).json({
          성공: false,
          메시지: 'CORS 정책 위반',
          오류코드: 'CORS_ERROR'
        });
      }

      // JSON 파싱 오류 처리
      if (error instanceof SyntaxError && error.status === 400 && 'body' in error) {
        return res.status(400).json({
          성공: false,
          메시지: 'JSON 형식이 올바르지 않습니다',
          오류코드: 'JSON_PARSE_ERROR'
        });
      }

      // MongoDB 연결 오류 처리
      if (error.name === 'MongoError' || error.name === 'MongooseError') {
        return res.status(503).json({
          성공: false,
          메시지: '데이터베이스 연결 오류',
          오류코드: 'DATABASE_ERROR'
        });
      }

      // JWT 관련 오류 처리
      if (error.name === 'JsonWebTokenError') {
        return res.status(401).json({
          성공: false,
          메시지: '유효하지 않은 토큰입니다',
          오류코드: 'INVALID_TOKEN'
        });
      }

      if (error.name === 'TokenExpiredError') {
        return res.status(401).json({
          성공: false,
          메시지: '토큰이 만료되었습니다',
          오류코드: 'TOKEN_EXPIRED'
        });
      }

      // 기본 서버 오류
      res.status(500).json({
        성공: false,
        메시지: this.환경 === 'production' 
          ? '서버 내부 오류가 발생했습니다' 
          : error.message,
        오류코드: 'INTERNAL_SERVER_ERROR',
        ...(this.환경 === 'development' && { 스택: error.stack })
      });
    });

    // 처리되지 않은 Promise 거부 처리
    process.on('unhandledRejection', (reason, promise) => {
      console.error('처리되지 않은 Promise 거부:', reason);
      console.error('Promise:', promise);
    });

    // 처리되지 않은 예외 처리
    process.on('uncaughtException', (error) => {
      console.error('처리되지 않은 예외:', error);
      process.exit(1);
    });
  }

  /**
   * 서버 시작
   */
  async 시작() {
    try {
      // 데이터베이스 연결
      await 데이터베이스설정.연결();

      // 서버 시작
      this.서버 = this.앱.listen(this.포트, () => {
        console.log(`
🚀 SLA Calculator 인증 서비스가 시작되었습니다!
📍 포트: ${this.포트}
🌍 환경: ${this.환경}
📊 헬스체크: http://localhost:${this.포트}/health
📚 API 문서: http://localhost:${this.포트}/api/auth
⏰ 시작 시간: ${new Date().toLocaleString('ko-KR')}
        `);
      });

      // Graceful shutdown 설정
      this.종료처리설정();

    } catch (error) {
      console.error('❌ 서버 시작 실패:', error);
      process.exit(1);
    }
  }

  /**
   * Graceful shutdown 처리
   */
  종료처리설정() {
    const 종료처리 = async (신호) => {
      console.log(`\n🛑 ${신호} 신호 수신, 서버 종료 중...`);
      
      if (this.서버) {
        this.서버.close(async () => {
          console.log('✅ HTTP 서버 종료 완료');
          
          // 데이터베이스 연결 해제
          await 데이터베이스설정.연결해제();
          
          console.log('✅ 모든 연결이 정리되었습니다');
          process.exit(0);
        });
      }
    };

    process.on('SIGTERM', () => 종료처리('SIGTERM'));
    process.on('SIGINT', () => 종료처리('SIGINT'));
  }
}

// 애플리케이션 인스턴스 생성 및 시작
const 앱 = new 인증서비스앱();

// 모듈이 직접 실행될 때만 서버 시작
if (require.main === module) {
  앱.시작();
}

module.exports = 앱;