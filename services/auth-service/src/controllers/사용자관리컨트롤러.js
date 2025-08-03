const Joi = require('joi');
const 사용자관리서비스 = require('../services/사용자관리서비스');

/**
 * 사용자 관리 관련 API 요청을 처리하는 컨트롤러
 * 관리자 권한이 필요한 사용자 관리 기능을 제공
 */
class 사용자관리컨트롤러 {

  /**
   * 사용자 목록 조회 API
   * GET /api/users
   */
  async 사용자목록조회(req, res) {
    try {
      // 쿼리 파라미터 검증 스키마
      const 검증스키마 = Joi.object({
        페이지: Joi.number().integer().min(1).default(1),
        페이지크기: Joi.number().integer().min(1).max(100).default(10),
        검색어: Joi.string().allow('').default(''),
        역할필터: Joi.string().valid('', 'admin', 'manager', 'viewer').default(''),
        활성상태필터: Joi.string().valid('', 'true', 'false').default('')
      });

      // 쿼리 파라미터 검증
      const { error, value: 검증된쿼리 } = 검증스키마.validate(req.query);
      if (error) {
        return res.status(400).json({
          성공: false,
          메시지: '쿼리 파라미터가 올바르지 않습니다',
          오류: error.details.map(detail => detail.message)
        });
      }

      // 사용자 목록 조회
      const 결과 = await 사용자관리서비스.사용자목록조회(검증된쿼리);
      
      res.status(200).json(결과);

    } catch (error) {
      console.error('사용자 목록 조회 컨트롤러 오류:', error.message);
      res.status(500).json({
        성공: false,
        메시지: error.message
      });
    }
  }

  /**
   * 사용자 상세 조회 API
   * GET /api/users/:id
   */
  async 사용자상세조회(req, res) {
    try {
      const 사용자아이디 = req.params.id;

      // 사용자 ID 검증
      if (!사용자아이디 || 사용자아이디.length !== 24) {
        return res.status(400).json({
          성공: false,
          메시지: '유효하지 않은 사용자 ID입니다'
        });
      }

      // 사용자 상세 조회
      const 결과 = await 사용자관리서비스.사용자상세조회(사용자아이디);
      
      res.status(200).json(결과);

    } catch (error) {
      console.error('사용자 상세 조회 컨트롤러 오류:', error.message);
      res.status(404).json({
        성공: false,
        메시지: error.message
      });
    }
  }

