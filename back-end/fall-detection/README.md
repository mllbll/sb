# fight3d — Prototype CCTV Fight Detection (R3D-18 + YOLO)

Прототип «детекция драки» для CCTV/RTSP:
- детекция людей на каждом кадре (Ultralytics YOLO, класс `person`)
- классификация коротких клипов (R3D-18 из TorchVision) на `Fight` vs `NonFight`
- realtime режим (RTSP или `file:video.avi`) + режим обработки видеофайла
- тревожная визуализация: один общий (union) красный бокс, мигающий и удерживаемый 3 секунды после срабатывания

## Схемы

### Пайплайн инференса
![Inference pipeline](docs/diagrams/pipeline.svg)

### Обучение
![Training loop](docs/diagrams/training.svg)

### Логика тревоги (hold + blink)
![Alert logic](docs/diagrams/alert_logic.svg)

## Технологии
- Python 3.10+
- PyTorch + TorchVision (`torchvision.models.video.r3d_18`)
- OpenCV (`cv2`) для чтения/показа/записи видео
- Ultralytics YOLO для детекции людей

## Быстрый старт

### 1) Установка
Запускать команды из корня репозитория (там лежат папки `fight3d/`, `RWF-2000/`, `outputs/`).

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
```

Проверка:
```bash
python -c "import torch, torchvision, cv2, ultralytics, yaml; print('ok')"
```

### 2) Данные (RWF-2000)
Поддерживаются два варианта размещения:

Вариант A (как у вас в workspace):
```
RWF-2000/
  train/
    Fight/
    NonFight/
  val/
    Fight/
    NonFight/
```

Вариант B (дефолтный путь):
```
data/rwf2000/
  train/...
  val/...
```

В командах ниже используйте `--data_root RWF-2000` или оставьте дефолт `data/rwf2000`.

## Как это работает

### Детекция людей (YOLO)
В каждом кадре запускается YOLO, берутся боксы класса `person`. Дальше:
- если `people < people_min` → считаем сцену «IDLE» и не гоняем R3D
- иначе кадры кладутся в буфер клипа

### Классификация клипа (R3D-18)
Каждые `--stride` кадров, когда буфер заполнен до `--clip_len`:
- собирается клип из последних T кадров
- клип приводится к RGB и нормализуется (Kinetics mean/std)
- R3D-18 выдаёт `fight_score = P(Fight)`

### Тревожная визуализация (1 общий бокс + мигание + удержание)
Если `fight_score >= fight_threshold`:
- сохраняются «замороженные» боксы людей (на момент срабатывания)
- рисуется один общий бокс: union всех боксов людей
- на 3 секунды включается hold: тревога продолжает показываться даже при флуктуациях
- в hold-окне бокс мигает (2 Гц)

## Обучение (fine-tune R3D-18)

Команда (пример):
```bash
python -m fight3d.train.train_r3d \
  --data_root RWF-2000 \
  --epochs 10 \
  --batch_size 8 \
  --lr 1e-4 \
  --device auto \
  --output outputs/r3d_rwf
```
```bash
python -m fight3d.train.train_r3d \
  --data_root RWF-2000 \
  --epochs 10 \
  --batch_size 32 \
  --num_workers 4 \
  --lr 1e-4 \
  --gpu_ids 0,1 \
  --output outputs/r3d_rwf_2gpu
```
Для выбора видеокарты:
```bash
  CUDA_VIDIBLE_DEVICES=1
```
gpu_ids - Выбор карты. '0,1' - используется обе карты

Артефакты:
- `outputs/r3d_rwf/last.pt` — последний чекпоинт
- `outputs/r3d_rwf/best.pt` — лучший по `f1_fight` на val
- `outputs/r3d_rwf/metrics.json` — гиперпараметры и метрики по эпохам

## Инференс: видеофайл → mp4

```bash
python -m fight3d.infer.infer_video \
  --video test3.avi \
  --ckpt outputs/r3d_rwf/best.pt \
  --yolo_model yolov8m.pt \
  --device auto \
  --out outputs/demo.mp4 \
  --fight_threshold 0.7 \
  --people_min 2 \
  --clip_len 16 \
  --stride 4
```

## Realtime: RTSP (или file-режим) + опциональная запись

RTSP с окном предпросмотра и записью:
```bash
python -m fight3d.infer.infer_rtsp \
  --rtsp "rtsp://USER:PASS@HOST:554/live/main" \
  --ckpt outputs/r3d_rwf/best.pt \
  --yolo_model yolov8m.pt \
  --device auto \
  --save outputs/rtsp_record.mp4 \
  --fight_threshold 0.6 \
  --people_min 2 \
  --clip_len 16 \
  --stride 4 \
  --show 1
```

Управление (окно `fight3d-rtsp`):
- `q` — выход
- `p` — пауза/продолжить

File-режим (удобно для теста realtime-логики без RTSP):
```bash
python -m fight3d.infer.infer_rtsp \
  --rtsp file:test3.avi \
  --ckpt outputs/r3d_rwf/best.pt \
  --show 0 \
  --save outputs/rtsp_demo.mp4
```

## Настройка порогов
- `--people_min` отсекает одиночные сцены/шум
- `--fight_threshold` управляет чувствительностью (выше → меньше ложных тревог)
- `--stride` влияет на частоту пересчёта R3D (ниже → чаще и дороже)

## Troubleshooting
- `ModuleNotFoundError: cv2` → вы запускаете не из venv. Активируйте: `source .venv/bin/activate`.
- Если `python` отсутствует в системе, используйте `python3` для создания venv.
- Для ускорения на GPU: ставьте CUDA-сборки PyTorch/TorchVision под вашу версию CUDA.
