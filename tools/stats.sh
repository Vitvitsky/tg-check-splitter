#!/usr/bin/env bash
# Статистика по боту check-splitter.
# Запуск: ./tools/stats.sh <команда>
#
# Команды:
#   dau [ДНЕЙ]      — уникальные активные пользователи по дням (по умолчанию 14)
#   mau             — MAU/WAU/DAU и отношение DAU/MAU (липкость)
#   funnel [ДНЕЙ]   — воронка: сессия -> распознано -> проголосовали -> рассчитано
#   retention       — возврат пользователей по месяцам
#   money           — платежи, Stars, конверсия в платящих
#   health          — размер БД, объём фото, самые тяжёлые таблицы
#   all             — всё сразу
#
# Активность считается по фактическим действиям, а не по открытию приложения:
# создание сессии, присоединение, голос, платёж. Отдельной таблицы событий нет —
# см. docs/BACKLOG.md, пункт про user_activity, если понадобится точность выше.

set -euo pipefail

PSQL_CMD="${PSQL_CMD:-docker compose exec -T db psql -U user -d checksplitter}"

run_sql() {
  $PSQL_CMD -v ON_ERROR_STOP=1 -c "$1"
}

# Все действия пользователей в одном месте. Используется почти всеми отчётами.
ACTIVITY_CTE="
WITH activity AS (
    SELECT admin_tg_id AS user_tg_id, created_at AS at FROM sessions
    UNION ALL SELECT user_tg_id, joined_at   FROM session_members
    UNION ALL SELECT user_tg_id, created_at  FROM item_votes
    UNION ALL SELECT user_tg_id, created_at  FROM payments
)"

cmd_dau() {
  local days="${1:-14}"
  echo "== Активные пользователи по дням (последние ${days}) =="
  run_sql "$ACTIVITY_CTE
    SELECT at::date AS \"день\",
           count(DISTINCT user_tg_id) AS \"активных\",
           count(*) AS \"действий\"
    FROM activity
    WHERE at >= now() - interval '${days} days'
    GROUP BY 1 ORDER BY 1 DESC;"
}

cmd_mau() {
  echo "== Липкость =="
  run_sql "$ACTIVITY_CTE
    SELECT
      count(DISTINCT user_tg_id) FILTER (WHERE at >= now() - interval '1 day')   AS \"DAU\",
      count(DISTINCT user_tg_id) FILTER (WHERE at >= now() - interval '7 days')  AS \"WAU\",
      count(DISTINCT user_tg_id) FILTER (WHERE at >= now() - interval '30 days') AS \"MAU\",
      count(DISTINCT user_tg_id)                                                 AS \"всего\",
      round(100.0 * NULLIF(count(DISTINCT user_tg_id) FILTER (WHERE at >= now() - interval '1 day'), 0)
            / NULLIF(count(DISTINCT user_tg_id) FILTER (WHERE at >= now() - interval '30 days'), 0), 1)
        AS \"DAU/MAU %\"
    FROM activity;"
}

