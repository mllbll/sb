import { useState, useRef } from "react";
import { Outlet, NavLink } from "react-router";
import {
  Activity, Users, Swords, PersonStanding,
  Settings, ChevronRight, ChevronDown, Wifi, WifiOff,
} from "lucide-react";
import { cameras } from "../data/mock";
import { useTheme } from "../context/ThemeContext";
import { useAppStore } from "../store/appStore";
import { useWebSocket } from "../hooks/useWebSocket";
import { useMockData } from "../hooks/useMockData";
import { SettingsPanel } from "./SettingsPanel";
import { WSStatusPanel } from "./WSStatusPanel";
import reuLogoDark from "../../assets/reu_logo_dark.png";
import reuLogoLight from "../../assets/reu_logo_light.png";

const navItems = [
  { to: "/", icon: Activity, label: "Обзор", end: true },
  { to: "/crowd", icon: Users, label: "Скопления людей", end: false },
  { to: "/fight", icon: Swords, label: "Конфликты", end: false },
  { to: "/fall", icon: PersonStanding, label: "Падения", end: false },
];

const wsStatusColor = {
  connected: "#3fb950",
  reconnecting: "#d29922",
  disconnected: "#f85149",
} as const;

const wsStatusLabel = {
  connected: "WS",
  reconnecting: "WS",
  disconnected: "офлайн",
} as const;

