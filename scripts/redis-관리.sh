#!/bin/bash
# Redis 관리 및 모니터링 스크립트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Redis 연결 정보
REDIS_HOST=${REDIS_HOST:-"localhost"}
REDIS_PORT=${REDIS_PORT:-"6379"}
REDIS_PASSWORD=${REDIS_PASSWORD:-""}

# Redis CLI 명령어 구성
if [ -n "$REDIS_PASSWORD" ]; then
    REDIS_CLI="redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD"
else
    REDIS_CLI="redis-cli -h $REDIS_HOST -p $REDIS_PORT"
fi

# 함수: 도움말 출력
show_help() {
    echo -e "${BLUE}Redis 관리 스크립트${NC}"
    echo ""
    echo "사용법: $0 [명령어]"
    echo ""
    echo "명령어:"
    echo "  status      - Redis 서버 상태 확인"
    echo "  info        - Redis 서버 정보 출력"
    echo "  memory      - 메모리 사용량 확인"
    echo "  keys        - 키 통계 확인"
    echo "  slowlog     - 슬로우 로그 확인"
    echo "  flush-cache - 캐시 데이터 삭제 (주의!)"
    echo "  backup      - 데이터 백업"
    echo "  monitor     - 실시간 모니터링"
    echo "  help        - 이 도움말 출력"
}

# 함수: Redis 연결 테스트
test_connection() {
    echo -e "${YELLOW}Redis 연결 테스트 중...${NC}"
    if $REDIS_CLI ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis 서버에 성공적으로 연결되었습니다${NC}"
        return 0
    else
        echo -e "${RED}✗ Redis 서버에 연결할 수 없습니다${NC}"
        return 1
    fi
}

# 함수: Redis 상태 확인
check_status() {
    echo -e "${BLUE}=== Redis 서버 상태 ===${NC}"
    
    if ! test_connection; then
        return 1
    fi
    
    # 기본 정보
    echo -e "\n${YELLOW}기본 정보:${NC}"
    $REDIS_CLI info server | grep -E "(redis_version|os|arch|process_id|uptime_in_seconds)" | while IFS=':' read -r key value; do
        case $key in
            redis_version) echo "  Redis 버전: $value" ;;
            os) echo "  운영체제: $value" ;;
            arch_bits) echo "  아키텍처: ${value}bit" ;;
            process_id) echo "  프로세스 ID: $value" ;;
            uptime_in_seconds) 
                hours=$((value / 3600))
                minutes=$(((value % 3600) / 60))
                echo "  가동 시간: ${hours}시간 ${minutes}분"
                ;;
        esac
    done
    
    # 연결 정보
    echo -e "\n${YELLOW}연결 정보:${NC}"
    $REDIS_CLI info clients | grep -E "(connected_clients|blocked_clients)" | while IFS=':' read -r key value; do
        case $key in
            connected_clients) echo "  연결된 클라이언트: $value" ;;
            blocked_clients) echo "  대기 중인 클라이언트: $value" ;;
        esac
    done
}

# 함수: 메모리 사용량 확인
check_memory() {
    echo -e "${BLUE}=== Redis 메모리 사용량 ===${NC}"
    
    if ! test_connection; then
        return 1
    fi
    
    $REDIS_CLI info memory | grep -E "(used_memory_human|used_memory_peak_human|maxmemory_human|mem_fragmentation_ratio)" | while IFS=':' read -r key value; do
        case $key in
            used_memory_human) echo "  현재 사용 메모리: $value" ;;
            used_memory_peak_human) echo "  최대 사용 메모리: $value" ;;
            maxmemory_human) echo "  최대 허용 메모리: $value" ;;
            mem_fragmentation_ratio) echo "  메모리 단편화 비율: $value" ;;
        esac
    done
    
    # 메모리 정책 확인
    echo -e "\n${YELLOW}메모리 정책:${NC}"
    maxmemory_policy=$($REDIS_CLI config get maxmemory-policy | tail -n 1)
    echo "  메모리 정책: $maxmemory_policy"
}

