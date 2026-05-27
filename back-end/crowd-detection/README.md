# REU Secure — Crowd Detection

Система видеоаналитики для подсчёта людей и обнаружения скоплений в реальном времени. Используется YOLO для детекции, PostgreSQL для хранения, FastAPI + WebSocket для раздачи данных на фронт.

## Архитектура

Три Docker-контейнера:

| Контейнер | Что делает |
|-----------|-----------|
| `migrate` | Запускает Alembic-миграции и завершается. Стартует до `api` и `model`. |
| `api` | FastAPI: REST-эндпоинты со статистикой + WebSocket для реального времени. |
| `model` | YOLO-инференс по RTSP-потокам с двух камер, пишет результаты в БД. |

`model` и `api` не связаны напрямую — общаются только через PostgreSQL.

## Зоны

Каждая камера соответствует зоне на фронте:

| zone id | camera_id | Название | Макс. вместимость |
|---------|-----------|----------|-------------------|
| z1 | lift | Главный вход | 80 |
| z2 | hall | Холл | 300 |

Конфигурация зон — в `keys/secrets.json` в поле `zones`. Если добавляется новая камера, нужно добавить источник в `sources` и зону в `zones`.

## Настройка

Все параметры хранятся в одном файле `keys/secrets.json`. Шаблон:

```json
{
  "sources": [
    {"id": "lift", "rtsp_url": "rtsp://user:pass@ip:554/live/main"},
    {"id": "hall", "rtsp_url": "rtsp://user:pass@ip:554/live/main"}
  ],

  "zones": [
    {"id": "z1", "camera_id": "lift", "name": "Главный вход", "max_capacity": 80},
    {"id": "z2", "camera_id": "hall", "name": "Холл", "max_capacity": 300}
  ],

  "ws_broadcast_interval_sec": 3,

  "DB_HOST": "localhost",
  "DB_NAME": "crowd_detection",
  "DB_USER": "youruser",
  "DB_PASSWORD": "yourpassword",
  "PORT": 5432,

  "inference_enabled": true,
  "model_path": "models_yolo/yolo11x.pt",
  "yolo_conf": 0.35,

  "crowd_min_people": 5,
  "crowd_iou_threshold": 0.0,
  "crowd_overlap_mode": "adaptive",
  "crowd_adaptive_dist_mult": 1.2,
  "crowd_center_dist_fraction": 0.06,
  "crowd_roi_mode": "center",

  "crowd_timeout_sec": 2,
  "write_interval_sec": 30,

  "roi_box": [0, 0, 1920, 1080],
  "roi_base_w": 1920,
  "roi_base_h": 1080,

  "output_dir": "images",
  "show": "0",
  "log_level": "INFO"
}
```

Файл `keys/secrets.json` монтируется в оба контейнера через volume. Не коммитить в git.

## Деплой

### Требования

- Docker Engine 24+
- Docker Compose v2 (поддержка `service_completed_successfully`)
- PostgreSQL — внешняя БД (указывается в `secrets.json`)
- Веса модели: файл `model/models_yolo/yolo11x.pt` должен лежать на сервере

### Запуск

```bash
git clone <repo>
cd crowd-detection

# Заполнить конфиг
cp keys/secrets.json.example keys/secrets.json
nano keys/secrets.json

docker compose up --build -d
```

При первом запуске контейнер `migrate` автоматически создаст таблицу `crowd_data` и индексы, после чего завершится. `api` и `model` стартуют только после его успешного завершения.

### Миграции вручную (без Docker)

Если нужно накатить миграции отдельно, например перед деплоем:

```bash
pip install -r requirements-migrations.txt
alembic upgrade head
```

Для отката:

```bash
alembic downgrade -1
```

### Обновление

```bash
git pull
docker compose up --build -d
```

При обновлении контейнер `migrate` снова запустится первым и применит новые миграции, если они есть.

## API

Base URL: `http://host:8000`

Документация (Swagger): `http://host:8000/docs`

### WebSocket

**Подключение:** `ws://host:8000/ws/crowd`

