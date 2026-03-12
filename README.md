# GlassSelling

Проект подготовлен под деплой одним контейнером приложения и отдельным Postgres через `docker compose`.

## Быстрый старт

1. Скопируй `.env.example` в `.env`.
2. Заполни секреты, SMTP и параметры ЮKassa.
3. Для деплоя в Docker оставь `DB_HOST=db`.
4. Собери и запусти:

```bash
docker compose up --build -d
```

5. Проверь healthcheck:

```bash
curl http://127.0.0.1:8000/healthz
```

Сайт и API будут доступны на одном домене через порт `8000`. Фронтенд уже встраивается в backend-образ, поэтому отдельный nginx для раздачи SPA не обязателен.

## Что важно перед продом

- Выставить `COOKIE_SECURE=true` и запускать только за `https`.
- Указать `YOOKASSA_RETURN_URL` на боевой домен, например `https://example.com/basket`.
- Указать webhook ЮKassa: `https://example.com/payments/yookassa/webhook/<твой токен>`.
- Для отдельного фронтенд-домена заполни `BACKEND_CORS_ORIGINS` через запятую.
- Для боевого запуска с онлайн-оплатой ещё нужен отдельный этап с чеками и 54-ФЗ.
