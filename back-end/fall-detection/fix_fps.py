"""
fix_fps.py — Перекодирование всех mp4 в data/ в 30fps / 3с.

Находит файлы с FPS != 30 или длительностью вне 2.9–3.1с,
перекодирует их на месте (через временный файл).

Использование:
  python fix_fps.py           # показать что будет перекодировано (dry-run)
  python fix_fps.py --fix     # перекодировать
"""

import argparse
import shutil
import subprocess
from pathlib import Path

TARGET_FPS = 30
CLIP_SEC = 3.0
MIN_DUR = 2.9
MAX_DUR = 3.1
DATA_ROOT = Path("data")


def resolve_ff_tools() -> tuple[str, str]:
    ffmpeg_bin = shutil.which("ffmpeg")
    ffprobe_bin = shutil.which("ffprobe")
    if not ffmpeg_bin:
        p = Path(r"C:\ffmpeg\bin\ffmpeg.exe")
        if p.exists():
            ffmpeg_bin = str(p)
    if not ffprobe_bin:
        p = Path(r"C:\ffmpeg\bin\ffprobe.exe")
        if p.exists():
            ffprobe_bin = str(p)
    if not ffmpeg_bin or not ffprobe_bin:
        raise FileNotFoundError("ffmpeg/ffprobe not found")
    return ffmpeg_bin, ffprobe_bin


def get_dur(ffprobe: str, f: Path) -> float:
    return float(subprocess.check_output(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(f)],
        text=True).strip())


def get_fps(ffprobe: str, f: Path) -> float:
    raw = subprocess.check_output(
        [ffprobe, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=avg_frame_rate",
         "-of", "default=noprint_wrappers=1:nokey=1", str(f)],
        text=True).strip()
    if "/" in raw:
        n, d = raw.split("/")
        return round(float(n) / float(d), 1)
    return round(float(raw), 1)


def reencode(ffmpeg: str, src: Path) -> bool:
    """Перекодировать файл на месте: 30fps, ≤3с, libx264."""
    tmp = src.with_suffix(".tmp.mp4")
    cmd = [
        ffmpeg,
        "-hide_banner", "-loglevel", "warning",
        "-i", str(src),
        "-t", f"{CLIP_SEC:.3f}",
        "-map", "0:v:0",
        "-vf", f"scale=trunc(iw/2)*2:trunc(ih/2)*2,fps={TARGET_FPS},format=yuv420p",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-profile:v", "main", "-level", "4.0",
        "-preset", "veryfast", "-crf", "23",
        "-movflags", "+faststart",
        "-an", "-y",
        str(tmp),
    ]
    try:
        subprocess.run(cmd, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        src.unlink()
        tmp.rename(src)
        return True
    except subprocess.CalledProcessError:
        if tmp.exists():
            tmp.unlink()
        return False


def main():
    parser = argparse.ArgumentParser(description="Перекодировать mp4 в data/ → 30fps/3с")
    parser.add_argument("--fix", action="store_true",
                        help="Перекодировать (без флага — dry-run)")
    args = parser.parse_args()

    ffmpeg_bin, ffprobe_bin = resolve_ff_tools()

    files = sorted(DATA_ROOT.rglob("*.mp4"))
    print(f"Всего файлов: {len(files)}\n")

    to_fix = []
    for f in files:
        try:
            dur = get_dur(ffprobe_bin, f)
            fps = get_fps(ffprobe_bin, f)
        except Exception as e:
            print(f"[ERR] {f}: {e}")
            continue

        dur_ok = MIN_DUR <= dur <= MAX_DUR
        fps_ok = fps == float(TARGET_FPS)

        if not dur_ok or not fps_ok:
            to_fix.append((f, dur, fps))

    if not to_fix:
        print("Все файлы в порядке (3с, 30fps).")
        return

    print(f"Нужно перекодировать: {len(to_fix)} файлов\n")

    if not args.fix:
        for f, d, r in to_fix[:50]:
            print(f"  {f}  dur={d:.2f}s  fps={r}")
        if len(to_fix) > 50:
            print(f"  ... и ещё {len(to_fix) - 50}")
        print(f"\nДля перекодирования запустите:  python fix_fps.py --fix")
        return

    ok = 0
    fail = 0
    for i, (f, d, r) in enumerate(to_fix, 1):
        status = f"[{i}/{len(to_fix)}] {f.name}  {d:.2f}s/{r}fps"
        if reencode(ffmpeg_bin, f):
            ok += 1
            print(f"  {status}  -> OK")
        else:
            fail += 1
            print(f"  {status}  -> FAIL")

    print(f"\nГотово: {ok} перекодировано, {fail} ошибок")


if __name__ == "__main__":
    main()
