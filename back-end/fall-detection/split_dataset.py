"""
split_dataset.py — Разделение data/fall и data/non-fall на train/val (80/20).

Результат:
  data/train/fall/*.mp4
  data/train/non-fall/*.mp4
  data/val/fall/*.mp4
  data/val/non-fall/*.mp4

Исходные файлы ПЕРЕМЕЩАЮТСЯ (не копируются) для экономии места.
"""

import random
import shutil
from pathlib import Path

SEED = 42
TRAIN_RATIO = 0.80
SRC_ROOT = Path("data")
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"}


def split_class(class_name: str) -> None:
    src_dir = SRC_ROOT / class_name
    if not src_dir.exists():
        print(f"[SKIP] {src_dir} не найдена")
        return

    files = sorted(
        p for p in src_dir.iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_EXTS
    )
    if not files:
        print(f"[SKIP] нет видео в {src_dir}")
        return

    random.seed(SEED)
    random.shuffle(files)

    n_train = int(len(files) * TRAIN_RATIO)
    train_files = files[:n_train]
    val_files = files[n_train:]

    train_dir = SRC_ROOT / "train" / class_name
    val_dir = SRC_ROOT / "val" / class_name
    train_dir.mkdir(parents=True, exist_ok=True)
    val_dir.mkdir(parents=True, exist_ok=True)

    for f in train_files:
        shutil.move(str(f), str(train_dir / f.name))
    for f in val_files:
        shutil.move(str(f), str(val_dir / f.name))

    print(f"[{class_name}] total={len(files)}  train={len(train_files)}  val={len(val_files)}")


def main():
    print(f"Split ratio: train={TRAIN_RATIO:.0%}  val={1 - TRAIN_RATIO:.0%}")
    print(f"Seed: {SEED}")
    print()

    split_class("fall")
    split_class("non-fall")

    # Удалить исходные папки если пусты
    for name in ("fall", "non-fall"):
        d = SRC_ROOT / name
        if d.exists() and not any(d.iterdir()):
            d.rmdir()
            print(f"[CLEAN] удалена пустая {d}")

    print()
    # Итоговая статистика
    for split in ("train", "val"):
        for cls in ("fall", "non-fall"):
            d = SRC_ROOT / split / cls
            if d.exists():
                n = len(list(d.glob("*.mp4")))
                print(f"  {split}/{cls}: {n}")

    print("\nDone!")


if __name__ == "__main__":
    main()
