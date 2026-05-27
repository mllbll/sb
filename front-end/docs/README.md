# REU Secure Dashboard

## 1. Обзор проекта

REU Secure Dashboard — SPA-дашборд системы безопасности для университетского кампуса РЭУ им. Г.В. Плеханова. Система предназначена для операторов охраны и обрабатывает три класса событий в режиме реального времени: скопления людей (подсчёт людей по зонам, превышение порогов), конфликты (детекция агрессивного поведения) и падения (детекция падений, медицинский протокол).

---

## 2. Стек технологий

| Технология   | Версия  | Роль                                                    |
|--------------|---------|---------------------------------------------------------|
| TypeScript   | 5.x     | Типизация всего проекта                                 |
| React        | 18.3.1  | UI, контексты, хуки                                     |
| Vite         | 6.3.5   | Сборщик, `import.meta.env`                              |
| React Router | 7.13.0  | Клиентский роутинг                                      |
| Tailwind CSS | 4.1.12  | Утилитарные стили                                       |
| Recharts     | 2.15.2  | Графики                                                 |
| Lucide React | 0.487.0 | Иконки                                                  |
| date-fns     | 3.6.0   | Форматирование дат                                      |
| nginx:alpine | latest  | Раздача статики SPA + reverse proxy для WS и auth API   |
| node:20-alpine | 20    | Auth-сервис (без npm-зависимостей)                      |

---

## 3. Быстрый старт (разработка)

### Требования

- Node.js >= 20

### Установка и запуск

```bash
npm install
npm run dev       # dev-сервер на http://localhost:5173
```

В dev-режиме работает **mock-режим** — реальный бэкенд не нужен. Данные генерируются в браузере через `useMockData.ts` (crowd-обновления каждые 3 с, случайные fight/fall каждые 30 с).

```bash
npm run build     # production-сборка в dist/
npm run preview   # предпросмотр собранной версии
```

---

## 4. Деплой — полное руководство

### 4.1 Архитектура развёртывания

```
                         ХОСТ-МАШИНА
  ┌──────────────────────────────────────────────────────────┐
  │                                                          │
  │   Docker Compose Network ("secure-system_default")       │
  │  ┌────────────────────────────────────────────────────┐  │
  │  │                                                    │  │
  │  │  ┌─────────────────────┐   ┌──────────────────┐   │  │
  │  │  │  frontend           │   │  auth            │   │  │
  │  │  │  nginx:alpine       │──▶│  node:20-alpine  │   │  │
  │  │  │  :80 (внешний порт) │   │  :3001 (internal)│   │  │
  │  │  └──────────┬──────────┘   └──────────────────┘   │  │
  │  │             │                                      │  │
  │  └─────────────┼──────────────────────────────────────┘  │
  │                │ host.docker.internal:8000               │
  │                ▼                                         │
  │  ┌──────────────────────────────────────────────────┐   │
  │  │  Бэкенд-сервисы (запускаются отдельно)           │   │
  │  │  ws://localhost:8000/ws/crowd   (crowd-сервис)    │   │
  │  │  ws://localhost:8000/ws/fight   (fight-сервис)    │   │
  │  └──────────────────────────────────────────────────┘   │
  │                                                          │
  └──────────────────────────────────────────────────────────┘

  Браузер → http://HOST:80
```

**Порты:**

| Сервис        | Порт (снаружи) | Порт (внутри контейнера) | Кто обращается         |
|---------------|----------------|--------------------------|------------------------|
| frontend      | **80**         | 80                       | браузер                |
| auth          | не открыт      | 3001                     | nginx (внутри compose) |
| бэкенд WS     | **8000** (хост)| —                        | nginx через `host.docker.internal` |

### 4.2 Требования к окружению

- Docker >= 24
- Docker Compose >= 2 (`docker compose` без дефиса)
- Два бэкенд WS-сервиса, доступных на **хост-машине** по адресам:
  - `ws://localhost:8000/ws/crowd`
  - `ws://localhost:8000/ws/fight`

> Бэкенд-сервисы могут быть реализованы на любом стеке (Python/FastAPI, Go, Node.js и т.д.) — главное, что они слушают `:8000` и отдают нужные WS-эндпоинты.

### 4.3 Первый запуск

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd secure-system

# 2. Создать .env с учётными данными
cp .env.example .env
```

Отредактировать `.env`:

```dotenv
AUTH_USER=admin
AUTH_PASSWORD=ваш_надёжный_пароль
```

```bash
# 3. Запустить бэкенд-сервисы на хосте (например)
python crowd_service.py   # слушает :8000/ws/crowd
python fight_service.py   # слушает :8000/ws/fight

