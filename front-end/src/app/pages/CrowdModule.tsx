import { useState } from "react";
import {
  Users, AlertTriangle, CheckCircle2,
  RefreshCw,
} from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid,
} from "recharts";
import { zones, crowdHistory } from "../data/mock";
import { useTheme } from "../context/ThemeContext";
import { useAppStore } from "../store/appStore";

function ZoneBar({ zone }: { zone: typeof zones[0] }) {
  const { t } = useTheme();
  const pct = Math.round((zone.current / zone.capacity) * 100);
  const isAlert = pct >= zone.alertThreshold;
  const isWarning = pct >= zone.alertThreshold - 10 && !isAlert;
  const color = isAlert ? "#f85149" : isWarning ? "#d29922" : "#3fb950";

  return (
    <div className="p-3 rounded-lg border transition-all"
      style={{
        background: isAlert ? (t.isDark ? "#f8514908" : "#fff5f5") : t.surface,
        borderColor: isAlert ? "#f8514940" : t.border,
      }}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {isAlert
            ? <AlertTriangle style={{ width: 11, height: 11, color: "#f85149" }} />
            : <CheckCircle2 style={{ width: 11, height: 11, color: "#3fb950" }} />}
          <span className="text-xs" style={{ color: t.text, fontWeight: 500 }}>{zone.name}</span>
        </div>
        <span className="text-xs tabular-nums" style={{ color, fontWeight: 600 }}>{pct}%</span>
      </div>
      <div className="h-1.5 rounded-full mb-2 overflow-hidden" style={{ background: t.hover }}>
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${Math.min(pct, 100)}%`, background: color }}
        />
      </div>
      <div className="flex justify-between" style={{ color: t.textMuted, fontSize: 10 }}>
        <span>{zone.current} чел.</span>
        <span>Макс: {zone.capacity}</span>
      </div>
    </div>
  );
}

export function CrowdModule() {
  const { t } = useTheme();
  const { state } = useAppStore();
  const [threshold] = useState(80);
  const [refreshing, setRefreshing] = useState(false);

  const liveZones = zones.map(z => ({
    ...z,
    current: state.zoneStats[z.id]?.current ?? z.current,
  }));

  const totalPeople = state.totalPeople;
  const alertZones = liveZones.filter(z => (z.current / z.capacity * 100) >= z.alertThreshold);

  const handleRefresh = () => {
    setRefreshing(true);
    setTimeout(() => setRefreshing(false), 800);
  };

  return (
    <div className="h-full overflow-y-auto"><div className="p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg" style={{ color: t.text, fontWeight: 600 }}>Скопления людей</h1>
          <p className="text-xs mt-0.5" style={{ color: t.textSec }}>
            Подсчёт людей и анализ плотности по зонам
          </p>
        </div>
        <button onClick={handleRefresh}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border transition-all"
          style={{ background: t.hover, borderColor: t.border, color: t.textSec }}>
          <RefreshCw style={{ width: 11, height: 11, ...(refreshing ? { animation: "spin 0.8s linear" } : {}) }} />
          Обновить
        </button>
      </div>

      {/* Alert banner */}
      {alertZones.length > 0 && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-lg border"
          style={{ background: t.isDark ? "#d2992210" : "#fffbeb", borderColor: "#d2992240" }}>
          <AlertTriangle style={{ width: 13, height: 13, color: "#d29922", flexShrink: 0 }} />
          <span className="text-xs" style={{ color: "#d29922" }}>
            <strong>{alertZones.length} зон</strong> превысили пороговое значение:{" "}
            {alertZones.map(z => z.name).join(", ")}
          </span>
        </div>
      )}

      {/* Metric cards */}
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: "Людей в здании", value: totalPeople, unit: "", color: "#58a6ff", icon: Users, sub: "Все зоны" },
          { label: "Зон с превышением", value: alertZones.length, unit: `/${zones.length}`, color: alertZones.length > 0 ? "#f85149" : "#3fb950", icon: AlertTriangle, sub: `Порог: ${threshold}%` },
        ].map(card => (
          <div key={card.label} className="p-3.5 rounded-lg border" style={{ background: t.surface, borderColor: t.border }}>
            <div className="flex items-center justify-between mb-2">
              <span style={{ fontSize: 10, color: t.textSec }}>{card.label}</span>
              <card.icon style={{ width: 11, height: 11, color: card.color }} />
            </div>
            <div className="tabular-nums" style={{ fontSize: 20, color: card.color, fontWeight: 700, lineHeight: 1 }}>
              {card.value}<span style={{ fontSize: 11, color: t.textMuted }}>{card.unit}</span>
            </div>
            <div style={{ fontSize: 9, color: t.textMuted, marginTop: 4 }}>{card.sub}</div>
          </div>
        ))}
      </div>

      {/* Zone details */}
      <div className="p-4 rounded-lg border" style={{ background: t.surface, borderColor: t.border }}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm" style={{ color: t.text, fontWeight: 500 }}>Детализация по зонам</h3>
          <span style={{ fontSize: 10, color: t.textMuted }}>Порог: {threshold}%</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
          {liveZones.map(zone => (
            <ZoneBar key={zone.id} zone={zone} />
          ))}
        </div>
      </div>

      {/* 24h crowd chart */}
      <div className="p-4 rounded-lg border" style={{ background: t.surface, borderColor: t.border }}>
        <div className="mb-4">
          <h3 className="text-sm" style={{ color: t.text, fontWeight: 500 }}>Посещаемость за 24 ч</h3>
          <p style={{ fontSize: 10, color: t.textSec, marginTop: 2 }}>Динамика входящего потока</p>
        </div>
        <ResponsiveContainer width="100%" height={180}>
          <AreaChart data={crowdHistory}>
            <defs>
              <linearGradient id="grad1" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#1f6feb" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#1f6feb" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={t.borderLight} />
            <XAxis dataKey="time" tick={{ fill: t.textMuted, fontSize: 8 }} tickLine={false} axisLine={false} interval={12} />
            <YAxis tick={{ fill: t.textMuted, fontSize: 8 }} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{ background: t.surface2, border: `1px solid ${t.border}`, borderRadius: 6, fontSize: 11 }}
              labelStyle={{ color: t.textSec }}
              itemStyle={{ color: "#58a6ff" }}
            />
            <Area type="monotone" dataKey="count" stroke="#1f6feb" strokeWidth={2} fill="url(#grad1)" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div></div>
  );
}
