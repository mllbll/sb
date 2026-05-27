import { useState, useEffect } from "react";
import {
  PersonStanding, AlertTriangle, CheckCircle2, Clock,
  Heart, MapPin, User, ChevronRight,
  BarChart3, Check,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Cell,
} from "recharts";
import { fallIncidents, fallByHour } from "../data/mock";
import { useTheme } from "../context/ThemeContext";
import { useAppStore } from "../store/appStore";

const severityConfig = {
  low: { label: "Низкая", color: "#3fb950", bg: "#3fb95015" },
  medium: { label: "Средняя", color: "#d29922", bg: "#d2992215" },
  high: { label: "Высокая", color: "#f0883e", bg: "#f0883e15" },
};

const statusConfig = {
  active: { label: "⚡ Активен", color: "#f85149" },
  responded: { label: "✓ Медики прибыли", color: "#3fb950" },
  resolved: { label: "✓ Закрыт", color: "#6e7681" },
};

function MedicalChecklist({ incidentId }: { incidentId: string }) {
  const { t } = useTheme();
  const [steps, setSteps] = useState([
    { id: 1, label: "Уведомить медицинский персонал", done: true },
    { id: 2, label: "Подтвердить местоположение", done: true },
    { id: 3, label: "Выслать ответную группу", done: false },
    { id: 4, label: "Оценить состояние пострадавшего", done: false },
    { id: 5, label: "Вызвать скорую помощь (при необходимости)", done: false },
    { id: 6, label: "Составить отчёт об инциденте", done: false },
  ]);
  void incidentId;

  return (
    <div className="space-y-1.5">
      {steps.map(step => (
        <div
          key={step.id}
          className="flex items-center gap-2.5 cursor-pointer"
          onClick={() => setSteps(prev => prev.map(s => s.id === step.id ? { ...s, done: !s.done } : s))}
        >
          <div
            className="w-4 h-4 rounded flex items-center justify-center shrink-0 transition-all"
            style={{
              background: step.done ? "#3fb950" : "transparent",
              border: `1px solid ${step.done ? "#3fb950" : t.border}`,
            }}
          >
            {step.done && <Check style={{ width: 9, height: 9, color: "white" }} />}
          </div>
          <span style={{
            fontSize: 11,
            color: step.done ? t.textMuted : t.text,
            textDecoration: step.done ? "line-through" : "none",
          }}>
            {step.label}
          </span>
        </div>
      ))}
    </div>
  );
}

