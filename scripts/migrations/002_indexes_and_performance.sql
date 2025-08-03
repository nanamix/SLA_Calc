-- 002_indexes_and_performance.sql
-- 인덱스 및 성능 최적화 마이그레이션

-- 기본 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_사용자_이메일 ON 사용자(이메일);
CREATE INDEX IF NOT EXISTS idx_사용자_역할 ON 사용자(역할);
CREATE INDEX IF NOT EXISTS idx_사용자_활성여부 ON 사용자(활성여부);
CREATE INDEX IF NOT EXISTS idx_사용자_마지막로그인일시 ON 사용자(마지막로그인일시);

-- 서비스 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_서비스_이름 ON 서비스 USING gin(이름 gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_서비스_타입 ON 서비스(서비스타입);
CREATE INDEX IF NOT EXISTS idx_서비스_활성여부 ON 서비스(활성여부);
CREATE INDEX IF NOT EXISTS idx_서비스_소유자 ON 서비스(소유자아이디);
CREATE INDEX IF NOT EXISTS idx_서비스_목표SLA ON 서비스(목표SLA);

-- SLA 메트릭 테이블 인덱스 (파티션 테이블용)
CREATE INDEX IF NOT EXISTS idx_sla메트릭_서비스아이디_타임스탬프 ON SLA메트릭(서비스아이디, 타임스탬프 DESC);
CREATE INDEX IF NOT EXISTS idx_sla메트릭_메트릭타입_타임스탬프 ON SLA메트릭(메트릭타입, 타임스탬프 DESC);
CREATE INDEX IF NOT EXISTS idx_sla메트릭_위반여부 ON SLA메트릭(위반여부) WHERE 위반여부 = true;
CREATE INDEX IF NOT EXISTS idx_sla메트릭_계산된sla ON SLA메트릭(계산된SLA);

-- 복합 인덱스 (자주 사용되는 쿼리 패턴용)
CREATE INDEX IF NOT EXISTS idx_sla메트릭_서비스_타입_시간 ON SLA메트릭(서비스아이디, 메트릭타입, 타임스탬프 DESC);

-- 알림 설정 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_알림설정_서비스아이디 ON 알림설정(서비스아이디);
CREATE INDEX IF NOT EXISTS idx_알림설정_활성여부 ON 알림설정(활성여부) WHERE 활성여부 = true;
CREATE INDEX IF NOT EXISTS idx_알림설정_임계값 ON 알림설정(임계값타입, 임계값);

-- 알림 히스토리 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_알림히스토리_발송일시 ON 알림히스토리(발송일시 DESC);
CREATE INDEX IF NOT EXISTS idx_알림히스토리_발송상태 ON 알림히스토리(발송상태);
CREATE INDEX IF NOT EXISTS idx_알림히스토리_서비스아이디 ON 알림히스토리(서비스아이디);

-- 보고서 관련 인덱스
CREATE INDEX IF NOT EXISTS idx_보고서템플릿_활성여부 ON 보고서템플릿(활성여부) WHERE 활성여부 = true;
CREATE INDEX IF NOT EXISTS idx_보고서템플릿_생성자 ON 보고서템플릿(생성자아이디);
CREATE INDEX IF NOT EXISTS idx_보고서히스토리_생성일시 ON 보고서히스토리(생성일시 DESC);
CREATE INDEX IF NOT EXISTS idx_보고서히스토리_상태 ON 보고서히스토리(생성상태);

-- 데이터 소스 인덱스
CREATE INDEX IF NOT EXISTS idx_데이터소스설정_타입 ON 데이터소스설정(타입);
CREATE INDEX IF NOT EXISTS idx_데이터소스설정_활성여부 ON 데이터소스설정(활성여부) WHERE 활성여부 = true;
CREATE INDEX IF NOT EXISTS idx_데이터소스설정_연결상태 ON 데이터소스설정(연결상태);

-- 감사 로그 인덱스
CREATE INDEX IF NOT EXISTS idx_감사로그_사용자아이디 ON 감사로그(사용자아이디);
CREATE INDEX IF NOT EXISTS idx_감사로그_실행일시 ON 감사로그(실행일시 DESC);
CREATE INDEX IF NOT EXISTS idx_감사로그_액션 ON 감사로그(액션);
CREATE INDEX IF NOT EXISTS idx_감사로그_리소스 ON 감사로그(리소스타입, 리소스아이디);

-- 성능 최적화를 위한 뷰 생성
CREATE OR REPLACE VIEW 서비스_현재_SLA_상태 AS
SELECT 
    s.아이디 as 서비스아이디,
    s.이름 as 서비스이름,
    s.목표SLA,
    s.서비스타입,
    COALESCE(
        (SELECT 계산된SLA 
         FROM SLA메트릭 m 
         WHERE m.서비스아이디 = s.아이디 
           AND m.메트릭타입 = 'availability'
         ORDER BY m.타임스탬프 DESC 
         LIMIT 1), 
        0
    ) as 현재_가용성,
    COALESCE(
        (SELECT 계산된SLA 
         FROM SLA메트릭 m 
         WHERE m.서비스아이디 = s.아이디 
           AND m.메트릭타입 = 'response_time'
         ORDER BY m.타임스탬프 DESC 
         LIMIT 1), 
        0
    ) as 현재_응답시간_SLA,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM SLA메트릭 m 
            WHERE m.서비스아이디 = s.아이디 
              AND m.위반여부 = true 
              AND m.타임스탬프 >= NOW() - INTERVAL '1 hour'
        ) THEN true 
        ELSE false 
    END as 최근_위반여부,
    s.활성여부
