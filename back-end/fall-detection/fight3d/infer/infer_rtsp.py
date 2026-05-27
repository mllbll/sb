from __future__ import annotations

from fight3d.infer.rtsp_runner import run_rtsp


def main() -> None:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--rtsp", type=str, required=True, help='RTSP URL or "file:video.avi"')
    p.add_argument("--ckpt", type=str, required=True)
    p.add_argument("--yolo_model", type=str, default="yolov8m.pt")
    p.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"])
    p.add_argument("--save", type=str, default="", help="Optional path to save mp4 recording")
    p.add_argument("--fall_threshold", type=float, default=0.7)
    p.add_argument("--people_min", type=int, default=2)
    p.add_argument("--clip_len", type=int, default=16)
    p.add_argument("--stride", type=int, default=4, help="Temporal stride (compute every N frames)")
    p.add_argument("--show", type=int, default=1, choices=[0, 1])
    p.add_argument("--yolo_conf", type=float, default=0.25)
    p.add_argument("--yolo_iou", type=float, default=0.7)
    args = p.parse_args()

    run_rtsp(
        rtsp=args.rtsp,
        ckpt=args.ckpt,
        yolo_model=args.yolo_model,
        device=args.device,
        save=args.save,
        fall_threshold=float(args.fall_threshold),
        people_min=int(args.people_min),
        clip_len=int(args.clip_len),
        stride=int(args.stride),
        show=int(args.show),
        yolo_conf=float(args.yolo_conf),
        yolo_iou=float(args.yolo_iou),
        window_name="fight3d-rtsp",
    )


if __name__ == "__main__":
    main()
