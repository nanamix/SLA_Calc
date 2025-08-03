const Joi = require('joi');
const 인증서비스 = require('../services/인증서비스');

/**
 * 인증 관련 API 요청을 처리하는 컨트롤러
 */
class 인증컨트롤러 {

  /**
   * 회원가입 API
   * POST /api/auth/register
   */
  async 회원가입(req, res) {
    try {
      // 요청 데이터 검증 스키마
      const 검증스키마 = Joi.object({
        이메일: Joi.string()
          .email()
          .required()
          .messages({
            'string.email': '유효한 이메일 주소를 입력해주세요',
            'any.required': '이메일은 필수 입력 항목입니다'
          }),
        이름: Joi.string()
          .min(2)
          .max(50)
          .required()
          .messages({
            'string.min': '이름은 최소 2자 이상이어야 합니다',
            'string.max': '이름은 최대 50자까지 입력 가능합니다',
            'any.required': '이름은 필수 입력 항목입니다'
          }),
        비밀번호: Joi.string()
          .min(8)
          .pattern(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/)
          .required()
          .messages({
            'string.min': '비밀번호는 최소 8자 이상이어야 합니다',
            'string.pattern.base': '비밀번호는 대소문자, 숫자, 특수문자를 포함해야 합니다',
            'any.required': '비밀번호는 필수 입력 항목입니다'
          }),
        역할: Joi.string()
          .valid('admin', 'manager', 'viewer')
          .default('viewer')
          .messages({
            'any.only': '역할은 admin, manager, viewer 중 하나여야 합니다'
          })
      });

      // 요청 데이터 검증
      const { error, value: 검증된데이터 } = 검증스키마.validate(req.body);
      if (error) {
        return res.status(400).json({
          성공: false,
          메시지: '입력 데이터가 올바르지 않습니다',
          오류: error.details.map(detail => detail.message)
        });
      }

      // 회원가입 처리
      const 결과 = await 인증서비스.회원가입(검증된데이터);
      
      res.status(201).json(결과);

    } catch (error) {
      console.error('회원가입 컨트롤러 오류:', error.message);
      res.status(400).json({
        성공: false,
        메시지: error.message
      });
    }
  }

  /**
   * 로그인 API
   * POST /api/auth/login
   */
  async 로그인(req, res) {
    try {
      // 요청 데이터 검증 스키마
      const 검증스키마 = Joi.object({
        이메일: Joi.string()
          .email()
          .required()
          .messages({
            'string.email': '유효한 이메일 주소를 입력해주세요',
            'any.required': '이메일은 필수 입력 항목입니다'
          }),
        비밀번호: Joi.string()
          .required()
          .messages({
            'any.required': '비밀번호는 필수 입력 항목입니다'
          })
      });

      // 요청 데이터 검증
      const { error, value: 검증된데이터 } = 검증스키마.validate(req.body);
      if (error) {
        return res.status(400).json({
          성공: false,
          메시지: '입력 데이터가 올바르지 않습니다',
          오류: error.details.map(detail => detail.message)
        });
      }

      // 로그인 처리
      const 결과 = await 인증서비스.로그인(검증된데이터);
      
      res.status(200).json(결과);

    } catch (error) {
      console.error('로그인 컨트롤러 오류:', error.message);
      res.status(401).json({
        성공: false,
        메시지: error.message
      });
    }
  }

  /**
   * 로그아웃 API
   * POST /api/auth/logout
   */
  async 로그아웃(req, res) {
    try {
      // 인증된 사용자 정보 가져오기
      const 사용자아이디 = req.사용자._id;
      const 액세스토큰 = req.headers.authorization?.split(' ')[1];

      // 로그아웃 처리
      const 결과 = await 인증서비스.로그아웃(사용자아이디, 액세스토큰);
      
      res.status(200).json(결과);

    } catch (error) {
      console.error('로그아웃 컨트롤러 오류:', error.message);
      res.status(500).json({
        성공: false,
        메시지: error.message
      });
    }
  }

  /**
   * 토큰 갱신 API
   * POST /api/auth/refresh
   */
  async 토큰갱신(req, res) {
    try {
      // 요청 데이터 검증 스키마
      const 검증스키마 = Joi.object({
        리프레시토큰: Joi.string()
          .required()
          .messages({
            'any.required': '리프레시 토큰은 필수입니다'
          })
      });

      // 요청 데이터 검증
      const { error, value: 검증된데이터 } = 검증스키마.validate(req.body);
      if (error) {
        return res.status(400).json({
          성공: false,
          메시지: '입력 데이터가 올바르지 않습니다',
          오류: error.details.map(detail => detail.message)
        });
      }

      // 토큰 갱신 처리
      const 결과 = await 인증서비스.토큰갱신(검증된데이터.리프레시토큰);
      
      res.status(200).json(결과);

    } catch (error) {
      console.error('토큰 갱신 컨트롤러 오류:', error.message);
      res.status(401).json({
        성공: false,
        메시지: error.message
      });
    }
  }