# 4. Собрать и запустить Docker Compose
docker compose up --build -d

# 5. Открыть в браузере
open http://localhost
```

### 4.4 Последующие обновления

```bash
# Пересобрать только фронтенд (после изменений в src/)
docker compose up --build -d frontend

# Пересобрать только auth (после изменений в auth-service/)
docker compose up --build -d auth

# Полная пересборка
docker compose up --build -d
```

### 4.5 Остановка

```bash
docker compose down          # остановить и удалить контейнеры
docker compose down -v       # + удалить volumes (если есть)
```

### 4.6 Логи

```bash
docker compose logs -f              # все сервисы
docker compose logs -f frontend     # только nginx
docker compose logs -f auth         # только auth-сервис
docker compose ps                   # статус контейнеров
```

---

## 5. Конфигурация nginx

Файл `nginx.conf` копируется в образ при сборке и управляет всеми входящими запросами.

```nginx
upstream backend {
    server host.docker.internal:8000;  # бэкенд на хосте
}

server {
    listen 80;
    root /usr/share/nginx/html;        # dist/ фронтенда

    # WebSocket: crowd-сервис
    location /ws/crowd { ... }

    # WebSocket: fight/fall-сервис
    location /ws/fight { ... }

    # Auth API
    location /api/ { ... }

    # SPA-роутинг (всё остальное → index.html)
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### 5.1 WebSocket-проксирование

```nginx
location /ws/crowd {
    proxy_pass http://backend/ws/crowd;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;      # обязательно для WS
    proxy_set_header Connection "upgrade";        # обязательно для WS
    proxy_set_header Host $host;
    proxy_read_timeout 86400;  # 24ч — не разрывать idle WS-соединение
}
```

**Почему так:**
- `proxy_http_version 1.1` — WebSocket требует HTTP/1.1
- `Upgrade` и `Connection "upgrade"` — заголовки handshake'а WS-соединения; без них nginx не пробрасывает апгрейд
- `proxy_read_timeout 86400` — без этого nginx закрывает соединение после 60 с без данных; для постоянных WS-соединений нужно большое значение

### 5.2 Auth API-проксирование

```nginx
location /api/ {
    proxy_pass http://auth:3001;    # auth — имя сервиса в docker-compose
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

`auth` разрешается через встроенный Docker DNS (оба контейнера в одной сети compose). Порт 3001 не открыт наружу — только nginx может к нему обратиться.

### 5.3 SPA-роутинг

```nginx
location / {
    try_files $uri $uri/ /index.html;
}
```

`try_files` сначала ищет реальный файл (`$uri`), затем директорию (`$uri/`), иначе отдаёт `index.html`. Это позволяет React Router обрабатывать URL типа `/crowd`, `/fight` на клиенте — при прямом переходе по ссылке страница не падает с 404.

### 5.4 Кэширование статики

```nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

Vite при сборке добавляет хеш к именам файлов (e.g. `index-Bn3xQ1aT.js`). Файл с новым хешем — новый URL → браузер скачает его. Старый URL никогда не изменится → можно кэшировать на год с `immutable`. `index.html` под этот regex не попадает и не кэшируется, поэтому новый деплой всегда подхватывается.

### 5.5 Gzip-сжатие

```nginx
gzip on;
gzip_types text/plain text/css application/javascript application/json;
```

Уменьшает размер JS/CSS бандла при передаче. Для типичного React-приложения даёт 60–70% экономии трафика.

---

## 6. Авторизация

### Принцип работы

```
Браузер                nginx              auth-сервис
   │                     │                    │
   │─ POST /api/auth/login ──────────────────▶│
   │  { login, password } │                   │ проверяет AUTH_USER/AUTH_PASSWORD
   │                      │◀── { token, user }─│
   │◀── { token, user } ──│                   │
   │                      │                   │
   │ (сохраняет token в localStorage)
   │
   │─ GET / (маршруты дашборда) ────────────▶ nginx (отдаёт index.html)
   │ (React проверяет токен в localStorage)
```

**Auth-сервис** (`auth-service/server.js`):
- Чистый Node.js, без npm-зависимостей (только встроенные `http` и `crypto`)
- Генерирует случайный токен (`crypto.randomBytes(32)`) при успешном входе
- Токен не хранится на сервере и не верифицируется при последующих запросах — он служит только для React как признак аутентификации в `localStorage`

**Смена пароля** — отредактировать `.env` и перезапустить:

```bash
docker compose up -d auth
```

### Ограничения и улучшения

Текущая реализация — защита **на уровне UI**. Прямое подключение к `ws://HOST:8000/ws/crowd` минует фронтенд полностью. Варианты усиления:

| Подход | Сложность | Что даёт |
|--------|-----------|----------|
| Проброс токена в WS URL (`?token=...`) и его верификация в бэкенде | средняя | Защита WS на уровне соединения |
| JWT с проверкой на nginx (`auth_request`) | высокая | Полноценная stateless авторизация |
| VPN / IP-allowlist на уровне firewall | низкая | Сетевая изоляция (для внутренних систем) |

---

## 7. Переменные окружения

### Фронтенд (build-time, встраиваются в JS-бандл)

| Переменная      | Файл               | Значение    | Описание                              |
|-----------------|--------------------|-------------|---------------------------------------|
| `VITE_USE_MOCK`  | `.env`             | `true`      | Dev: mock-данные                      |
| `VITE_USE_MOCK`  | `.env.production`  | `false`     | Prod: реальный бэкенд                 |

> Vite автоматически загружает `.env.production` при `npm run build` (режим `production`). Dockerfile запускает именно `npm run build`, поэтому при сборке образа `VITE_USE_MOCK=false` подхватывается автоматически.

### Auth-сервис (runtime, через docker-compose)

| Переменная      | По умолчанию | Описание           |
|-----------------|--------------|--------------------|
| `AUTH_USER`     | `admin`      | Логин оператора    |
| `AUTH_PASSWORD` | `changeme`   | Пароль оператора   |

Задаются в `.env` в корне репозитория, передаются в контейнер через `docker-compose.yml`:

```yaml
auth:
  environment:
    AUTH_USER: ${AUTH_USER:-admin}
    AUTH_PASSWORD: ${AUTH_PASSWORD:-changeme}
```

---

## 8. Docker — детали сборки

### 8.1 Dockerfile (фронтенд)

```dockerfile
# Stage 1: сборка React-приложения
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci                  # чистая установка по lock-файлу
COPY . .
# Vite подхватывает .env.production → VITE_USE_MOCK=false
RUN npm run build           # результат в /app/dist

# Stage 2: раздача статики
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

Двухэтапная сборка: финальный образ содержит только nginx + статику (~25 МБ), без Node.js и исходников.

### 8.2 docker-compose.yml

```yaml
services:
  frontend:
    build: .
    ports:
      - "80:80"          # браузер подключается сюда
    depends_on:
      - auth             # auth стартует раньше frontend
    extra_hosts:
      - "host.docker.internal:host-gateway"   # доступ к хосту из контейнера (Linux)

  auth:
    build: ./auth-service
    environment:
      AUTH_USER: ${AUTH_USER:-admin}
      AUTH_PASSWORD: ${AUTH_PASSWORD:-changeme}
    restart: unless-stopped
```

**`extra_hosts: host.docker.internal:host-gateway`** — ключевая строка для Linux. На Docker Desktop (Mac/Windows) `host.docker.internal` работает автоматически; на Linux-сервере нужен этот маппинг, чтобы nginx внутри контейнера мог достучаться до `localhost:8000` хоста.

### 8.3 Сетевая модель Docker Compose

```
Контейнер frontend (nginx)
  ├── может обращаться к auth:3001      (через Docker internal DNS)
  ├── может обращаться к host.docker.internal:8000  (через extra_hosts)
  └── открывает порт 80 наружу

Контейнер auth
  └── не открывает портов наружу (доступен только nginx-у)
```

---

## 9. WebSocket-протокол

Фронтенд открывает **два отдельных** WS-соединения через nginx:

| Путь (nginx) | Проксируется на       | События от бэкенда                                                                 |
|--------------|-----------------------|------------------------------------------------------------------------------------|
| `/ws/crowd`  | `host:8000/ws/crowd`  | `crowd.update`                                                                     |
| `/ws/fight`  | `host:8000/ws/fight`  | `fight.detected`, `fight.resolved`, `fall.detected`, `fall.resolved`, `camera.status` |

WS-URL строится фронтендом динамически: `ws(s)://{window.location.host}/ws/crowd` — хардкода нет, работает при любом домене.

### 9.1 Формат сообщений

Все сообщения от бэкенда:

```json
{ "type": "тип.события", "payload": { ... } }
```

### 9.2 Таблица событий

| Тип события      | Payload                                              | Откуда  | Рекомендуемая частота |
|------------------|------------------------------------------------------|---------|------------------------|
| `crowd.update`   | `{ total: number, zones: ZoneUpdate[] }`             | `/ws/crowd` | ~5 с              |
| `fight.detected` | `{ id, location, camera_id, participants }`          | `/ws/fight` | по событию        |
| `fight.resolved` | `{ id }`                                             | `/ws/fight` | по событию        |
| `fall.detected`  | `{ id, location, camera_id, person_type, age }`      | `/ws/fight` | по событию        |
| `fall.resolved`  | `{ id }`                                             | `/ws/fight` | по событию        |
| `camera.status`  | `{ camera_id: string, online: boolean }`             | `/ws/fight` | по событию        |
| `ping`           | —                                                    | любой   | ~30 с                  |

```typescript
interface ZoneUpdate {
  id: string;      // "z1", "z2", ... — должен совпадать с id из mock.ts
  current: number; // текущее количество людей
}
```

### 9.3 Примеры

```json
{ "type": "crowd.update", "payload": { "total": 312, "zones": [{ "id": "z1", "current": 47 }, { "id": "z2", "current": 89 }] } }

{ "type": "fight.detected", "payload": { "id": "FGT-0050", "location": "Корпус А, Коридор", "camera_id": "cam-04", "participants": 2 } }

{ "type": "fight.resolved", "payload": { "id": "FGT-0050" } }

{ "type": "fall.detected", "payload": { "id": "FLL-0032", "location": "Библиотека", "camera_id": "cam-05", "person_type": "Студент", "age": 21 } }

{ "type": "camera.status", "payload": { "camera_id": "cam-01", "online": false } }
```

### 9.4 Reconnect-логика

При обрыве соединения — автоматический переподключение с exponential backoff:

```
1с → 2с → 4с → 8с → 16с → 30с (максимум)
```

Максимум 5 попыток. WS-индикатор в хедере показывает агрегированный статус обоих соединений (наихудший из двух).

---


## 10. Структура файлов

```
.
├── auth-service/
│   ├── Dockerfile          # FROM node:20-alpine, node server.js
│   └── server.js           # POST /api/auth/login (без npm-зависимостей)
├── docs/
│   └── README.md           # этот файл
├── src/
│   └── app/
│       ├── components/
│       │   ├── CameraFeed.tsx      # отображение камеры (онлайн/офлайн/тревога)
│       │   ├── Layout.tsx          # header, sidebar, <Outlet>
│       │   ├── ProtectedRoute.tsx  # редирект на /login если нет токена
│       │   ├── SettingsPanel.tsx   # дропдаун: тема, выход
│       │   └── WSStatusPanel.tsx   # статус WS (crowd + fight агрегированно)
│       ├── context/
│       │   ├── AuthContext.tsx     # auth state, POST /api/auth/login
│       │   └── ThemeContext.tsx    # dark/light тема
│       ├── data/
│       │   └── mock.ts             # статичные mock-данные (камеры, зоны, инциденты)
│       ├── hooks/
│       │   ├── useMockData.ts      # эмуляция WS через setInterval (mock-режим)
│       │   └── useWebSocket.ts     # два WS-соединения: crowd + fight
│       ├── pages/
│       │   ├── CrowdModule.tsx     # /crowd — зоны, графики плотности
│       │   ├── FallModule.tsx      # /fall — алерты падений, чеклист
│       │   ├── FightModule.tsx     # /fight — алерт конфликта, журнал
│       │   ├── LoginPage.tsx       # /login — страница входа
│       │   └── Overview.tsx        # / — дашборд: KPI, график, журнал событий
│       ├── services/
│       │   └── websocket.ts        # crowdWsManager + fightWsManager
│       ├── store/
│       │   └── appStore.tsx        # Context + useReducer (глобальный стейт)
│       └── types/
│           └── events.ts           # TypeScript-типы WS-событий
├── .env                    # gitignored; AUTH_USER, AUTH_PASSWORD для dev/prod
├── .env.example            # шаблон для .env
├── .env.production         # VITE_USE_MOCK=false (используется при docker build)
├── docker-compose.yml      # frontend (nginx) + auth (node)
├── Dockerfile              # multi-stage: node builder → nginx:alpine
├── nginx.conf              # SPA + WS proxy (/ws/crowd, /ws/fight) + auth proxy (/api/)
├── vite.config.ts          # Vite + React + Tailwind
└── tsconfig.json           # TypeScript strict mode
```
