# Деплой tg-check-splitter

> Готово автоматически: код с OpenRouter на Z.AI (glm-4.6v), nginx-конфиг nginx/tg-check-splitter.conf создан.
> Осталось вам: команды ниже (требуют sudo).

> **Обновление с версии до `f1a2b3c4d5e6`.** Миграция добавляет уникальные индексы и
> схлопывает дубли в `session_members`, `item_votes` и `payments` (см. README →
> «Правила целостности»). Она удаляет строки — снимите дамп до `alembic upgrade head`:
> `docker compose exec db pg_dump -U user checksplitter > backup.sql`.
> Миграции прогоняет одноразовый сервис `migrate` — он стартует первым, а `api` и `bot`
> ждут его успешного завершения.

## Шаг 1: токены в .env

Отредактируйте .env в корне репо, замените плейсхолдеры:
- ZAI_API_KEY=ваш_ключ (получить: https://z.ai/manage-apikey)
- BOT_TOKEN=ваш_токен (получить: @BotFather)

Остальное: ZAI_MODEL=glm-4.6v, WEBAPP_URL=https://tg-check-splitter.serge-w.tech

## Шаг 2: nginx + SSL

```bash
sudo cp nginx/tg-check-splitter.conf /etc/nginx/sites-available/tg-check-splitter
sudo ln -sf /etc/nginx/sites-available/tg-check-splitter /etc/nginx/sites-enabled/tg-check-splitter
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d tg-check-splitter.serge-w.tech
curl -I https://tg-check-splitter.serge-w.tech
```

## Шаг 3: docker compose (после токенов!)

```bash
docker compose up -d --build
docker compose ps -a          # -a обязательно: migrate уже вышел с кодом 0
docker compose logs migrate api bot --tail=50
```

## Шаг 4: BotFather

@BotFather → /mybots → serge_w_check_splitter_bot → Menu Button → https://tg-check-splitter.serge-w.tech

## Если ошибки

```bash
sudo journalctl -u nginx -n 50 --no-pager
docker compose logs migrate api bot --tail=50
sudo certbot certificates
docker compose up -d --build --force-recreate
```
