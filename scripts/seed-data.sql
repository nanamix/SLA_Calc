-- seed-data.sql
-- SLA Calculator 초기 시드 데이터

-- 기본 관리자 사용자 생성 (비밀번호: admin123 - bcrypt 해시)
INSERT INTO 사용자 (이메일, 이름, 비밀번호해시, 역할, 권한목록) 
VALUES 
    ('admin@sla-calculator.local', '시스템 관리자', '$2b$10$rQZ8kHWKQVz8kHWKQVz8kOQVz8kHWKQVz8kHWKQVz8kHWKQVz8kH', 'admin', 
     '["user_management", "service_management", "alert_management", "report_management", "system_settings"]'),
    ('manager@sla-calculator.local', 'DevOps 매니저', '$2b$10$rQZ8kHWKQVz8kHWKQVz8kOQVz8kHWKQVz8kHWKQVz8kHWKQVz8kH', 'manager',
     '["service_management", "alert_management", "report_management"]'),
    ('engineer@sla-calculator.local', 'DevOps 엔지니어', '$2b$10$rQZ8kHWKQVz8kHWKQVz8kOQVz8kHWKQVz8kHWKQVz8kHWKQVz8kH', 'viewer',
     '["service_view", "alert_view"]')
ON CONFLICT (이메일) DO NOTHING;

-- 샘플 서비스 데이터
INSERT INTO 서비스 (이름, 설명, 목표SLA, 서비스타입, 모니터링설정, 소유자아이디) 
SELECT 
    '웹 애플리케이션',
    '메인 웹 애플리케이션 서비스 - 사용자 대면 서비스',
    99.9,
    'web',
    '{"endpoints": ["https://app.example.com/health"], "check_interval": 60, "timeout": 30}',
    아이디
FROM 사용자 WHERE 이메일 = 'admin@sla-calculator.local'
ON CONFLICT DO NOTHING;

INSERT INTO 서비스 (이름, 설명, 목표SLA, 서비스타입, 모니터링설정, 소유자아이디) 
SELECT 
    'API 게이트웨이',
    '마이크로서비스 API 게이트웨이',
    99.95,
    'api',
    '{"endpoints": ["https://api.example.com/health"], "check_interval": 30, "timeout": 15}',
    아이디
FROM 사용자 WHERE 이메일 = 'manager@sla-calculator.local'
ON CONFLICT DO NOTHING;

INSERT INTO 서비스 (이름, 설명, 목표SLA, 서비스타입, 모니터링설정, 소유자아이디) 
SELECT 
    '데이터베이스 클러스터',
    'PostgreSQL 마스터-슬레이브 클러스터',
    99.99,
    'database',
    '{"connection_string": "postgresql://monitor@db.example.com:5432/health", "check_interval": 60}',
    아이디
FROM 사용자 WHERE 이메일 = 'admin@sla-calculator.local'
ON CONFLICT DO NOTHING;

INSERT INTO 서비스 (이름, 설명, 목표SLA, 서비스타입, 모니터링설정, 소유자아이디) 
SELECT 
    'Kubernetes 클러스터',
    '프로덕션 Kubernetes 클러스터 인프라',
    99.5,
    'infrastructure',
    '{"prometheus_query": "up{job=\"kubernetes-nodes\"}", "check_interval": 120}',
    아이디
FROM 사용자 WHERE 이메일 = 'engineer@sla-calculator.local'
ON CONFLICT DO NOTHING;

-- 샘플 데이터 소스 설정
INSERT INTO 데이터소스설정 (이름, 타입, 연결설정, 인증정보, 활성여부)
VALUES 
    ('Prometheus 모니터링', 'prometheus', 
     '{"url": "http://prometheus:9090", "timeout": 30}',
     '{"username": "admin", "password": "encrypted_password"}',
     true),
    ('Grafana 대시보드', 'grafana',
     '{"url": "http://grafana:3000", "api_version": "v1"}',
     '{"api_key": "encrypted_api_key"}',
     true),
    ('Pingdom 외부 모니터링', 'pingdom',
     '{"api_url": "https://api.pingdom.com/api/3.1"}',
     '{"api_token": "encrypted_token"}',
     false);

-- 샘플 알림 설정
INSERT INTO 알림설정 (서비스아이디, 임계값타입, 임계값, 알림채널, 쿨다운시간)
SELECT 
    s.아이디,
    'below',
    99.0,
    '["email:admin@sla-calculator.local", "slack:#alerts"]',
    15
FROM 서비스 s 
WHERE s.이름 = '웹 애플리케이션';

INSERT INTO 알림설정 (서비스아이디, 임계값타입, 임계값, 알림채널, 쿨다운시간)
SELECT 
    s.아이디,
    'below',
    99.5,
    '["email:manager@sla-calculator.local", "slack:#devops"]',
    30
FROM 서비스 s 
WHERE s.이름 = 'API 게이트웨이';