export function FallModule() {
  const { t } = useTheme();
  const { state, dispatch } = useAppStore();
  const [selectedIncident, setSelectedIncident] = useState<string | null>("FLL-0031");
  const [responseTimers, setResponseTimers] = useState<Record<string, number>>({ "FLL-0031": 0 });

  const activeFallIds = state.activeFallIds;
  const activeIncidents = fallIncidents.filter(f => activeFallIds.includes(f.id));

  useEffect(() => {
    const timer = setInterval(() => {
      setResponseTimers(prev => {
        const next = { ...prev };
        activeIncidents.forEach(f => { next[f.id] = (next[f.id] || 0) + 1; });
        return next;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [activeIncidents.length]);

  const formatTimer = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m.toString().padStart(2, "0")}:${sec.toString().padStart(2, "0")}`;
  };

  const handleResolve = (id: string) => {
    dispatch({ type: 'FALL_RESOLVED', payload: { id } });
    if (selectedIncident === id) setSelectedIncident(null);
  };

  const totalFalls = fallIncidents.length;

  return (
    <div className="h-full overflow-y-auto"><div className="p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg" style={{ color: t.text, fontWeight: 600 }}>Детекция падений</h1>
          <p className="text-xs mt-0.5" style={{ color: t.textSec }}>
            Обнаружение падений, оповещение медицинского персонала
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border"
          style={{
            background: activeIncidents.length > 0
              ? (t.isDark ? "#f0883e10" : "#fff7ed")
              : (t.isDark ? "#1a3a1a" : "#f0fdf4"),
            borderColor: activeIncidents.length > 0 ? "#f0883e40" : "#3fb95030",
            color: activeIncidents.length > 0 ? "#f0883e" : "#3fb950",
            fontSize: 12,
          }}>
          <span className="w-1.5 h-1.5 rounded-full inline-block"
            style={{
              background: activeIncidents.length > 0 ? "#f0883e" : "#3fb950",
              animation: activeIncidents.length > 0 ? "pulse 1s infinite" : "none",
            }} />
          {activeIncidents.length > 0 ? `${activeIncidents.length} активных алерта` : "Норма"}
        </div>
      </div>

      {/* Active alerts */}
      {activeIncidents.length > 0 && (
        <div className="space-y-3">
          {activeIncidents.map(incident => (
            <div key={incident.id} className="rounded-xl border p-4 relative overflow-hidden"
              style={{
                background: t.isDark
                  ? "linear-gradient(135deg, #1a0f05, #0d0905)"
                  : "linear-gradient(135deg, #fff7ed, #fffbf5)",
                borderColor: "#f0883e",
                boxShadow: "0 0 20px #f0883e15",
              }}>
              <div className="absolute inset-0 rounded-xl border pointer-events-none"
                style={{ borderColor: "#f0883e", animation: "pulse 2s ease-in-out infinite", opacity: 0.2 }} />

              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-4">
                  <div className="p-3 rounded-xl shrink-0"
                    style={{ background: "#f0883e20", border: "1px solid #f0883e40" }}>
                    <PersonStanding style={{ width: 20, height: 20, color: "#f0883e" }} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs px-2 py-0.5 rounded"
                        style={{ background: "#f0883e", color: "white", fontSize: 10, fontWeight: 600 }}>
                        ⚡ ПАДЕНИЕ ОБНАРУЖЕНО
                      </span>
                      <span className="tabular-nums text-xs px-2 py-0.5 rounded"
                        style={{ background: "#f0883e20", color: "#f0883e", border: "1px solid #f0883e40" }}>
                        {formatTimer(responseTimers[incident.id] || 0)}
                      </span>
                    </div>
                    <h2 className="text-base mb-1.5" style={{ color: t.text, fontWeight: 600 }}>
                      {incident.location}
                    </h2>
                    <div className="flex flex-wrap items-center gap-3 text-xs" style={{ color: t.textSec }}>
                      <span className="flex items-center gap-1">
                        <Clock style={{ width: 10, height: 10 }} />
                        {new Date(incident.timestamp).toLocaleTimeString("ru", { hour12: false })}
                      </span>
                      <span className="flex items-center gap-1">
                        <MapPin style={{ width: 10, height: 10 }} />
                        {incident.id}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex flex-col gap-2 shrink-0">
                  <button
                    onClick={() => handleResolve(incident.id)}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs"
                    style={{ background: t.hover, border: `1px solid ${t.border}`, color: t.textSec, cursor: "pointer" }}>
                    <CheckCircle2 style={{ width: 11, height: 11 }} /> Закрыть инцидент
                  </button>
                </div>
              </div>

              {/* Medical checklist */}
              <div className="mt-4 pt-4 border-t" style={{ borderColor: "#f0883e20" }}>
                <div className="text-xs mb-3 flex items-center gap-2" style={{ color: t.textSec }}>
                  <Heart style={{ width: 11, height: 11, color: "#f85149" }} />
                  Медицинский протокол
                </div>
                <MedicalChecklist incidentId={incident.id} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: "Активных алертов", value: activeIncidents.length, color: activeIncidents.length > 0 ? "#f0883e" : "#3fb950", icon: AlertTriangle, sub: "Требует внимания" },
          { label: "Всего за неделю", value: totalFalls, color: "#58a6ff", icon: BarChart3, sub: "Зафиксировано" },
        ].map(card => (
          <div key={card.label} className="p-3.5 rounded-lg border"
            style={{ background: t.surface, borderColor: t.border }}>
            <div className="flex items-center justify-between mb-2">
              <span style={{ fontSize: 10, color: t.textSec }}>{card.label}</span>
              <card.icon style={{ width: 11, height: 11, color: card.color }} />
            </div>
            <div className="tabular-nums" style={{ fontSize: 22, color: card.color, fontWeight: 700, lineHeight: 1 }}>
              {card.value}
            </div>
            <div style={{ fontSize: 9, color: t.textMuted, marginTop: 4 }}>{card.sub}</div>
          </div>
        ))}
      </div>

      {/* Incident history — full width */}
      <div className="p-4 rounded-lg border" style={{ background: t.surface, borderColor: t.border }}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm" style={{ color: t.text, fontWeight: 500 }}>История инцидентов</h3>
        </div>

        <div className="space-y-2">
          {fallIncidents.map(inc => {
            const sev = severityConfig[inc.severity];
            const isActive = activeFallIds.includes(inc.id);
            const stat = statusConfig[isActive ? "active" : inc.status];
            const isSelected = selectedIncident === inc.id;

            return (
              <div key={inc.id}
                className="rounded-lg border cursor-pointer transition-all"
                style={{
                  background: isSelected ? t.surface2 : isActive ? "#f0883e06" : "transparent",
                  borderColor: isActive ? "#f0883e30" : isSelected ? t.border : t.borderLight,
                }}
                onClick={() => setSelectedIncident(isSelected ? null : inc.id)}>
                <div className="flex items-center gap-3 px-3 py-2.5">
                  <div className="w-2 h-2 rounded-full shrink-0"
                    style={{ background: sev.color, ...(isActive ? { animation: "pulse 1s infinite" } : {}) }} />

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
                        {inc.personType}
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
                        <div style={{ fontSize: 9, color: t.textMuted, marginBottom: 2 }}>Зона</div>
                        <div style={{ fontSize: 11, color: t.text }}>{inc.zone}</div>
                      </div>
                      {inc.responseTime && (
                        <div>
                          <div style={{ fontSize: 9, color: t.textMuted, marginBottom: 2 }}>Время ответа</div>
                          <div style={{ fontSize: 11, color: "#3fb950" }}>{inc.responseTime} мин</div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Falls by hour — full width */}
      <div className="p-4 rounded-lg border" style={{ background: t.surface, borderColor: t.border }}>
        <h3 className="text-sm mb-3" style={{ color: t.text, fontWeight: 500 }}>Падения по часам</h3>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={fallByHour.filter(d => parseInt(d.hour) >= 7 && parseInt(d.hour) <= 19)}>
            <CartesianGrid strokeDasharray="3 3" stroke={t.borderLight} />
            <XAxis dataKey="hour" tick={{ fill: t.textMuted, fontSize: 8 }} tickLine={false} axisLine={false} interval={3} />
            <YAxis tick={{ fill: t.textMuted, fontSize: 8 }} tickLine={false} axisLine={false} width={15} />
            <Tooltip
              contentStyle={{ background: t.surface2, border: `1px solid ${t.border}`, borderRadius: 6, fontSize: 10 }}
              labelStyle={{ color: t.textSec }}
              itemStyle={{ color: "#f0883e" }}
            />
            <Bar dataKey="count" radius={[3, 3, 0, 0]}>
              {fallByHour.filter(d => parseInt(d.hour) >= 7 && parseInt(d.hour) <= 19).map((entry, i) => (
                <Cell key={i} fill={entry.count >= 2 ? "#f85149" : entry.count === 1 ? "#f0883e" : t.hover} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  </div>
  );
}
