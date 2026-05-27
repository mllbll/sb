# Миграции (Alembic)

## Структура

```
alembic.ini                        — конфиг Alembic, указывает на папку migrations/
migrations/
  env.py                           — читает secrets.json и строит URL подключения
  script.py.mako                   — шаблон для новых ревизий
  versions/
    0001_create_crowd_data.py      — создание таблицы и индексов
```

`env.py` не использует `DATABASE_URL` из окружения — он сам читает `keys/secrets.json`. Менять его не нужно.

## Применить миграции

```bash
pip install -r requirements-migrations.txt
alembic upgrade head
```

В Docker это происходит автоматически через сервис `migrate` в `docker-compose.yml`.

## Откатить последнюю миграцию

```bash
alembic downgrade -1
```

## Посмотреть текущую версию

```bash
alembic current
```

## История ревизий

```bash
alembic history
```

## Создать новую миграцию

Alembic не использует ORM-модели, поэтому autogenerate не знает о структуре таблиц и не сможет сгенерировать diff автоматически. Нужно писать SQL вручную.

```bash
alembic revision -m "add_column_zone_id"
```

Откроется новый файл в `migrations/versions/`. Пишем изменения в `upgrade()` и откат в `downgrade()`:

```python
def upgrade() -> None:
    op.execute("ALTER TABLE crowd_data ADD COLUMN zone_id TEXT")

def downgrade() -> None:
    op.execute("ALTER TABLE crowd_data DROP COLUMN zone_id")
```

Затем применяем:

```bash
alembic upgrade head
```

## Что создаёт миграция 0001

Таблица `crowd_data`:

```sql
CREATE TABLE crowd_data (
    id           BIGSERIAL PRIMARY KEY,
    camera_id    TEXT           NOT NULL,
    people_count INT            NOT NULL DEFAULT 0,
    crowd_count  INT            NOT NULL DEFAULT 0,
    time         TIMESTAMPTZ(6)          DEFAULT NOW(),
    filename     TEXT
);
```

Индексы:

```sql
CREATE INDEX ix_crowd_data_camera_time ON crowd_data (camera_id, time DESC);
CREATE INDEX ix_crowd_data_time        ON crowd_data (time DESC);
```

`ix_crowd_data_camera_time` используется WebSocket-запросом `DISTINCT ON (camera_id) ORDER BY camera_id, time DESC` — это основной запрос реального времени, и без индекса он будет делать seq scan на большой таблице.

`ix_crowd_data_time` используется REST-эндпоинтами со `WHERE time >= NOW() - INTERVAL '...'`.

Миграция идемпотентна — использует `CREATE TABLE IF NOT EXISTS` и `CREATE INDEX IF NOT EXISTS`, поэтому безопасно запускать повторно на уже развёрнутой базе.
