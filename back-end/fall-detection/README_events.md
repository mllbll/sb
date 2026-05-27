# fight3d Events API (PostgreSQL + FastAPI)

Этот модуль хранит **только доменные данные**: локации, камеры и события `fight`.

- Системные метрики (CPU/GPU/FPS/дропы) **в БД не сохраняем** — только логируем.
- БД: PostgreSQL
- ORM: SQLAlchemy 2.0 async + asyncpg
- Миграции: Alembic
- API: FastAPI

## Быстрый запуск (Docker Compose)

Поднимет Postgres, применит миграции Alembic и запустит API.

1) Создай конфиг:

```bash
cp config.yaml.example config.yaml
```

Проверь `postgres.url` (в docker-compose по умолчанию это `db:5432`).

```bash
docker-compose up --build db api
```

Healthcheck:
```bash
curl -s http://localhost:8000/health
```

### Inference (опционально)

Inference тоже запускается из того же `config.yaml` (секция `cameras[]` + `inference.*`):

```bash
docker-compose up --build infer
```

## Локальный запуск без Docker

### 1) Запуск PostgreSQL (docker)
```bash
docker run --name fight3d-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=fight3d \
  -p 5433:5432 \
  -d postgres:16
```

### 2) config.yaml (рекомендуется)
Скопируй `config.yaml.example` → `config.yaml` и поменяй `postgres.url` на локальный Postgres.

Пример:
```yaml
postgres:
  url: "postgresql+asyncpg://postgres:postgres@localhost:5432/fight3d"
```

### 3) Зависимости
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

### 4) Миграции
```bash
source .venv/bin/activate
export FIGHT3D_CONFIG=./config.yaml

alembic upgrade head
```

### 5) Запуск API
```bash
source .venv/bin/activate
export FIGHT3D_CONFIG=./config.yaml

python -m fight3d.api.serve
```

## Примеры curl

### Создать локацию
```bash
curl -s -X POST http://localhost:8000/api/locations \
  -H 'Content-Type: application/json' \
  -d '{"name":"Склад A","address":"ул. Пушкина, 1","tags":["warehouse"]}'
```

### Создать камеру
```bash
LOCATION_ID=...
curl -s -X POST http://localhost:8000/api/cameras \
  -H 'Content-Type: application/json' \
  -d '{
    "location_id":"'"$LOCATION_ID"'",
    "name":"Cam-01",
    "external_id":"cam-01",
    "rtsp_uri_masked":"rtsp://user:***@10.0.0.1:554/live/main",
    "is_active": true
  }'
```

### Ingest батч событий (dedup_key + upsert)
```bash
CAMERA_ID=...
NOW=$(date -Iseconds)

curl -s -X POST http://localhost:8000/api/fight-events/batch \
  -H 'Content-Type: application/json' \
  -d '{
    "events": [
      {
        "camera_id": "'"$CAMERA_ID"'",
        "started_at": "'"$NOW"'",
        "ended_at": null,
        "peak_score": 0.93,
        "mean_score": 0.71,
        "status": "open",
        "tags": ["auto"],
        "meta": {"model":"r3d_18","threshold":0.7,"run_id":"run-123"},
        "dedup_key": "cam-01:'"$NOW"'"
      }
    ],
    "auto_create_camera": false
  }'
```

Повтори тот же запрос второй раз — дубль не создастся (UPSERT по `(camera_id, dedup_key)`).

### Summary по камере
```bash
curl -s http://localhost:8000/api/cameras/$CAMERA_ID/summary
```

### Summary по локации
```bash
curl -s http://localhost:8000/api/locations/$LOCATION_ID/summary
```

## Тесты

Тесты требуют PostgreSQL. Укажи `TEST_DATABASE_URL` и запусти:

```bash
source .venv/bin/activate
export TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/fight3d_test

python -m pytest -q
```

Если `TEST_DATABASE_URL` не задан, тесты API будут автоматически skipped.

---

# Multi-camera RTSP inference

Скрипт [fight3d/infer/infer_rtsp.py](fight3d/infer/infer_rtsp.py) работает с 1 источником. Для 2+ камер используй [fight3d/infer/infer_multi_rtsp.py](fight3d/infer/infer_multi_rtsp.py) — он запускает **1 процесс на камеру**.

Пример (2 RTSP одновременно):

```bash
python -m fight3d.infer.infer_multi_rtsp \
  --rtsp "rtsp://user:pass@10.0.0.1:554/live/main" \
  --rtsp "rtsp://user:pass@10.0.0.2:554/live/main" \
  --ckpt outputs/new-data/best.pt \
  --device cuda \
  --fight_threshold 0.9 \
  --people_min 2 \
  --clip_len 16 \
  --stride 4 \
  --show 0 \
  --save_dir outputs/multi
```

Или через файл `sources.txt` (по одному URL на строку):

```bash
python -m fight3d.infer.infer_multi_rtsp \
  --sources sources.txt \
  --ckpt outputs/new-data/best.pt \
  --device cuda \
  --show 0
```
