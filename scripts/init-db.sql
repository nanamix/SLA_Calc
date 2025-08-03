-- SLA Calculator 데이터베이스 초기화 스크립트

-- 확장 기능 활성화
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- 사용자 테이블
CREATE TABLE IF NOT EXISTS 사용자 (
    아이디 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    이메일 VARCHAR(255) UNIQUE NOT NULL,
    이름 VARCHAR(100) NOT NULL,
    비밀번호해시 VARCHAR(255) NOT NULL,
    역할 VARCHAR(20) DEFAULT 'viewer' CHECK (역할 IN ('admin', 'manager', 'viewer')),
    활성여부 BOOLEAN DEFAULT true,
    생성일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    수정일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    마지막로그인일시 TIMESTAMP WITH TIME ZONE
);

-- 서비스 테이블
CREATE TABLE IF NOT EXISTS 서비스 (
    아이디 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    이름 VARCHAR(100) NOT NULL,
    설명 TEXT,
    목표SLA DECIMAL(5,2) NOT NULL CHECK (목표SLA >= 0 AND 목표SLA <= 100),
    서비스타입 VARCHAR(20) DEFAULT 'web' CHECK (서비스타입 IN ('web', 'api', 'database', 'infrastructure')),
    활성여부 BOOLEAN DEFAULT true,
    생성일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    수정일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    소유자아이디 UUID REFERENCES 사용자(아이디)
);

-- SLA 메트릭 테이블
CREATE TABLE IF NOT EXISTS SLA메트릭 (
    아이디 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    서비스아이디 UUID NOT NULL REFERENCES 서비스(아이디) ON DELETE CASCADE,
    메트릭타입 VARCHAR(20) NOT NULL CHECK (메트릭타입 IN ('availability', 'response_time', 'throughput')),
    값 DECIMAL(10,4) NOT NULL,
    계산된SLA DECIMAL(5,2),
    위반여부 BOOLEAN DEFAULT false,
    타임스탬프 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 알림 설정 테이블
CREATE TABLE IF NOT EXISTS 알림설정 (
    아이디 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    서비스아이디 UUID NOT NULL REFERENCES 서비스(아이디) ON DELETE CASCADE,
    임계값타입 VARCHAR(10) NOT NULL CHECK (임계값타입 IN ('below', 'above')),
    임계값 DECIMAL(5,2) NOT NULL,
    알림채널 JSONB NOT NULL DEFAULT '[]',
    활성여부 BOOLEAN DEFAULT true,
    쿨다운시간 INTEGER DEFAULT 30, -- 분 단위
    생성일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    수정일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 알림 히스토리 테이블
CREATE TABLE IF NOT EXISTS 알림히스토리 (
    아이디 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    알림설정아이디 UUID NOT NULL REFERENCES 알림설정(아이디) ON DELETE CASCADE,
    메시지 TEXT NOT NULL,
    발송채널 VARCHAR(50) NOT NULL,
    발송상태 VARCHAR(20) DEFAULT 'pending' CHECK (발송상태 IN ('pending', 'sent', 'failed')),
    발송일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    오류메시지 TEXT
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_sla메트릭_서비스아이디 ON SLA메트릭(서비스아이디);
CREATE INDEX IF NOT EXISTS idx_sla메트릭_타임스탬프 ON SLA메트릭(타임스탬프);
CREATE INDEX IF NOT EXISTS idx_sla메트릭_메트릭타입 ON SLA메트릭(메트릭타입);
CREATE INDEX IF NOT EXISTS idx_알림설정_서비스아이디 ON 알림설정(서비스아이디);
CREATE INDEX IF NOT EXISTS idx_알림히스토리_발송일시 ON 알림히스토리(발송일시);

-- 기본 관리자 사용자 생성 (비밀번호: admin123)
INSERT INTO 사용자 (이메일, 이름, 비밀번호해시, 역할) 
VALUES ('admin@sla-calculator.local', '시스템 관리자', '$2b$10$rQZ8kHWKQVz8kHWKQVz8kOQVz8kHWKQVz8kHWKQVz8kHWKQVz8kH', 'admin')
ON CONFLICT (이메일) DO NOTHING;

-- 샘플 서비스 데이터
INSERT INTO 서비스 (이름, 설명, 목표SLA, 서비스타입, 소유자아이디) 
SELECT 
    '웹 애플리케이션',
    '메인 웹 애플리케이션 서비스',
    99.9,
    'web',
    아이디
FROM 사용자 WHERE 이메일 = 'admin@sla-calculator.local'
ON CONFLICT DO NOTHING;

-- 트리거 함수: 수정일시 자동 업데이트
CREATE OR REPLACE FUNCTION 수정일시_업데이트()
RETURNS TRIGGER AS $$
BEGIN
    NEW.수정일시 = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 트리거 생성
DROP TRIGGER IF EXISTS 사용자_수정일시_트리거 ON 사용자;
CREATE TRIGGER 사용자_수정일시_트리거
    BEFORE UPDATE ON 사용자
    FOR EACH ROW
    EXECUTE FUNCTION 수정일시_업데이트();

DROP TRIGGER IF EXISTS 서비스_수정일시_트리거 ON 서비스;
CREATE TRIGGER 서비스_수정일시_트리거
    BEFORE UPDATE ON 서비스
    FOR EACH ROW
    EXECUTE FUNCTION 수정일시_업데이트();

DROP TRIGGER IF EXISTS 알림설정_수정일시_트리거 ON 알림설정;
CREATE TRIGGER 알림설정_수정일시_트리거
    BEFORE UPDATE ON 알림설정
    FOR EACH ROW
    EXECUTE FUNCTION 수정일시_업데이트();