-- 샘플 보고서 템플릿
INSERT INTO 보고서템플릿 (이름, 설명, 템플릿타입, 스케줄, 서비스아이디목록, 수신자목록, 템플릿설정, 생성자아이디)
SELECT 
    '주간 SLA 보고서',
    '모든 서비스의 주간 SLA 현황 보고서',
    'pdf',
    '0 9 * * 1', -- 매주 월요일 오전 9시
    (SELECT json_agg(아이디) FROM 서비스 WHERE 활성여부 = true),
    '["admin@sla-calculator.local", "manager@sla-calculator.local"]',
    '{"include_charts": true, "include_details": true, "language": "ko"}',
    아이디
FROM 사용자 WHERE 이메일 = 'admin@sla-calculator.local';

INSERT INTO 보고서템플릿 (이름, 설명, 템플릿타입, 스케줄, 서비스아이디목록, 수신자목록, 템플릿설정, 생성자아이디)
SELECT 
    '월간 SLA 요약',
    '경영진용 월간 SLA 요약 보고서',
    'excel',
    '0 10 1 * *', -- 매월 1일 오전 10시
    (SELECT json_agg(아이디) FROM 서비스 WHERE 활성여부 = true),
    '["admin@sla-calculator.local", "ceo@company.com"]',
    '{"summary_only": true, "include_trends": true, "language": "ko"}',
    아이디
FROM 사용자 WHERE 이메일 = 'admin@sla-calculator.local';

-- 샘플 SLA 메트릭 데이터 (최근 24시간)
DO $$
DECLARE
    서비스_레코드 RECORD;
    시간_포인트 TIMESTAMP WITH TIME ZONE;
    가용성_값 DECIMAL(5,2);
    응답시간_값 DECIMAL(10,4);
    처리량_값 DECIMAL(10,4);
BEGIN
    -- 각 서비스에 대해 샘플 데이터 생성
    FOR 서비스_레코드 IN SELECT 아이디, 이름, 목표SLA FROM 서비스 WHERE 활성여부 = true LOOP
        -- 최근 24시간 동안 1시간 간격으로 데이터 생성
        FOR i IN 0..23 LOOP
            시간_포인트 := NOW() - (i || ' hours')::INTERVAL;
            
            -- 가용성 메트릭 (목표 SLA 근처에서 약간의 변동)
            가용성_값 := 서비스_레코드.목표SLA + (RANDOM() - 0.5) * 2;
            가용성_값 := GREATEST(95.0, LEAST(100.0, 가용성_값));
            
            INSERT INTO SLA메트릭 (서비스아이디, 메트릭타입, 값, 계산된SLA, 위반여부, 타임스탬프)
            VALUES (
                서비스_레코드.아이디,
                'availability',
                가용성_값,
                가용성_값,
                가용성_값 < 서비스_레코드.목표SLA,
                시간_포인트
            );
            
            -- 응답시간 메트릭 (밀리초 단위, SLA는 목표 시간 내 요청 비율)
            응답시간_값 := 100 + RANDOM() * 400; -- 100-500ms 범위
            INSERT INTO SLA메트릭 (서비스아이디, 메트릭타입, 값, 계산된SLA, 위반여부, 타임스탬프)
            VALUES (
                서비스_레코드.아이디,
                'response_time',
                응답시간_값,
                CASE WHEN 응답시간_값 <= 300 THEN 99.5 ELSE 95.0 END, -- 300ms 이하면 99.5%, 아니면 95%
                응답시간_값 > 300,
                시간_포인트
            );
            
            -- 처리량 메트릭 (초당 요청 수)
            처리량_값 := 50 + RANDOM() * 200; -- 50-250 RPS 범위
            INSERT INTO SLA메트릭 (서비스아이디, 메트릭타입, 값, 계산된SLA, 위반여부, 타임스탬프)
            VALUES (
                서비스_레코드.아이디,
                'throughput',
                처리량_값,
                CASE WHEN 처리량_값 >= 100 THEN 99.0 ELSE 90.0 END, -- 100 RPS 이상이면 99%, 아니면 90%
                처리량_값 < 100,
                시간_포인트
            );
        END LOOP;
    END LOOP;
END $$;

-- 샘플 알림 히스토리 (일부 SLA 위반에 대한 알림 기록)
INSERT INTO 알림히스토리 (알림설정아이디, 서비스아이디, 메시지, 발송채널, 발송상태, 발송일시)
SELECT 
    a.아이디,
    a.서비스아이디,
    s.이름 || ' 서비스의 SLA가 ' || a.임계값 || '% 아래로 떨어졌습니다.',
    'email',
    'sent',
    NOW() - INTERVAL '2 hours'
FROM 알림설정 a
JOIN 서비스 s ON a.서비스아이디 = s.아이디
WHERE a.임계값타입 = 'below'
LIMIT 3;

-- 데이터베이스 통계 업데이트
ANALYZE;