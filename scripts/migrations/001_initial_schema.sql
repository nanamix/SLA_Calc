-- 001_initial_schema.sql
-- SLA Calculator 초기 스키마 마이그레이션

-- 마이그레이션 히스토리 테이블 생성
CREATE TABLE IF NOT EXISTS 마이그레이션히스토리 (
    아이디 SERIAL PRIMARY KEY,
    마이그레이션명 VARCHAR(255) UNIQUE NOT NULL,
    실행일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    성공여부 BOOLEAN DEFAULT true
);

-- 확장 기능 활성화
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- 텍스트 검색 최적화

-- 사용자 테이블
CREATE TABLE IF NOT EXISTS 사용자 (
    아이디 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    이메일 VARCHAR(255) UNIQUE NOT NULL,
    이름 VARCHAR(100) NOT NULL,
    비밀번호해시 VARCHAR(255) NOT NULL,
    역할 VARCHAR(20) DEFAULT 'viewer' CHECK (역할 IN ('admin', 'manager', 'viewer')),
    권한목록 JSONB DEFAULT '[]',
    활성여부 BOOLEAN DEFAULT true,
    생성일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    수정일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    마지막로그인일시 TIMESTAMP WITH TIME ZONE,
    로그인실패횟수 INTEGER DEFAULT 0,
    계정잠금일시 TIMESTAMP WITH TIME ZONE
);

-- 서비스 테이블
CREATE TABLE IF NOT EXISTS 서비스 (
    아이디 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    이름 VARCHAR(100) NOT NULL,
    설명 TEXT,
    목표SLA DECIMAL(5,2) NOT NULL CHECK (목표SLA >= 0 AND 목표SLA <= 100),
    서비스타입 VARCHAR(20) DEFAULT 'web' CHECK (서비스타입 IN ('web', 'api', 'database', 'infrastructure')),
    모니터링설정 JSONB DEFAULT '{}',
    활성여부 BOOLEAN DEFAULT true,
    생성일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    수정일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    소유자아이디 UUID REFERENCES 사용자(아이디)
);

-- SLA 메트릭 테이블 (파티셔닝 적용)
CREATE TABLE IF NOT EXISTS SLA메트릭 (
    아이디 UUID DEFAULT uuid_generate_v4(),
    서비스아이디 UUID NOT NULL REFERENCES 서비스(아이디) ON DELETE CASCADE,
    메트릭타입 VARCHAR(20) NOT NULL CHECK (메트릭타입 IN ('availability', 'response_time', 'throughput')),
    값 DECIMAL(10,4) NOT NULL,
    계산된SLA DECIMAL(5,2),
    위반여부 BOOLEAN DEFAULT false,
    메타데이터 JSONB DEFAULT '{}',
    타임스탬프 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (아이디, 타임스탬프)
) PARTITION BY RANGE (타임스탬프);

-- 월별 파티션 테이블 생성 함수
CREATE OR REPLACE FUNCTION SLA메트릭_파티션_생성(시작날짜 DATE, 종료날짜 DATE)
RETURNS VOID AS $$
DECLARE
    파티션명 TEXT;
    년월 TEXT;
BEGIN
    년월 := TO_CHAR(시작날짜, 'YYYY_MM');
    파티션명 := 'SLA메트릭_' || 년월;
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF SLA메트릭 
                    FOR VALUES FROM (%L) TO (%L)', 
                   파티션명, 시작날짜, 종료날짜);
    
    -- 파티션별 인덱스 생성
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_서비스아이디 ON %I(서비스아이디)', 
                   파티션명, 파티션명);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_메트릭타입 ON %I(메트릭타입)', 
                   파티션명, 파티션명);
END;
$$ LANGUAGE plpgsql;

-- 현재 월과 다음 월 파티션 생성
SELECT SLA메트릭_파티션_생성(
    DATE_TRUNC('month', CURRENT_DATE),
    DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month')
);

SELECT SLA메트릭_파티션_생성(
    DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month'),
    DATE_TRUNC('month', CURRENT_DATE + INTERVAL '2 month')
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
    마지막알림일시 TIMESTAMP WITH TIME ZONE,
    생성일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    수정일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 알림 히스토리 테이블
CREATE TABLE IF NOT EXISTS 알림히스토리 (
    아이디 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    알림설정아이디 UUID NOT NULL REFERENCES 알림설정(아이디) ON DELETE CASCADE,
    서비스아이디 UUID NOT NULL REFERENCES 서비스(아이디) ON DELETE CASCADE,
    메시지 TEXT NOT NULL,
    발송채널 VARCHAR(50) NOT NULL,
    발송상태 VARCHAR(20) DEFAULT 'pending' CHECK (발송상태 IN ('pending', 'sent', 'failed')),
    발송일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    오류메시지 TEXT,
    재시도횟수 INTEGER DEFAULT 0
);

-- 보고서 템플릿 테이블
CREATE TABLE IF NOT EXISTS 보고서템플릿 (
    아이디 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    이름 VARCHAR(100) NOT NULL,
    설명 TEXT,
    템플릿타입 VARCHAR(20) DEFAULT 'pdf' CHECK (템플릿타입 IN ('pdf', 'excel')),
    스케줄 VARCHAR(100), -- Cron 표현식
    서비스아이디목록 JSONB DEFAULT '[]',
    수신자목록 JSONB DEFAULT '[]',
    템플릿설정 JSONB DEFAULT '{}',
    활성여부 BOOLEAN DEFAULT true,
    생성일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    수정일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    생성자아이디 UUID REFERENCES 사용자(아이디)
);

-- 보고서 생성 히스토리 테이블
CREATE TABLE IF NOT EXISTS 보고서히스토리 (
    아이디 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    템플릿아이디 UUID NOT NULL REFERENCES 보고서템플릿(아이디) ON DELETE CASCADE,
    파일경로 VARCHAR(500),
    생성상태 VARCHAR(20) DEFAULT 'pending' CHECK (생성상태 IN ('pending', 'completed', 'failed')),
    생성일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    완료일시 TIMESTAMP WITH TIME ZONE,
    오류메시지 TEXT,
    파일크기 BIGINT
);

-- 데이터 소스 설정 테이블
CREATE TABLE IF NOT EXISTS 데이터소스설정 (
    아이디 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    이름 VARCHAR(100) NOT NULL,
    타입 VARCHAR(50) NOT NULL CHECK (타입 IN ('prometheus', 'grafana', 'pingdom', 'newrelic', 'custom')),
    연결설정 JSONB NOT NULL DEFAULT '{}',
    인증정보 JSONB DEFAULT '{}', -- 암호화된 인증 정보
    활성여부 BOOLEAN DEFAULT true,
    마지막연결일시 TIMESTAMP WITH TIME ZONE,
    연결상태 VARCHAR(20) DEFAULT 'unknown' CHECK (연결상태 IN ('connected', 'disconnected', 'error', 'unknown')),
    생성일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    수정일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 감사 로그 테이블
CREATE TABLE IF NOT EXISTS 감사로그 (
    아이디 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    사용자아이디 UUID REFERENCES 사용자(아이디),
    액션 VARCHAR(100) NOT NULL,
    리소스타입 VARCHAR(50) NOT NULL,
    리소스아이디 UUID,
    변경전데이터 JSONB,
    변경후데이터 JSONB,
    IP주소 INET,
    사용자에이전트 TEXT,
    실행일시 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 마이그레이션 기록
INSERT INTO 마이그레이션히스토리 (마이그레이션명) 
VALUES ('001_initial_schema') 
ON CONFLICT (마이그레이션명) DO NOTHING;