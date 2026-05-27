import { useEffect, useRef } from "react";
import { Sun, Moon, LogOut } from "lucide-react";
import { useTheme } from "../context/ThemeContext";
import { useAuth } from "../hooks/useAuth";
import { useAuthContext } from "../context/AuthContext";

interface Props {
  onClose: () => void;
  triggerRef?: React.RefObject<HTMLButtonElement | null>;
}

function Toggle({ on, onToggle }: { on: boolean; onToggle: () => void }) {
  return (
    <div
      onClick={onToggle}
      style={{
        width: 32,
        height: 18,
        borderRadius: 9,
        background: on ? "#1f6feb" : "#30363d",
        position: "relative",
        cursor: "pointer",
        transition: "background 0.15s",
        flexShrink: 0,
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 2,
          width: 14,
          height: 14,
          borderRadius: "50%",
          background: "white",
          transform: on ? "translateX(16px)" : "translateX(2px)",
          transition: "transform 0.15s",
        }}
      />
    </div>
  );
}

export function SettingsPanel({ onClose, triggerRef }: Props) {
  const { t, toggle } = useTheme();
  const { logout } = useAuth();
  const { user } = useAuthContext();
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
  }, [onClose]);

  const initials = user?.login ? user.login[0].toUpperCase() : "?";

  return (
    <div
      ref={ref}
      style={{
        position: "absolute",
        top: "calc(100% + 8px)",
        right: 0,
        width: 260,
        background: "#161b22",
        border: "1px solid #30363d",
        borderRadius: 10,
        padding: 0,
        overflow: "hidden",
        zIndex: 50,
      }}
    >
      {/* Profile */}
      <div style={{ padding: 16, background: "#1c2128" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: "50%",
              background: "#30363d",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
              fontSize: 15,
              fontWeight: 600,
              color: "#e6edf3",
            }}
          >
            {initials}
          </div>
          <div>
            <div style={{ fontSize: 13, color: "#e6edf3", fontWeight: 500 }}>
              {user?.login ?? "—"}
            </div>
            <div style={{ fontSize: 11, color: "#6e7681", marginTop: 1 }}>
              {user?.role ?? "—"}
            </div>
          </div>
        </div>
      </div>

      <div style={{ height: 1, background: "#21262d" }} />

      {/* Theme */}
      <div style={{ padding: "12px 16px" }}>
        <div style={{ fontSize: 10, color: "#6e7681", letterSpacing: "0.08em", marginBottom: 8 }}>
          ОФОРМЛЕНИЕ
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {t.isDark
            ? <Moon style={{ width: 13, height: 13, color: "#8b949e", flexShrink: 0 }} />
            : <Sun style={{ width: 13, height: 13, color: "#8b949e", flexShrink: 0 }} />}
          <span style={{ fontSize: 12, color: "#8b949e", flex: 1 }}>Тёмная тема</span>
          <Toggle on={t.isDark} onToggle={toggle} />
        </div>
      </div>

      <div style={{ height: 1, background: "#21262d" }} />

      {/* Logout */}
      <div style={{ padding: 8 }}>
        <button
          onClick={logout}
          style={{
            width: "100%",
            padding: "8px 8px",
            borderRadius: 6,
            border: "none",
            background: "transparent",
            display: "flex",
            alignItems: "center",
            gap: 8,
            color: "#f85149",
            fontSize: 12,
            cursor: "pointer",
            fontFamily: "'Inter', sans-serif",
          }}
          onMouseEnter={e => { e.currentTarget.style.background = "#f8514910"; }}
          onMouseLeave={e => { e.currentTarget.style.background = "transparent"; }}
        >
          <LogOut style={{ width: 13, height: 13 }} />
          Выйти из системы
        </button>
      </div>
    </div>
  );
}