При подключении сразу отдаётся текущее состояние, затем обновления каждые `ws_broadcast_interval_sec` секунд (по умолчанию 3).

Формат сообщения:

```json
{
  "type": "crowd.update",
  "payload": {
    "total": 235,
    "zones": [
      {"id": "z1", "current": 48},
      {"id": "z2", "current": 187}
    ]
  }
}
```

`total` — сумма по всем зонам. Порог для подсветки зоны красным (`max_capacity`) хранится в `zones` в `secrets.json`.

Пример подключения на JS:

```js
const ws = new WebSocket("ws://localhost:8000/ws/crowd");

ws.onmessage = (e) => {
  const { type, payload } = JSON.parse(e.data);
  if (type === "crowd.update") {
    console.log("Всего:", payload.total);
    console.log("Зоны:", payload.zones);
  }
};
```

### REST — статистика

Все эндпоинты возвращают массив объектов с почасовой агрегацией.

| Метод | Путь | Параметры |
|-------|------|-----------|
| GET | `/api/stats/day` | `date=YYYY-MM-DD` (опционально, по умолчанию сегодня) |
| GET | `/api/stats/week` | — |
| GET | `/api/stats/month` | — |
| GET | `/api/stats/year` | — |
| GET | `/api/stats/month/custom` | `month=1..12&year=YYYY` |
| GET | `/api/stats/year/custom` | `year=YYYY` |

Формат ответа:

```json
[
  {"hour": 9,  "average_people": 48.3, "crowd_count": 0.0},
  {"hour": 10, "average_people": 112.7, "crowd_count": 1.2},
  {"hour": 11, "average_people": 98.1, "crowd_count": 0.8}
]
```

`crowd_count` — среднее количество зафиксированных скоплений за час. Скоплением считается группа от 5 человек (настраивается через `crowd_min_people`).

## Схема БД

Одна таблица `crowd_data`:

| Колонка | Тип | Описание |
|---------|-----|----------|
| id | BIGSERIAL | PK |
| camera_id | TEXT | Идентификатор камеры (`lift`, `hall`) |
| people_count | INT | Количество людей в зоне в момент записи |
| crowd_count | INT | Количество скоплений |
| time | TIMESTAMPTZ | Время записи (московское время) |
| filename | TEXT | Путь к сохранённому кадру, если было скопление |

Запись в БД происходит двумя способами:
- **Периодически** — каждые `write_interval_sec` секунд (по умолчанию 30)
- **По событию** — когда обнаружено скопление, кадр сохраняется в `images/` и фиксируется в БД

## Структура проекта

```
.
├── api/
│   ├── main.py              — FastAPI app, подключение роутеров
│   ├── websocket.py         — WebSocket endpoint и broadcast loop
│   ├── stats_endpoints.py   — REST эндпоинты статистики
│   ├── db_conn.py           — подключение к PostgreSQL
│   ├── db_crud.py           — SQL-запросы для статистики
│   └── response.py          — Pydantic-модель ответа
├── model/
│   ├── detection.py         — мульти-камерный пайплайн (CameraWorker)
│   ├── config.py            — загрузка secrets.json
│   ├── utils.py             — алгоритм поиска скоплений (DFS)
│   ├── roi.py               — масштабирование ROI под разрешение камеры
│   ├── write_to_db.py       — запись в PostgreSQL
│   └── models_yolo/         — веса YOLO (не в git)
├── migrations/
│   ├── env.py               — Alembic env, читает secrets.json
│   ├── script.py.mako       — шаблон для новых ревизий
│   └── versions/
│       └── 0001_create_crowd_data.py
├── keys/
│   └── secrets.json         — все параметры (не в git)
├── alembic.ini
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.model
├── requirements-api.txt
├── requirements-model.txt
└── requirements-migrations.txt
```

## Зависимости

| Файл | Используется |
|------|-------------|
| `requirements-api.txt` | контейнер `api`, контейнер `migrate` |
| `requirements-model.txt` | контейнер `model` |
| `requirements-migrations.txt` | ручной запуск миграций вне Docker |
