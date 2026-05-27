import { useState, useEffect } from "react";
import {
  Swords, AlertTriangle, CheckCircle2, Clock, Shield,
  MapPin, User, ChevronRight,
  TrendingUp, Check,
} from "lucide-react";
import { fightIncidents } from "../data/mock";
import { useTheme } from "../context/ThemeContext";
import { useAppStore } from "../store/appStore";

const severityConfig = {
  low: { label: "Низкая", color: "#3fb950", bg: "#3fb95015" },
  medium: { label: "Средняя", color: "#d29922", bg: "#d2992215" },
  high: { label: "Высокая", color: "#f0883e", bg: "#f0883e15" },
  critical: { label: "Критическая", color: "#f85149", bg: "#f8514915" },
};

const statusConfig = {
  active: { label: "Активен", color: "#f85149" },
  resolved: { label: "Разрешён", color: "#3fb950" },
  pending: { label: "Ожидание", color: "#d29922" },
};

interface AlertDetails {
  location: string;
  participants: number;
  since: Date;
  severity: "high" | "critical";
}

const INITIAL_ALERT_DETAILS: AlertDetails = {
  location: "Коридор 2 · Корпус А",
  participants: 3,
  since: new Date(Date.now() - 38000),
  severity: "high",
};

export function FightModule() {
  const { t } = useTheme();
  const { state, dispatch } = useAppStore();
  const activeFightId = state.activeFightId;

  const [alertDetails, setAlertDetails] = useState<AlertDetails | null>(
    activeFightId ? INITIAL_ALERT_DETAILS : null
  );
  const [selectedIncident, setSelectedIncident] = useState<string | null>(null);
  const [securityDispatched, setSecurityDispatched] = useState(false);
  const [alertTimer, setAlertTimer] = useState(38);
  const [dismissing, setDismissing] = useState(false);

  // Sync alertDetails when store activeFightId changes
  useEffect(() => {
    if (activeFightId && !alertDetails) {
      setAlertDetails({
        location: "Обнаружено системой мониторинга",
        participants: 2,
        since: new Date(),
        severity: "high",
      });
      setAlertTimer(0);
      setSecurityDispatched(false);
    } else if (!activeFightId) {
      setAlertDetails(null);
    }
  }, [activeFightId]);

  useEffect(() => {
    if (!activeFightId) return;
    const timer = setInterval(() => setAlertTimer(s => s + 1), 1000);
    return () => clearInterval(timer);
  }, [activeFightId]);

  const resolveAlert = () => {
    if (!activeFightId) return;
    setDismissing(true);
    setTimeout(() => {
      dispatch({ type: 'FIGHT_RESOLVED', payload: { id: activeFightId } });
      setSecurityDispatched(false);
      setAlertTimer(0);
      setDismissing(false);
    }, 600);
  };

  const today = fightIncidents.filter(f => f.timestamp.startsWith("2026-02-20"));

  const formatTimer = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <div className="h-full overflow-y-auto"><div className="p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg" style={{ color: t.text, fontWeight: 600 }}>Детекция конфликтов</h1>
          <p className="text-xs mt-0.5" style={{ color: t.textSec }}>
            Обнаружение агрессивного поведения и физических конфликтов
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border"
          style={{
            background: activeFightId
              ? (t.isDark ? "#f8514910" : "#fff5f5")
              : (t.isDark ? "#1a3a1a" : "#f0fdf4"),
            borderColor: activeFightId ? "#f8514940" : "#3fb95030",
            color: activeFightId ? "#f85149" : "#3fb950",
            fontSize: 12,
          }}>
          <span className="w-1.5 h-1.5 rounded-full inline-block"
            style={{ background: activeFightId ? "#f85149" : "#3fb950", animation: "pulse 1.5s infinite" }} />
          {activeFightId ? "ТРЕВОГА АКТИВНА" : "Мониторинг активен"}
        </div>
      </div>

      {/* Active alert banner */}
      {activeFightId && alertDetails && (
        <div className="rounded-lg border p-4 relative overflow-hidden"
          style={{
            background: t.isDark
              ? "linear-gradient(135deg, #1a0808, #0d0505)"
              : "linear-gradient(135deg, #fff5f5, #fffafa)",
            borderColor: "#f85149",
            boxShadow: "0 0 20px #f8514915",
            opacity: dismissing ? 0 : 1,
            transition: "opacity 0.5s",
          }}>
          <div className="absolute inset-0 rounded-lg border pointer-events-none"
            style={{ borderColor: "#f85149", animation: "pulse 2s ease-in-out infinite", opacity: 0.3 }} />

          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg shrink-0"
                style={{ background: "#f8514920", border: "1px solid #f8514940" }}>
                <Swords style={{ width: 18, height: 18, color: "#f85149" }} />
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs px-2 py-0.5 rounded"
                    style={{ background: "#f85149", color: "white", fontSize: 10, fontWeight: 600, letterSpacing: "0.05em" }}>
                    ⚡ КОНФЛИКТ ОБНАРУЖЕН
                  </span>
                  <span className="text-xs tabular-nums px-2 py-0.5 rounded"
                    style={{ background: "#f8514920", color: "#f85149", border: "1px solid #f8514940" }}>
                    {formatTimer(alertTimer)}
                  </span>
                </div>
                <h2 className="text-base mb-1" style={{ color: t.text, fontWeight: 600 }}>
                  {alertDetails.location}
                </h2>
                <div className="flex items-center gap-4 text-xs" style={{ color: t.textSec }}>
                  <span className="flex items-center gap-1">
                    <User style={{ width: 10, height: 10 }} />
                    {alertDetails.participants} участника
                  </span>
                  <span className="flex items-center gap-1">
                    <MapPin style={{ width: 10, height: 10 }} />
                    ID: {activeFightId}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock style={{ width: 10, height: 10 }} />
                    {alertDetails.since.toLocaleTimeString("ru", { hour12: false })}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-2 shrink-0">
              <button
                onClick={() => setSecurityDispatched(true)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs transition-all"
                style={{
                  background: securityDispatched ? "#3fb95020" : "#f8514920",
                  border: `1px solid ${securityDispatched ? "#3fb95050" : "#f8514950"}`,
                  color: securityDispatched ? "#3fb950" : "#f85149",
                  cursor: securityDispatched ? "default" : "pointer",
                }}>
                {securityDispatched
                  ? <><Check style={{ width: 11, height: 11 }} /> Охрана уведомлена</>
                  : <><Shield style={{ width: 11, height: 11 }} /> Вызвать охрану</>}
              </button>
              <button
                onClick={resolveAlert}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs"
                style={{ background: t.hover, border: `1px solid ${t.border}`, color: t.textSec }}>
                <CheckCircle2 style={{ width: 11, height: 11 }} /> Закрыть инцидент
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: "Сегодня", value: today.length + (activeFightId ? 1 : 0), color: "#f85149", icon: Swords, sub: "Инцидентов" },
          { label: "Всего за период", value: fightIncidents.length, color: "#58a6ff", icon: TrendingUp, sub: "7 дней" },
        ].map(card => (
          <div key={card.label} className="p-3.5 rounded-lg border" style={{ background: t.surface, borderColor: t.border }}>
            <div className="flex items-center justify-between mb-2">
              <span style={{ fontSize: 10, color: t.textSec }}>{card.label}</span>
              <card.icon style={{ width: 11, height: 11, color: card.color }} />
            </div>
            <div className="tabular-nums" style={{ fontSize: 22, color: card.color, fontWeight: 700, lineHeight: 1 }}>{card.value}</div>
            <div style={{ fontSize: 9, color: t.textMuted, marginTop: 4 }}>{card.sub}</div>
          </div>
        ))}
      </div>

      {/* Incident log — full width */}
      <div className="p-4 rounded-lg border" style={{ background: t.surface, borderColor: t.border }}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm" style={{ color: t.text, fontWeight: 500 }}>Журнал инцидентов</h3>
          <span style={{ fontSize: 10, color: t.textMuted }}>Последние 7 дней</span>
        </div>

        <div className="space-y-2">
          {fightIncidents.map(inc => {
            const sev = severityConfig[inc.severity];
            const stat = statusConfig[inc.status];
            const isSelected = selectedIncident === inc.id;

            return (
              <div key={inc.id}
                className="rounded-lg border cursor-pointer transition-all"
                style={{
                  background: isSelected ? t.surface2 : "transparent",
                  borderColor: isSelected ? t.border : t.borderLight,
                }}
                onClick={() => setSelectedIncident(isSelected ? null : inc.id)}>
                <div className="flex items-center gap-3 px-3 py-2.5">
                  <div className="w-2 h-2 rounded-full shrink-0" style={{ background: sev.color }} />
                  <span className="shrink-0 tabular-nums" style={{ fontSize: 10, color: "#58a6ff", minWidth: 72 }}>
                    {inc.id}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs truncate" style={{ color: t.text }}>{inc.location}</span>
                      <span className="shrink-0 px-1.5 py-0.5 rounded"
                        style={{ background: sev.bg, color: sev.color, fontSize: 9 }}>
                        {sev.label}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-0.5" style={{ fontSize: 10, color: t.textMuted }}>
                      <span className="flex items-center gap-1">
                        <Clock style={{ width: 9, height: 9 }} />
                        {new Date(inc.timestamp).toLocaleString("ru", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                      </span>
                      <span className="flex items-center gap-1">
                        <User style={{ width: 9, height: 9 }} />
                        {inc.participants} чел.
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span style={{ fontSize: 10, color: stat.color }}>{stat.label}</span>
                    {inc.responseTime && (
                      <span style={{ fontSize: 10, color: t.textMuted }}>{inc.responseTime} мин</span>
                    )}
                    <ChevronRight style={{
                      width: 12, height: 12, color: t.border,
                      transform: isSelected ? "rotate(90deg)" : undefined,
                      transition: "transform 0.2s",
                    }} />
                  </div>
                </div>

                {isSelected && (
                  <div className="px-4 pb-3 pt-1 border-t" style={{ borderColor: t.borderLight }}>
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <div style={{ fontSize: 9, color: t.textMuted, marginBottom: 2 }}>Камера</div>
                        <div style={{ fontSize: 11, color: t.text }}>{inc.cameraId}</div>
                      </div>
                      <div>
                        <div style={{ fontSize: 9, color: t.textMuted, marginBottom: 2 }}>Охрана</div>
                        <div style={{ fontSize: 11, color: inc.securityNotified ? "#3fb950" : t.textMuted }}>
                          {inc.securityNotified ? "✓ Уведомлена" : "Не вызвана"}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: 9, color: t.textMuted, marginBottom: 2 }}>Полиция</div>
                        <div style={{ fontSize: 11, color: inc.policeNotified ? "#f0883e" : t.textMuted }}>
                          {inc.policeNotified ? "✓ Вызвана" : "Не вызвана"}
                        </div>
                      </div>
                      <div className="col-span-3">
                        <div style={{ fontSize: 9, color: t.textMuted, marginBottom: 2 }}>Примечания</div>
                        <div style={{ fontSize: 11, color: t.textSec }}>{inc.notes}</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  </div>
  );
}