FROM 서비스 s
WHERE s.활성여부 = true;

-- SLA 통계 뷰
CREATE OR REPLACE VIEW 월별_SLA_통계 AS
SELECT 
    s.아이디 as 서비스아이디,
    s.이름 as 서비스이름,
    DATE_TRUNC('month', m.타임스탬프) as 월,
    m.메트릭타입,
    AVG(m.계산된SLA) as 평균_SLA,
    MIN(m.계산된SLA) as 최소_SLA,
    MAX(m.계산된SLA) as 최대_SLA,
    COUNT(*) as 측정횟수,
    COUNT(*) FILTER (WHERE m.위반여부 = true) as 위반횟수
FROM 서비스 s
JOIN SLA메트릭 m ON s.아이디 = m.서비스아이디
WHERE s.활성여부 = true
GROUP BY s.아이디, s.이름, DATE_TRUNC('month', m.타임스탬프), m.메트릭타입;

-- 트리거 함수들
CREATE OR REPLACE FUNCTION 수정일시_업데이트()
RETURNS TRIGGER AS $$
BEGIN
    NEW.수정일시 = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 감사 로그 트리거 함수
CREATE OR REPLACE FUNCTION 감사로그_기록()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO 감사로그 (액션, 리소스타입, 리소스아이디, 변경전데이터)
        VALUES (TG_OP, TG_TABLE_NAME, OLD.아이디, row_to_json(OLD));
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO 감사로그 (액션, 리소스타입, 리소스아이디, 변경전데이터, 변경후데이터)
        VALUES (TG_OP, TG_TABLE_NAME, NEW.아이디, row_to_json(OLD), row_to_json(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO 감사로그 (액션, 리소스타입, 리소스아이디, 변경후데이터)
        VALUES (TG_OP, TG_TABLE_NAME, NEW.아이디, row_to_json(NEW));
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 수정일시 트리거 생성
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

DROP TRIGGER IF EXISTS 보고서템플릿_수정일시_트리거 ON 보고서템플릿;
CREATE TRIGGER 보고서템플릿_수정일시_트리거
    BEFORE UPDATE ON 보고서템플릿
    FOR EACH ROW
    EXECUTE FUNCTION 수정일시_업데이트();

DROP TRIGGER IF EXISTS 데이터소스설정_수정일시_트리거 ON 데이터소스설정;
CREATE TRIGGER 데이터소스설정_수정일시_트리거
    BEFORE UPDATE ON 데이터소스설정
    FOR EACH ROW
    EXECUTE FUNCTION 수정일시_업데이트();

-- 감사 로그 트리거 생성 (중요한 테이블들에만 적용)
DROP TRIGGER IF EXISTS 사용자_감사로그_트리거 ON 사용자;
CREATE TRIGGER 사용자_감사로그_트리거
    AFTER INSERT OR UPDATE OR DELETE ON 사용자
    FOR EACH ROW
    EXECUTE FUNCTION 감사로그_기록();

DROP TRIGGER IF EXISTS 서비스_감사로그_트리거 ON 서비스;
CREATE TRIGGER 서비스_감사로그_트리거
    AFTER INSERT OR UPDATE OR DELETE ON 서비스
    FOR EACH ROW
    EXECUTE FUNCTION 감사로그_기록();

DROP TRIGGER IF EXISTS 알림설정_감사로그_트리거 ON 알림설정;
CREATE TRIGGER 알림설정_감사로그_트리거
    AFTER INSERT OR UPDATE OR DELETE ON 알림설정
    FOR EACH ROW
    EXECUTE FUNCTION 감사로그_기록();

-- 마이그레이션 기록
INSERT INTO 마이그레이션히스토리 (마이그레이션명) 
VALUES ('002_indexes_and_performance') 
ON CONFLICT (마이그레이션명) DO NOTHING;