cmd_funnel() {
  local days="${1:-30}"
  echo "== Воронка (сессии за последние ${days} дней) =="
  # Каждый шаг — надмножество следующего, поэтому проценты читаются сверху вниз.
  run_sql "
    WITH s AS (
      SELECT id, status,
             EXISTS (SELECT 1 FROM session_photos p WHERE p.session_id = s.id)  AS has_photo,
             EXISTS (SELECT 1 FROM session_items  i WHERE i.session_id = s.id)  AS has_items,
             EXISTS (SELECT 1 FROM item_votes v JOIN session_items i ON i.id = v.item_id
                     WHERE i.session_id = s.id)                                 AS has_votes,
             (SELECT count(*) FROM session_members m WHERE m.session_id = s.id) AS members
      FROM sessions s WHERE created_at >= now() - interval '${days} days'
    )
    SELECT 'создано сессий' AS \"шаг\", count(*) AS \"штук\", '100%' AS \"доля\" FROM s
    UNION ALL SELECT 'загружено фото', count(*) FILTER (WHERE has_photo),
                     round(100.0*count(*) FILTER (WHERE has_photo)/NULLIF(count(*),0))||'%' FROM s
    UNION ALL SELECT 'распознаны позиции', count(*) FILTER (WHERE has_items),
                     round(100.0*count(*) FILTER (WHERE has_items)/NULLIF(count(*),0))||'%' FROM s
    UNION ALL SELECT 'пришёл кто-то ещё', count(*) FILTER (WHERE members > 1),
                     round(100.0*count(*) FILTER (WHERE members > 1)/NULLIF(count(*),0))||'%' FROM s
    UNION ALL SELECT 'начали голосовать', count(*) FILTER (WHERE has_votes),
                     round(100.0*count(*) FILTER (WHERE has_votes)/NULLIF(count(*),0))||'%' FROM s
    UNION ALL SELECT 'рассчитано', count(*) FILTER (WHERE status = 'settled'),
                     round(100.0*count(*) FILTER (WHERE status='settled')/NULLIF(count(*),0))||'%' FROM s;"

  echo "== Средний чек по размеру компании =="
  run_sql "
    SELECT (SELECT count(*) FROM session_members m WHERE m.session_id = s.id) AS \"участников\",
           count(*) AS \"сессий\",
           round(avg((SELECT coalesce(sum(price),0) FROM session_items i WHERE i.session_id = s.id))) AS \"средний чек\"
    FROM sessions s
    WHERE created_at >= now() - interval '${days} days'
    GROUP BY 1 ORDER BY 1;"
}

cmd_retention() {
  echo "== Возврат по месяцам (когорта = месяц первого действия) =="
  run_sql "$ACTIVITY_CTE,
    first_seen AS (
      SELECT user_tg_id, date_trunc('month', min(at)) AS cohort FROM activity GROUP BY 1
    ),
    months AS (
      SELECT DISTINCT user_tg_id, date_trunc('month', at) AS m FROM activity
    )
    SELECT to_char(f.cohort, 'YYYY-MM') AS \"когорта\",
           count(DISTINCT f.user_tg_id) AS \"пришло\",
           count(DISTINCT m.user_tg_id) FILTER (
             WHERE m.m = f.cohort + interval '1 month') AS \"вернулись через мес\"
    FROM first_seen f LEFT JOIN months m USING (user_tg_id)
    GROUP BY 1, f.cohort ORDER BY f.cohort DESC;"
}

cmd_money() {
  echo "== Платежи =="
  run_sql "
    SELECT count(*) AS \"платежей\",
           count(DISTINCT user_tg_id) AS \"платящих\",
           coalesce(sum(stars_amount),0) AS \"всего Stars\",
           coalesce(round(avg(stars_amount)),0) AS \"средний платёж\"
    FROM payments;"

  echo "== Квоты: кто упирается в лимит =="
  run_sql "
    SELECT count(*) AS \"пользователей с квотой\",
           count(*) FILTER (WHERE free_scans_used >= 3) AS \"исчерпали бесплатные\",
           count(*) FILTER (WHERE paid_scans > 0) AS \"есть платные сканы\",
           coalesce(sum(free_scans_used),0) AS \"бесплатных сканов всего\"
    FROM user_quotas;"
}

cmd_health() {
  echo "== Размер БД =="
  run_sql "
    SELECT relname AS \"таблица\",
           to_char(n_live_tup, '999G999G999') AS \"строк\",
           pg_size_pretty(pg_total_relation_size(relid)) AS \"размер\"
    FROM pg_stat_user_tables ORDER BY pg_total_relation_size(relid) DESC;"

  echo "== Фото чеков (должны обнуляться после распознавания) =="
  run_sql "
    SELECT count(*) AS \"строк с фото\",
           count(*) FILTER (WHERE data IS NOT NULL) AS \"с байтами\",
           pg_size_pretty(coalesce(sum(octet_length(data)),0)) AS \"занято байтами\"
    FROM session_photos;"
}

case "${1:-help}" in
  dau)       cmd_dau "${2:-14}" ;;
  mau)       cmd_mau ;;
  funnel)    cmd_funnel "${2:-30}" ;;
  retention) cmd_retention ;;
  money)     cmd_money ;;
  health)    cmd_health ;;
  all)       cmd_mau; cmd_dau 14; cmd_funnel 30; cmd_retention; cmd_money; cmd_health ;;
  *)
    sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'
    ;;
esac
