# Kufar Parser Bot

Телеграм-бот для мониторинга новых объявлений Kufar с мультикатегориями и inline-управлением.

## Возможности

- Одновременный мониторинг нескольких категорий.
- Добавление категории:
  - по ID категории (`17010`);
  - по полной ссылке поиска Kufar (бот сохраняет `cat` и дополнительные query-параметры).
- Включение/пауза/удаление категории из меню.
- Выбор региона и района через inline-кнопки.
- `Baseline` для каждой категории (чтобы не сыпались старые объявления).
- Команда `/all` с выбором категории для ручного пролистывания.
- Кэш фото и отправка галереи (до 10 изображений).
- Сохранение списка категорий между перезапусками (`data/targets.json`).

## Команды

- `/start` - краткая справка.
- `/menu` - основная панель управления.
- `/targets` - быстрый список категорий.
- `/set_location` - смена региона/района.
- `/all` - просмотр объявлений по выбранной категории.

## Как получить ID категории (`cat`)

1. Открой на Kufar нужную категорию.
2. Нажми `F12` и перейди во вкладку `Network`.
3. В строке фильтра введи `cat`.
4. Открой любой запрос из списка.
5. В поле `Request URL` найди параметр `?cat=...`.
6. Возьми число после `?cat=` и отправь его боту в `/menu -> ➕ Добавить`.

Пример: если в URL есть `?cat=17010`, то ID категории = `17010`.

## Структура

```text
src/
  app.py                    # запуск и wiring приложения
  config.py                 # env-конфиг
  app_context.py            # runtime state (сессии, категории, cache)
  models/
    search_config.py        # регион/район
    search_target.py        # категория мониторинга
  services/
    kufar_parser.py         # HTTP + парсинг объявлений
    location_manager.py     # загрузка locations.json
    monitoring.py           # фоновый мультипарсинг
    target_storage.py       # сохранение/загрузка категорий
  handlers/
    watchlist.py            # /menu и управление категориями
    location.py             # выбор локации
    ads.py                  # /all и навигация по объявлениям
  keyboards/
    watchlist.py
    ads.py
  states/
    location.py
    target.py
```

## Быстрый старт (PowerShell)

1. Создай venv и активируй:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Установи зависимости:

```powershell
pip install -r requirements.txt
```

3. Создай `.env`:

```powershell
Copy-Item .env.example .env
```

4. Заполни `.env` и запусти:

```powershell
python main.py
```

## Переменные окружения

- `BOT_TOKEN` - токен Telegram-бота.
- `USER_ID` - Telegram user ID, куда отправлять мониторинг.
- `CHECK_INTERVAL` - интервал проверки, сек (по умолчанию `60`).
- `LOCATIONS_FILE` - путь к `locations.json`.
- `TARGETS_FILE` - путь к JSON с категориями (по умолчанию `data/targets.json`).
- `KUFAR_AUTH_TOKEN` - опциональный токен авторизации Kufar.
- `KUFAR_USER_AGENT` - User-Agent для запросов.

## Замечания

- На самом первом запуске (когда `TARGETS_FILE` еще не создан) автоматически добавляется `iPhone (по умолчанию)`.
- Рекомендуется держать `BOT_TOKEN` только в `.env`, не в коде.