# 함수: 키 통계 확인
check_keys() {
    echo -e "${BLUE}=== Redis 키 통계 ===${NC}"
    
    if ! test_connection; then
        return 1
    fi
    
    # 데이터베이스별 키 개수
    echo -e "${YELLOW}데이터베이스별 키 개수:${NC}"
    $REDIS_CLI info keyspace | grep "^db" | while IFS=':' read -r db info; do
        keys=$(echo $info | sed 's/.*keys=\([0-9]*\).*/\1/')
        expires=$(echo $info | sed 's/.*expires=\([0-9]*\).*/\1/')
        echo "  $db: $keys개 키 (만료 예정: $expires개)"
    done
    
    # SLA Calculator 관련 키 통계
    echo -e "\n${YELLOW}SLA Calculator 키 통계:${NC}"
    for namespace in "metrics" "sessions" "alerts" "reports" "users" "services" "settings"; do
        pattern="sla_calc:${namespace}:*"
        count=$($REDIS_CLI eval "return #redis.call('keys', ARGV[1])" 0 "$pattern" 2>/dev/null || echo "0")
        echo "  $namespace: $count개"
    done
}

# 함수: 슬로우 로그 확인
check_slowlog() {
    echo -e "${BLUE}=== Redis 슬로우 로그 ===${NC}"
    
    if ! test_connection; then
        return 1
    fi
    
    slowlog_len=$($REDIS_CLI slowlog len)
    echo "슬로우 로그 항목 수: $slowlog_len"
    
    if [ "$slowlog_len" -gt 0 ]; then
        echo -e "\n${YELLOW}최근 슬로우 쿼리 (상위 10개):${NC}"
        $REDIS_CLI slowlog get 10 | grep -E "^\d+\)" -A 3
    else
        echo -e "${GREEN}슬로우 쿼리가 없습니다${NC}"
    fi
}

# 함수: 캐시 데이터 삭제
flush_cache() {
    echo -e "${RED}경고: 이 작업은 모든 캐시 데이터를 삭제합니다!${NC}"
    read -p "정말로 계속하시겠습니까? (yes/no): " confirm
    
    if [ "$confirm" = "yes" ]; then
        echo -e "${YELLOW}캐시 데이터 삭제 중...${NC}"
        $REDIS_CLI flushall
        echo -e "${GREEN}✓ 캐시 데이터가 삭제되었습니다${NC}"
    else
        echo -e "${BLUE}작업이 취소되었습니다${NC}"
    fi
}

# 함수: 데이터 백업
backup_data() {
    echo -e "${BLUE}=== Redis 데이터 백업 ===${NC}"
    
    if ! test_connection; then
        return 1
    fi
    
    backup_dir="./backups/redis"
    mkdir -p "$backup_dir"
    
    timestamp=$(date +"%Y%m%d_%H%M%S")
    backup_file="$backup_dir/redis_backup_$timestamp.rdb"
    
    echo -e "${YELLOW}백업 생성 중...${NC}"
    $REDIS_CLI --rdb "$backup_file"
    
    if [ -f "$backup_file" ]; then
        echo -e "${GREEN}✓ 백업이 완료되었습니다: $backup_file${NC}"
        ls -lh "$backup_file"
    else
        echo -e "${RED}✗ 백업 생성에 실패했습니다${NC}"
    fi
}

# 함수: 실시간 모니터링
monitor_redis() {
    echo -e "${BLUE}=== Redis 실시간 모니터링 ===${NC}"
    echo -e "${YELLOW}Ctrl+C로 종료하세요${NC}"
    echo ""
    
    if ! test_connection; then
        return 1
    fi
    
    $REDIS_CLI monitor
}

# 메인 로직
case "${1:-help}" in
    status)
        check_status
        ;;
    info)
        check_status
        echo ""
        check_memory
        echo ""
        check_keys
        ;;
    memory)
        check_memory
        ;;
    keys)
        check_keys
        ;;
    slowlog)
        check_slowlog
        ;;
    flush-cache)
        flush_cache
        ;;
    backup)
        backup_data
        ;;
    monitor)
        monitor_redis
        ;;
    help|*)
        show_help
        ;;
esac