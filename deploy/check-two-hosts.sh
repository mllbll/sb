#!/usr/bin/env bash
# Проверка двухузлового развёртывания REU Secure System.
#
# Использование:
#   ./deploy/check-two-hosts.sh              # проверка с любой машины в LAN
#   ./deploy/check-two-hosts.sh --local      # + статус docker compose на этом ПК
#
# Переменные (опционально):
#   HOST10=192.168.1.10  HOST20=192.168.1.20
#   CROWD_PORT=8001  FIGHT_PORT=8002  FALL_PORT=8003  FRONTEND_PORT=80

set -euo pipefail

HOST10="${HOST10:-192.168.1.10}"
HOST20="${HOST20:-192.168.1.20}"
CROWD_PORT="${CROWD_PORT:-8001}"
FIGHT_PORT="${FIGHT_PORT:-8002}"
FALL_PORT="${FALL_PORT:-8003}"
FRONTEND_PORT="${FRONTEND_PORT:-80}"

LOCAL_MODE=false
if [[ "${1:-}" == "--local" ]]; then
  LOCAL_MODE=true
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok=0
fail=0
warn=0

log_ok()   { echo -e "${GREEN}  OK${NC}   $*"; ((ok++)) || true; }
log_fail() { echo -e "${RED}  FAIL${NC} $*"; ((fail++)) || true; }
log_warn() { echo -e "${YELLOW}  WARN${NC} $*"; ((warn++)) || true; }

section() {
  echo ""
  echo "=== $* ==="
}

# --- TCP port (bash /dev/tcp) ---
check_tcp() {
  local host="$1" port="$2" label="$3"
  if timeout 3 bash -c "echo >/dev/tcp/${host}/${port}" 2>/dev/null; then
    log_ok "${label}: ${host}:${port} доступен"
    return 0
  fi
  log_fail "${label}: ${host}:${port} недоступен"
  return 1
}

# --- HTTP GET, ожидаем 2xx ---
check_http() {
  local url="$1" label="$2"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$url" 2>/dev/null || echo "000")
  if [[ "$code" =~ ^2 ]]; then
    log_ok "${label}: ${url} (HTTP ${code})"
    return 0
  fi
  if [[ "$code" == "000" ]]; then
    log_fail "${label}: ${url} — нет ответа"
  else
    log_fail "${label}: ${url} (HTTP ${code})"
  fi
  return 1
}

# --- HTTP через nginx на .20 (health paths) ---
check_http_loose() {
  local url="$1" label="$2"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$url" 2>/dev/null || echo "000")
  if [[ "$code" =~ ^2 ]]; then
    log_ok "${label}: ${url} (HTTP ${code})"
    return 0
  fi
  log_fail "${label}: ${url} (HTTP ${code})"
  return 1
}

detect_local_ip() {
  local ip=""
  if command -v ip &>/dev/null; then
    ip=$(ip -4 route get "$HOST10" 2>/dev/null | awk '{for (i=1;i<=NF;i++) if ($i=="src") print $(i+1)}' | head -1)
  elif command -v ifconfig &>/dev/null; then
    ip=$(ifconfig 2>/dev/null | awk '/inet / && $2 != "127.0.0.1" {print $2; exit}' | sed 's/addr://')
  fi
  echo "${ip:-unknown}"
}

guess_role() {
  local my_ip="$1"
  if [[ "$my_ip" == "$HOST10" ]]; then
    echo "host10 (${HOST10})"
  elif [[ "$my_ip" == "$HOST20" ]]; then
    echo "host20 (${HOST20})"
  else
    echo "клиент в LAN (мой IP: ${my_ip})"
  fi
}