  /**
   * 사용자 생성 API
   * POST /api/users
   */
  async 사용자생성(req, res) {
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
          .required()
          .messages({
            'any.only': '역할은 admin, manager, viewer 중 하나여야 합니다',
            'any.required': '역할은 필수 입력 항목입니다'
          }),
        권한목록: Joi.array()
          .items(Joi.string().valid(
            'service:read', 'service:write', 'service:delete',
            'sla:read', 'sla:calculate',
            'alert:read', 'alert:write',
            'report:read', 'report:generate',
            'user:read', 'user:write',
            'system:admin'
          ))
          .optional()
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

      // 사용자 생성
      const 결과 = await 사용자관리서비스.사용자생성(검증된데이터);
      
      res.status(201).json(결과);

    } catch (error) {
      console.error('사용자 생성 컨트롤러 오류:', error.message);
      res.status(400).json({
        성공: false,
        메시지: error.message
      });
    }
  }

  /**
   * 사용자 수정 API
   * PUT /api/users/:id
   */
  async 사용자수정(req, res) {
    try {
      const 사용자아이디 = req.params.id;

      // 사용자 ID 검증
      if (!사용자아이디 || 사용자아이디.length !== 24) {
        return res.status(400).json({
          성공: false,
          메시지: '유효하지 않은 사용자 ID입니다'
        });
      }

      // 요청 데이터 검증 스키마
      const 검증스키마 = Joi.object({
        이름: Joi.string()
          .min(2)
          .max(50)
          .optional()
          .messages({
            'string.min': '이름은 최소 2자 이상이어야 합니다',
            'string.max': '이름은 최대 50자까지 입력 가능합니다'
          }),
        역할: Joi.string()
          .valid('admin', 'manager', 'viewer')
          .optional()
          .messages({
            'any.only': '역할은 admin, manager, viewer 중 하나여야 합니다'
          }),
        권한목록: Joi.array()
          .items(Joi.string().valid(
            'service:read', 'service:write', 'service:delete',
            'sla:read', 'sla:calculate',
            'alert:read', 'alert:write',
            'report:read', 'report:generate',
            'user:read', 'user:write',
            'system:admin'
          ))
          .optional(),
        활성상태: Joi.boolean().optional()
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

      // 수정할 데이터가 없는 경우
      if (Object.keys(검증된데이터).length === 0) {
        return res.status(400).json({
          성공: false,
          메시지: '수정할 데이터가 없습니다'
        });
      }

      // 사용자 수정
      const 결과 = await 사용자관리서비스.사용자수정(사용자아이디, 검증된데이터);
      
      res.status(200).json(결과);

    } catch (error) {
      console.error('사용자 수정 컨트롤러 오류:', error.message);
      res.status(400).json({
        성공: false,
        메시지: error.message
      });
    }
  }

  /**
   * 사용자 삭제 API
   * DELETE /api/users/:id
   */
  async 사용자삭제(req, res) {
    try {
      const 사용자아이디 = req.params.id;

      // 사용자 ID 검증
      if (!사용자아이디 || 사용자아이디.length !== 24) {
        return res.status(400).json({
          성공: false,
          메시지: '유효하지 않은 사용자 ID입니다'
        });
      }

      // 자기 자신을 삭제하려는 경우 방지
      if (사용자아이디 === req.사용자._id.toString()) {
        return res.status(400).json({
          성공: false,
          메시지: '자기 자신의 계정은 삭제할 수 없습니다'
        });
      }

      // 사용자 삭제
      const 결과 = await 사용자관리서비스.사용자삭제(사용자아이디);
      
      res.status(200).json(결과);

    } catch (error) {
      console.error('사용자 삭제 컨트롤러 오류:', error.message);
      res.status(400).json({
        성공: false,
        메시지: error.message
      });
    }
  }

  /**
   * 계정 상태 변경 API
   * PATCH /api/users/:id/status
   */
  async 계정상태변경(req, res) {
    try {
      const 사용자아이디 = req.params.id;

      // 사용자 ID 검증
      if (!사용자아이디 || 사용자아이디.length !== 24) {
        return res.status(400).json({
          성공: false,
          메시지: '유효하지 않은 사용자 ID입니다'
        });
      }

      // 요청 데이터 검증 스키마
      const 검증스키마 = Joi.object({
        활성상태: Joi.boolean()
          .required()
          .messages({
            'any.required': '활성 상태는 필수입니다'
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

      // 자기 자신의 계정을 비활성화하려는 경우 방지
      if (사용자아이디 === req.사용자._id.toString() && !검증된데이터.활성상태) {
        return res.status(400).json({
          성공: false,
          메시지: '자기 자신의 계정은 비활성화할 수 없습니다'
        });
      }

      // 계정 상태 변경
      const 결과 = await 사용자관리서비스.계정상태변경(사용자아이디, 검증된데이터.활성상태);
      
      res.status(200).json(결과);

    } catch (error) {
      console.error('계정 상태 변경 컨트롤러 오류:', error.message);
      res.status(400).json({
        성공: false,
        메시지: error.message
      });
    }
  }

  /**
   * 계정 잠금 해제 API
   * PATCH /api/users/:id/unlock
   */
  async 계정잠금해제(req, res) {
    try {
      const 사용자아이디 = req.params.id;

      // 사용자 ID 검증
      if (!사용자아이디 || 사용자아이디.length !== 24) {
        return res.status(400).json({
          성공: false,
          메시지: '유효하지 않은 사용자 ID입니다'
        });
      }

      // 계정 잠금 해제
      const 결과 = await 사용자관리서비스.계정잠금해제(사용자아이디);
      
      res.status(200).json(결과);

    } catch (error) {
      console.error('계정 잠금 해제 컨트롤러 오류:', error.message);
      res.status(400).json({
        성공: false,
        메시지: error.message
      });
    }
  }

  /**
   * 비밀번호 재설정 API
   * PATCH /api/users/:id/reset-password
   */
  async 비밀번호재설정(req, res) {
    try {
      const 사용자아이디 = req.params.id;

      // 사용자 ID 검증
      if (!사용자아이디 || 사용자아이디.length !== 24) {
        return res.status(400).json({
          성공: false,
          메시지: '유효하지 않은 사용자 ID입니다'
        });
      }

      // 요청 데이터 검증 스키마
      const 검증스키마 = Joi.object({
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

      // 비밀번호 재설정
      const 결과 = await 사용자관리서비스.비밀번호재설정(사용자아이디, 검증된데이터.새비밀번호);
      
      res.status(200).json(결과);

    } catch (error) {
      console.error('비밀번호 재설정 컨트롤러 오류:', error.message);
      res.status(400).json({
        성공: false,
        메시지: error.message
      });
    }
  }

  /**
   * 사용자 통계 조회 API
   * GET /api/users/stats
   */
  async 사용자통계조회(req, res) {
    try {
      // 사용자 통계 조회
      const 결과 = await 사용자관리서비스.사용자통계조회();
      
      res.status(200).json(결과);

    } catch (error) {
      console.error('사용자 통계 조회 컨트롤러 오류:', error.message);
      res.status(500).json({
        성공: false,
        메시지: error.message
      });
    }
  }
}

// 싱글톤 인스턴스 생성
const 사용자관리컨트롤러인스턴스 = new 사용자관리컨트롤러();

module.exports = 사용자관리컨트롤러인스턴스;