  /**
   * 비밀번호 변경 API
   * PUT /api/auth/password
   */
  async 비밀번호변경(req, res) {
    try {
      // 요청 데이터 검증 스키마
      const 검증스키마 = Joi.object({
        현재비밀번호: Joi.string()
          .required()
          .messages({
            'any.required': '현재 비밀번호는 필수입니다'
          }),
        새비밀번호: Joi.string()
          .min(8)
          .pattern(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/)
          .required()
          .messages({
            'string.min': '새 비밀번호는 최소 8자 이상이어야 합니다',
            'string.pattern.base': '새 비밀번호는 대소문자, 숫자, 특수문자를 포함해야 합니다',
            'any.required': '새 비밀번호는 필수입니다'
          })
      });

      // 요청 데이터 검증
      const { error, value: 검증된데이터 } = 검증스키마.validate(req.body);
      if (error) {
        return res.status(400).json({
          성공: false,
          메시지: '입력 데이터가 올바르지 않습니다',
          오류: error.details.map(detail => detail.message)
        });
      }

      // 비밀번호 변경 처리
      const 사용자아이디 = req.사용자._id;
      const 결과 = await 인증서비스.비밀번호변경(사용자아이디, 검증된데이터);
      
      res.status(200).json(결과);

    } catch (error) {
      console.error('비밀번호 변경 컨트롤러 오류:', error.message);
      res.status(400).json({
        성공: false,
        메시지: error.message
      });
    }
  }

  /**
   * 프로필 조회 API
   * GET /api/auth/profile
   */
  async 프로필조회(req, res) {
    try {
      const 사용자아이디 = req.사용자._id;
      const 결과 = await 인증서비스.프로필조회(사용자아이디);
      
      res.status(200).json(결과);

    } catch (error) {
      console.error('프로필 조회 컨트롤러 오류:', error.message);
      res.status(500).json({
        성공: false,
        메시지: error.message
      });
    }
  }

  /**
   * 프로필 수정 API
   * PUT /api/auth/profile
   */
  async 프로필수정(req, res) {
    try {
      // 요청 데이터 검증 스키마
      const 검증스키마 = Joi.object({
        이름: Joi.string()
          .min(2)
          .max(50)
          .required()
          .messages({
            'string.min': '이름은 최소 2자 이상이어야 합니다',
            'string.max': '이름은 최대 50자까지 입력 가능합니다',
            'any.required': '이름은 필수 입력 항목입니다'
          })
      });

      // 요청 데이터 검증
      const { error, value: 검증된데이터 } = 검증스키마.validate(req.body);
      if (error) {
        return res.status(400).json({
          성공: false,
          메시지: '입력 데이터가 올바르지 않습니다',
          오류: error.details.map(detail => detail.message)
        });
      }

      // 프로필 수정 처리
      const 사용자아이디 = req.사용자._id;
      const 결과 = await 인증서비스.프로필수정(사용자아이디, 검증된데이터);
      
      res.status(200).json(결과);

    } catch (error) {
      console.error('프로필 수정 컨트롤러 오류:', error.message);
      res.status(400).json({
        성공: false,
        메시지: error.message
      });
    }
  }

  /**
   * 토큰 검증 API (다른 서비스에서 사용)
   * POST /api/auth/verify
   */
  async 토큰검증(req, res) {
    try {
      // 이미 인증 미들웨어를 통과했으므로 사용자 정보가 있음
      res.status(200).json({
        성공: true,
        메시지: '유효한 토큰입니다',
        데이터: {
          사용자정보: req.사용자.toJSON(),
          토큰정보: req.토큰정보
        }
      });

    } catch (error) {
      console.error('토큰 검증 컨트롤러 오류:', error.message);
      res.status(500).json({
        성공: false,
        메시지: '토큰 검증 중 오류가 발생했습니다'
      });
    }
  }
}

// 싱글톤 인스턴스 생성
const 인증컨트롤러인스턴스 = new 인증컨트롤러();

module.exports = 인증컨트롤러인스턴스;