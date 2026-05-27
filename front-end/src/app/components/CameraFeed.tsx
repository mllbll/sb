import { useEffect, useState } from "react";
import { WifiOff, AlertTriangle } from "lucide-react";
import { useTheme } from "../context/ThemeContext";

interface CameraFeedProps {
  cameraId: string;
  cameraName: string;
  building: string;
  online: boolean;
  alertActive?: boolean;
  showCount?: boolean;
  compact?: boolean;
}

export function CameraFeed({
  cameraId,
  cameraName,
  building,
  online,
  alertActive = false,
  compact = false,
}: CameraFeedProps) {
  const { t } = useTheme();
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  if (!online) {
    return (
      <div
        className={`relative overflow-hidden ${compact ? "aspect-video" : "aspect-video"}`}
        style={{ background: t.isDark ? "#0d1117" : "#f0f0f0", borderRadius: 4 }}
      >
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
          <WifiOff className="w-5 h-5" style={{ color: t.border }} />
          <span style={{ fontSize: 9, color: t.border, fontFamily: "monospace" }}>
            НЕТ СИГНАЛА
          </span>
        </div>
        <div className="absolute top-2 left-2 flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full" style={{ background: "#f85149" }} />
          <span style={{ fontSize: 9, color: t.textMuted, fontFamily: "monospace" }}>
            {cameraId.toUpperCase()}
          </span>
        </div>
        <div className="absolute bottom-0 left-0 right-0 px-2 py-1.5"
          style={{ background: "linear-gradient(to top, rgba(0,0,0,0.5), transparent)" }}>
          <span style={{ fontSize: 9, color: t.textMuted, fontFamily: "monospace" }}>{cameraName}</span>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`relative overflow-hidden ${compact ? "aspect-video" : "aspect-video"}`}
      style={{
        background: alertActive
          ? "radial-gradient(ellipse at 50% 30%, #180a0a 0%, #0d0808 100%)"
          : "radial-gradient(ellipse at 50% 30%, #0f1a0f 0%, #080c08 100%)",
        borderRadius: 4,
      }}
    >
      {/* Subtle vignette */}
      <div className="absolute inset-0 pointer-events-none" style={{
        background: "radial-gradient(ellipse at center, transparent 45%, rgba(0,0,0,0.55) 100%)",
        zIndex: 1,
      }} />

      {/* Alert border pulse */}
      {alertActive && (
        <div className="absolute inset-0 pointer-events-none" style={{
          border: "1px solid #f85149",
          animation: "pulse 1.5s ease-in-out infinite",
          zIndex: 2,
        }} />
      )}

      {/* Top bar */}
      <div className="absolute top-0 left-0 right-0 flex justify-between items-center px-2 pt-1.5 z-10">
        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full animate-pulse"
            style={{ background: alertActive ? "#f85149" : "#3fb950" }} />
          <span style={{ fontSize: 8, color: alertActive ? "#f85149" : "#3fb950", fontFamily: "monospace", opacity: 0.9 }}>
            REC
          </span>
          <span style={{ fontSize: 8, color: "#8b949e", fontFamily: "monospace", opacity: 0.7, marginLeft: 3 }}>
            {cameraId.toUpperCase()}
          </span>
        </div>
        <span style={{ fontSize: 8, color: "#8b949e", fontFamily: "monospace", opacity: 0.7 }} className="tabular-nums">
          {time.toLocaleTimeString("ru", { hour12: false })}
        </span>
      </div>

      {/* Alert label */}
      {alertActive && (
        <div className="absolute top-6 left-0 right-0 flex justify-center z-10">
          <div className="flex items-center gap-1 px-2 py-0.5 rounded"
            style={{ background: "rgba(248,81,73,0.8)", fontSize: 8 }}>
            <AlertTriangle style={{ width: 7, height: 7, color: "white" }} />
            <span style={{ color: "white", fontFamily: "monospace", fontSize: 8 }}>ТРЕВОГА</span>
          </div>
        </div>
      )}

      {/* Bottom bar */}
      <div className="absolute bottom-0 left-0 right-0 px-2 py-1.5 z-10"
        style={{ background: "linear-gradient(to top, rgba(0,0,0,0.8), transparent)" }}>
        <div className="flex justify-between items-end">
          <div>
            <div style={{ fontSize: 8, color: "#e6edf3", fontFamily: "monospace", opacity: 0.9, lineHeight: 1 }}>
              {cameraName}
            </div>
            <div style={{ fontSize: 7, color: "#8b949e", fontFamily: "monospace", opacity: 0.6, marginTop: 1 }}>
              {building}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}