check_docker_local() {
  local compose_file="$1" name="$2"
  if ! command -v docker &>/dev/null; then
    log_warn "${name}: docker не установлен — пропуск локальной проверки"
    return
  fi
  if [[ ! -f "$compose_file" ]]; then
    log_warn "${name}: не найден ${compose_file}"
    return
  fi
  section "Docker Compose — ${name}"
  if docker compose -f "$compose_file" ps --format json 2>/dev/null | grep -q '"State":"running"'; then
    docker compose -f "$compose_file" ps 2>/dev/null || true
    local unhealthy
    unhealthy=$(docker compose -f "$compose_file" ps 2>/dev/null | grep -E 'unhealthy|Exit|exited' || true)
    if [[ -n "$unhealthy" ]]; then
      log_warn "${name}: есть остановленные или unhealthy контейнеры (см. выше)"
    else
      log_ok "${name}: контейнеры запущены"
    fi
  else
    log_warn "${name}: compose не запущен или нет running-контейнеров"
    docker compose -f "$compose_file" ps 2>/dev/null || log_fail "${name}: docker compose ps недоступен"
  fi
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_HOST10="${REPO_ROOT}/deploy/host10/docker-compose.yml"
COMPOSE_HOST20="${REPO_ROOT}/deploy/host20/docker-compose.yml"

MY_IP=$(detect_local_ip)
ROLE=$(guess_role "$MY_IP")

section "Конфигурация"
echo "  HOST10 (crowd+fight): ${HOST10}"
echo "  HOST20 (fall+UI):     ${HOST20}"
echo "  Эта машина:           ${ROLE}"

section "Сеть — порты на ${HOST10}"
check_tcp "$HOST10" "$CROWD_PORT" "crowd-api"
check_tcp "$HOST10" "$FIGHT_PORT" "fight-api"

section "Сеть — порты на ${HOST20}"
check_tcp "$HOST20" "$FRONTEND_PORT" "frontend (nginx)"
check_tcp "$HOST20" "$FALL_PORT" "fall-api (прямой доступ)"

section "API health — напрямую на ${HOST10}"
check_http "http://${HOST10}:${CROWD_PORT}/health" "crowd-api /health"
check_http "http://${HOST10}:${FIGHT_PORT}/health" "fight-api /health"

section "API health — напрямую на ${HOST20}"
check_http "http://${HOST20}:${FALL_PORT}/health" "fall-api /health"

section "Прокси через nginx на ${HOST20}"
check_http_loose "http://${HOST20}:${FRONTEND_PORT}/health/crowd" "nginx → crowd"
check_http_loose "http://${HOST20}:${FRONTEND_PORT}/health/fight" "nginx → fight"
check_http_loose "http://${HOST20}:${FRONTEND_PORT}/health/fall" "nginx → fall"

section "Точка входа оператора"
check_http_loose "http://${HOST20}:${FRONTEND_PORT}/" "дашборд (index.html)"

if [[ "$LOCAL_MODE" == true ]]; then
  if [[ "$MY_IP" == "$HOST10" ]]; then
    check_docker_local "$COMPOSE_HOST10" "host10"
  elif [[ "$MY_IP" == "$HOST20" ]]; then
    check_docker_local "$COMPOSE_HOST20" "host20"
  else
    check_docker_local "$COMPOSE_HOST10" "host10 (если запущен здесь)"
    check_docker_local "$COMPOSE_HOST20" "host20 (если запущен здесь)"
  fi
fi

section "Итог"
echo "  Успешно: ${ok}  Предупреждений: ${warn}  Ошибок: ${fail}"

if [[ "$fail" -gt 0 ]]; then
  echo ""
  echo "Подсказки:"
  echo "  • Сначала запустите host10: docker compose -f deploy/host10/docker-compose.yml up -d"
  echo "  • Затем host20:           docker compose -f deploy/host20/docker-compose.yml up --build -d"
  echo "  • На ${HOST10} откройте firewall для портов ${CROWD_PORT}, ${FIGHT_PORT}"
  echo "  • Проверьте nginx на ${HOST20}: deploy/host20/nginx.conf → ${HOST10}"
  exit 1
fi

if [[ "$warn" -gt 0 ]]; then
  exit 0
fi

echo -e "${GREEN}Все проверки пройдены.${NC}"
exit 0
