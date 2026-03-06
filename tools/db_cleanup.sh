#!/usr/bin/env bash
# Утилита для очистки данных в БД check-splitter.
# Запуск: ./tools/db_cleanup.sh <команда> [аргументы]
#
# Команды:
#   reset-quota [USER_TG_ID]   — сбросить счётчик сканирований (всем или конкретному)
#   clear-history [USER_TG_ID] — удалить settled-сессии (все или конкретного админа)
#   clear-all [USER_TG_ID]     — удалить ВСЕ сессии (все или конкретного админа)
#   show-quotas                — показать текущие квоты
#   show-sessions              — показать список сессий

set -euo pipefail

# Подключение: через docker compose или напрямую
PSQL_CMD="${PSQL_CMD:-docker compose exec -T db psql -U user -d checksplitter}"

run_sql() {
  $PSQL_CMD -c "$1"
}

case "${1:-help}" in
  reset-quota)
    if [ -n "${2:-}" ]; then
      echo "Сброс счётчика сканирований для user_tg_id=$2..."
      run_sql "UPDATE user_quotas SET free_scans_used = 0 WHERE user_tg_id = $2;"
    else
      echo "Сброс счётчика сканирований для ВСЕХ пользователей..."
      run_sql "UPDATE user_quotas SET free_scans_used = 0;"
    fi
    echo "Готово."
    ;;

  clear-history)
    if [ -n "${2:-}" ]; then
      echo "Удаление settled-сессий для admin_tg_id=$2..."
      run_sql "DELETE FROM sessions WHERE status = 'settled' AND admin_tg_id = $2;"
    else
      echo "Удаление ВСЕХ settled-сессий..."
      run_sql "DELETE FROM sessions WHERE status = 'settled';"
    fi
    echo "Готово."
    ;;

  clear-all)
    if [ -n "${2:-}" ]; then
      echo "Удаление ВСЕХ сессий для admin_tg_id=$2..."
      run_sql "DELETE FROM sessions WHERE admin_tg_id = $2;"
    else
      echo "Удаление ВСЕХ сессий..."
      run_sql "DELETE FROM sessions;"
    fi
    echo "Готово."
    ;;

  show-quotas)
    run_sql "SELECT user_tg_id, free_scans_used, paid_scans, reset_at FROM user_quotas ORDER BY user_tg_id;"
    ;;

  show-sessions)
    run_sql "SELECT id, admin_tg_id, invite_code, status, created_at FROM sessions ORDER BY created_at DESC LIMIT 20;"
    ;;

  *)
    echo "Использование: $0 <команда> [USER_TG_ID]"
    echo ""
    echo "Команды:"
    echo "  reset-quota [ID]    Сбросить счётчик сканирований"
    echo "  clear-history [ID]  Удалить завершённые (settled) сессии"
    echo "  clear-all [ID]      Удалить ВСЕ сессии"
    echo "  show-quotas         Показать квоты пользователей"
    echo "  show-sessions       Показать последние сессии"
    echo ""
    echo "ID — Telegram user ID (необязательно, без него — для всех)"
    echo ""
    echo "Переменная PSQL_CMD переопределяет команду подключения к БД."
    echo "По умолчанию: docker compose exec -T db psql -U user -d checksplitter"
    ;;
esac
