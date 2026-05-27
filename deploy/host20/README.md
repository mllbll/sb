# ПК 2 — 192.168.1.20 (fall + UI)

## Запуск

Из **корня репозитория**:

```bash
docker compose -f deploy/host20/docker-compose.yml up --build -d
```

Не запускайте `docker compose up` из `deploy/host20/` без `-f` — пути к `../../back-end` будут неверны.

## Сборка frontend отдельно

```bash
cd front-end
docker build -f Dockerfile.host20 -t reu-frontend-host20 .
```

## Если падает `npm run build` в Docker

1. Пересоберите без кэша:
   ```bash
   docker compose -f deploy/host20/docker-compose.yml build --no-cache frontend
   ```

2. Проверьте сборку на хосте (нужны Node 20+ и сеть до registry.npmjs.org):
   ```bash
   cd front-end && npm ci && VITE_USE_MOCK=false npm run build
   ```

3. На слабых машинах увеличьте память для Node:
   ```bash
   docker compose -f deploy/host20/docker-compose.yml build frontend \
     --build-arg NODE_OPTIONS=--max-old-space-size=4096
   ```
   (при необходимости добавьте `ARG`/`ENV` в `front-end/Dockerfile.host20`)

4. Убедитесь, что в репозитории есть `front-end/package-lock.json`.