export function Layout() {
  const { t } = useTheme();
  const { state } = useAppStore();
  const [camerasOpen, setCamerasOpen] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [wsOpen, setWsOpen] = useState(false);

  const settingsBtnRef = useRef<HTMLButtonElement>(null);
  const wsBtnRef = useRef<HTMLButtonElement>(null);

  useWebSocket();
  useMockData();

  const onlineCams = Object.values(state.cameraStatuses).filter(Boolean).length;
  const totalCams = Object.keys(state.cameraStatuses).length || cameras.length;

  const wsColor = wsStatusColor[state.wsStatus];
  const wsLabel = wsStatusLabel[state.wsStatus];

  return (
    <div
      className="flex flex-col h-screen overflow-hidden"
      style={{ background: t.bg, color: t.text, fontFamily: "'Inter', sans-serif", transition: "background 0.2s, color 0.2s" }}
    >
      {/* Top header */}
      <header
        className="shrink-0 flex items-center px-5 h-12 border-b z-20"
        style={{ background: t.surface, borderColor: t.border, transition: "background 0.2s, border-color 0.2s" }}
      >
        {/* Logo — fixed width matching sidebar */}
        <div style={{ width: 208, minWidth: 208, flexShrink: 0, display: "flex", alignItems: "center", gap: 10 }}>
          <img
            src={t.isDark ? reuLogoDark : reuLogoLight}
            alt="РЭУ им. Г.В. Плеханова"
            style={{
              height: 30,
              width: "auto",
              borderRadius: 5,
              display: "block",
              flexShrink: 0,
              boxShadow: t.isDark
                ? "0 0 0 1px rgba(88,166,255,0.25), 0 0 8px rgba(88,166,255,0.12)"
                : "0 0 0 1px rgba(0,0,0,0.08), 0 0 6px rgba(31,111,235,0.10)",
            }}
          />
          <div style={{ width: 1, height: 20, background: t.border, flexShrink: 0 }} />
          <span style={{ color: t.text, fontWeight: 600, fontSize: 14, whiteSpace: "nowrap" }}>
            REU Secure
          </span>
        </div>

        {/* Right */}
        <div className="ml-auto flex items-center gap-3">
          {/* WS indicator — clickable */}
          <div style={{ position: "relative" }}>
            <button
              ref={wsBtnRef}
              onClick={() => { setWsOpen(o => !o); setSettingsOpen(false); }}
              className="flex items-center gap-1.5"
              style={{ fontSize: 12, color: wsColor, background: "none", border: "none", padding: 0, cursor: "pointer" }}
            >
              <span
                className="w-1.5 h-1.5 rounded-full inline-block"
                style={{
                  background: wsColor,
                  ...(state.wsStatus === "connected"
                    ? { animation: "pulse 2s ease-in-out infinite" }
                    : state.wsStatus === "reconnecting"
                    ? { animation: "pulse 0.8s ease-in-out infinite" }
                    : {}),
                }}
              />
              <span>{wsLabel}</span>
            </button>
            {wsOpen && (
              <WSStatusPanel
                onClose={() => setWsOpen(false)}
                triggerRef={wsBtnRef}
              />
            )}
          </div>

          {/* Settings */}
          <div style={{ position: "relative" }}>
            <button
              ref={settingsBtnRef}
              onClick={() => { setSettingsOpen(o => !o); setWsOpen(false); }}
              style={{ background: "none", border: "none", padding: 0, cursor: "pointer", display: "flex", alignItems: "center" }}
              aria-label="Настройки"
            >
              <Settings className="w-4 h-4" style={{ color: t.textMuted }} />
            </button>
            {settingsOpen && (
              <SettingsPanel
                onClose={() => setSettingsOpen(false)}
                triggerRef={settingsBtnRef}
              />
            )}
          </div>
        </div>
      </header>

      {/* Body */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Sidebar */}
        <aside
          className="w-52 shrink-0 flex flex-col overflow-y-auto border-r"
          style={{ background: t.surface, borderColor: t.border, transition: "background 0.2s", minWidth: 208 }}
        >
          {/* Module nav */}
          <div className="p-2 pt-4">
            <p
              className="px-2 mb-2 uppercase tracking-widest"
              style={{ fontSize: 10, color: t.textMuted, fontWeight: 500 }}
            >
              Модули
            </p>
            {navItems.map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className="flex items-center gap-2 px-2.5 py-2 rounded-md mb-0.5 transition-all"
                style={({ isActive }) => ({
                  background: isActive ? "#1f6feb20" : "transparent",
                  color: isActive ? "#58a6ff" : t.textSec,
                  borderLeft: isActive ? "2px solid #1f6feb" : "2px solid transparent",
                  fontSize: 13,
                  textDecoration: "none",
                })}
              >
                <item.icon style={{ width: 14, height: 14 }} />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </div>

          <div className="mx-3 my-2 border-t" style={{ borderColor: t.borderLight }} />

          {/* Cameras list */}
          <div className="p-2">
            <button
              className="flex items-center justify-between w-full px-2 mb-1.5"
              onClick={() => setCamerasOpen(!camerasOpen)}
              style={{ fontSize: 10, color: t.textMuted, fontWeight: 500 }}
            >
              <span className="uppercase tracking-widest">Камеры</span>
              <div className="flex items-center gap-1">
                <span style={{ color: "#3fb950", fontSize: 9 }}>{onlineCams}/{totalCams}</span>
                {camerasOpen
                  ? <ChevronDown style={{ width: 10, height: 10 }} />
                  : <ChevronRight style={{ width: 10, height: 10 }} />}
              </div>
            </button>

            {camerasOpen && (
              <div className="space-y-0.5">
                {cameras.map(cam => (
                  <div
                    key={cam.id}
                    className="flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-colors"
                    style={{ fontSize: 11, color: t.textSec }}
                    onMouseEnter={e => (e.currentTarget.style.background = t.hover)}
                    onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                  >
                    {(state.cameraStatuses[cam.id] ?? cam.online)
                      ? <Wifi style={{ width: 9, height: 9, color: "#3fb950", flexShrink: 0 }} />
                      : <WifiOff style={{ width: 9, height: 9, color: "#f85149", flexShrink: 0 }} />}
                    <span className="truncate">{cam.name}</span>
                    <span className="ml-auto shrink-0" style={{ fontSize: 9, color: t.textMuted }}>
                      {cam.id.replace("cam-", "")}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 min-h-0 overflow-hidden" style={{ background: t.bg, transition: "background 0.2s" }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
