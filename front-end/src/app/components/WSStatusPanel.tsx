import { useEffect, useRef } from "react";
import { crowdWsManager, fallWsManager, fightWsManager } from "../services/websocket";
import { useAppStore } from "../store/appStore";

interface Props {
  onClose: () => void;
  triggerRef?: React.RefObject<HTMLButtonElement | null>;
}

const statusColor = {
  connected: "#3fb950",
  reconnecting: "#d29922",
  disconnected: "#f85149",
} as const;

const statusLabel = {
  connected: "Подключён",
  reconnecting: "Переподключение...",
  disconnected: "Нет соединения",
} as const;

export function WSStatusPanel({ onClose, triggerRef }: Props) {
  const { state } = useAppStore();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        ref.current &&
        !ref.current.contains(e.target as Node) &&
        !triggerRef?.current?.contains(e.target as Node)
      ) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose, triggerRef]);

  const color = statusColor[state.wsStatus];
  const label = statusLabel[state.wsStatus];
  const wsUrl = `${crowdWsManager.getPath()}, ${fightWsManager.getPath()}, ${fallWsManager.getPath()}`;

  return (
    <div
      ref={ref}
      style={{
        position: "absolute",
        top: "calc(100% + 8px)",
        right: 0,
        width: 220,
        background: "#161b22",
        border: "1px solid #30363d",
        borderRadius: 8,
        padding: 12,
        zIndex: 50,
      }}
    >
      {/* Status */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: color,
            flexShrink: 0,
            display: "inline-block",
          }}
        />
        <span style={{ fontSize: 12, color, fontWeight: 500 }}>{label}</span>
      </div>

      {state.wsStatus === "reconnecting" && (
        <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 4 }}>
          Попытка {state.wsRetryCount} из 5
        </div>
      )}

      {/* URL */}
      <div
        style={{
          fontSize: 10,
          color: "#6e7681",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          marginBottom: state.wsStatus === "connected" ? 4 : 8,
        }}
      >
        {wsUrl}
      </div>

      {state.wsStatus === "connected" && state.lastUpdate && (
        <div style={{ fontSize: 10, color: "#6e7681" }}>
          Последнее обновление:{" "}
          {state.lastUpdate.toLocaleTimeString("ru", { hour12: false })}
        </div>
      )}

      {state.wsStatus === "disconnected" && (
        <button
          onClick={() => { crowdWsManager.reconnect(); fightWsManager.reconnect(); fallWsManager.reconnect(); onClose(); }}
          style={{
            width: "100%",
            padding: "6px 0",
            borderRadius: 6,
            border: "1px solid #30363d",
            background: "#1c2128",
            color: "#e6edf3",
            fontSize: 11,
            cursor: "pointer",
            fontFamily: "'Inter', sans-serif",
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = "#58a6ff50"; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = "#30363d"; }}
        >
          Переподключиться
        </button>
      )}
    </div>
  );
}
