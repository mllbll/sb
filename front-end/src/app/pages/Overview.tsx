import { useState } from "react";
import {
  Users, Swords, PersonStanding, AlertTriangle,
  TrendingUp, TrendingDown, Activity,
} from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { zones, systemEvents, crowdHistory, fightIncidents, fallIncidents } from "../data/mock";
import { useTheme } from "../context/ThemeContext";
import { useAppStore } from "../store/appStore";

type FilterType = "all" | "fight" | "fall" | "crowd";

const typeColor: Record<string, string> = {
  fight: "#f85149",
  fall: "#f0883e",
  crowd: "#d29922",
};

const filterConfig: { key: FilterType; label: string; color: string }[] = [
  { key: "all", label: "Все", color: "#58a6ff" },
  { key: "fight", label: "Конфликты", color: "#f85149" },
  { key: "fall", label: "Падения", color: "#f0883e" },
  { key: "crowd", label: "Скопления", color: "#d29922" },
];

export function Overview() {
  const { t } = useTheme();
  const { state } = useAppStore();
  const totalPeople = state.totalPeople;
  const [filter, setFilter] = useState<FilterType>("all");

  const alertZones = zones.filter(z => {
    const current = state.zoneStats[z.id]?.current ?? z.current;
    return (current / z.capacity * 100) >= z.alertThreshold;
  });

  const statCards = [
    {
      label: "Людей в здании",
      value: totalPeople.toLocaleString("ru"),
      icon: Users,
      color: "#58a6ff",
      bg: "#1f6feb15",
      trend: "+12 за час",
      trendUp: true,
    },
    {
      label: "Инцидентов сегодня",
      value: "7",
      icon: AlertTriangle,
      color: "#f0883e",
      bg: "#f0883e15",
      trend: "−3 вчера",
      trendUp: false,
    },
  ];

  const modules = [
    {
      icon: Users,
      name: "Скопления людей",
      desc: "Подсчёт людей, плотность зон",
      color: "#58a6ff",
      bg: "#1f6feb15",
      hasAlert: alertZones.length > 0,
      stats: [
        { label: "Зон", value: zones.length },
        { label: "Превышений", value: alertZones.length },
        { label: "Людей", value: totalPeople },
      ],
    },
    {
      icon: Swords,
      name: "Конфликты",
      desc: "Обнаружение, сигналы охране",
      color: "#f85149",
      bg: "#f8514915",
      hasAlert: state.activeFightId !== null,
      stats: [
        { label: "Сегодня", value: fightIncidents.filter(f => f.timestamp.startsWith("2026-02-20")).length },
        { label: "Всего", value: fightIncidents.length },
        { label: "Отклик", value: "3.8м" },
      ],
    },
    {
      icon: PersonStanding,
      name: "Падения",
      desc: "Детекция, медицинские уведомления",
      color: "#f0883e",
      bg: "#f0883e15",
      hasAlert: state.activeFallIds.length > 0,
      stats: [
        { label: "Активных", value: state.activeFallIds.length },
        { label: "Сегодня", value: fallIncidents.filter(f => f.timestamp.startsWith("2026-02-20")).length },
        { label: "Отклик", value: "2.4м" },
      ],
    },
  ];

  const activeEvts = systemEvents.filter(e => !e.resolved);
  const resolvedEvts = systemEvents.filter(e => e.resolved);
  const sortedEvents = [...activeEvts, ...resolvedEvts];
  const filteredEvents = filter === "all"
    ? sortedEvents
    : sortedEvents.filter(e => e.type === filter);

  return (
    <div className="h-full flex flex-col gap-4 p-4 overflow-hidden">

      {/* Row 1: KPI cards */}
      <div className="grid grid-cols-2 gap-4 shrink-0">
        {statCards.map(card => (
          <div key={card.label} className="p-4 rounded-lg border"
            style={{ background: t.surface, borderColor: t.border }}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs" style={{ color: t.textSec }}>{card.label}</span>
              <div className="p-1.5 rounded" style={{ background: card.bg }}>
                <card.icon style={{ width: 13, height: 13, color: card.color }} />
              </div>
            </div>
            <div className="tabular-nums" style={{ fontSize: 24, color: card.color, fontWeight: 600, lineHeight: 1 }}>
              {card.value}
            </div>
            <div className="mt-1.5 flex items-center gap-1" style={{ fontSize: 11, color: t.textMuted }}>
              {card.trendUp
                ? <TrendingUp style={{ width: 10, height: 10, color: "#3fb950" }} />
                : <TrendingDown style={{ width: 10, height: 10, color: "#f85149" }} />}
              {card.trend}
            </div>
          </div>
        ))}
      </div>

      {/* Row 2: chart + event log */}
      <div className="grid grid-cols-12 gap-4 flex-1 min-h-0">

        {/* Chart col-span-8 */}
        <div
          className="col-span-8 h-full flex flex-col rounded-lg border overflow-hidden"
          style={{ background: t.surface, borderColor: t.border }}
        >
          <div className="shrink-0 px-4 pt-3 pb-2">
            <h3 style={{ color: t.text, fontWeight: 500, fontSize: 13, margin: 0 }}>Динамика посещаемости</h3>
            <p style={{ color: t.textSec, fontSize: 11, marginTop: 2, marginBottom: 0 }}>За 24 часа</p>
          </div>
          <div className="flex-1 min-h-0 px-2 pb-3">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={crowdHistory} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                <defs>
                  <linearGradient id="crowdGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#1f6feb" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#1f6feb" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={t.borderLight} vertical={false} />
                <XAxis dataKey="time" tick={{ fill: t.textMuted, fontSize: 9 }} tickLine={false} axisLine={false} interval={12} height={18} />
                <YAxis tick={{ fill: t.textMuted, fontSize: 9 }} tickLine={false} axisLine={false} width={32} />
                <Tooltip
                  contentStyle={{ background: t.surface2, border: `1px solid ${t.border}`, borderRadius: 8, fontSize: 11, padding: "6px 10px" }}
                  labelStyle={{ color: t.text, fontWeight: 600, marginBottom: 2 }}
                  itemStyle={{ color: "#58a6ff" }}
                  cursor={{ stroke: t.border, strokeWidth: 1 }}
                />
                <Area type="monotone" dataKey="count" stroke="#1f6feb" strokeWidth={2} fill="url(#crowdGrad)" dot={false} activeDot={{ r: 4, fill: "#58a6ff", stroke: t.surface, strokeWidth: 2 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Event log col-span-4 */}
        <div
          className="col-span-4 flex flex-col rounded-lg border min-h-0"
          style={{ background: t.surface, borderColor: t.border }}
        >
          <div className="shrink-0 flex items-center justify-between px-4 pt-3 pb-2 border-b"
            style={{ borderColor: t.borderLight }}>
            <div className="flex items-center gap-2">
              <Activity style={{ width: 13, height: 13, color: "#58a6ff" }} />
              <span style={{ color: t.text, fontWeight: 500, fontSize: 13 }}>Журнал событий</span>
            </div>
            <span
              className="tabular-nums px-1.5 py-0.5 rounded"
              style={{ fontSize: 10, background: "#58a6ff15", color: "#58a6ff" }}
            >
              {filteredEvents.length}
            </span>
          </div>

          <div className="shrink-0 flex items-center gap-1.5 px-4 py-2 border-b" style={{ borderColor: t.borderLight }}>
            {filterConfig.map(f => (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                style={{
                  fontSize: 10,
                  padding: "2px 8px",
                  borderRadius: 99,
                  border: `1px solid ${filter === f.key ? f.color + "60" : t.borderLight}`,
                  background: filter === f.key ? f.color + "15" : "transparent",
                  color: filter === f.key ? f.color : t.textMuted,
                  cursor: "pointer",
                  fontFamily: "'Inter', sans-serif",
                  transition: "all 0.15s",
                }}
              >
                {f.label}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1" style={{ minHeight: 0 }}>
            {filteredEvents.map(evt => (
              <div
                key={evt.id}
                className="px-3 py-2 rounded-md"
                style={{
                  borderLeft: `2px solid ${typeColor[evt.type] ?? "#58a6ff"}`,
                  background: !evt.resolved
                    ? `${typeColor[evt.type] ?? "#58a6ff"}08`
                    : "transparent",
                }}
              >
                <div className="flex items-center justify-between gap-2 mb-0.5">
                  <span style={{ fontSize: 9, color: typeColor[evt.type] ?? "#58a6ff", textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 600 }}>
                    {evt.type === "fight" ? "Конфликт" : evt.type === "fall" ? "Падение" : "Скопление"}
                  </span>
                  <span
                    className="px-1.5 py-0.5 rounded shrink-0"
                    style={{
                      fontSize: 9,
                      background: evt.resolved ? "#3fb95015" : "#f8514915",
                      color: evt.resolved ? "#3fb950" : "#f85149",
                    }}
                  >
                    {evt.resolved ? "Закрыт" : "Активен"}
                  </span>
                </div>
                <p style={{ fontSize: 11, color: t.text, lineHeight: 1.4, margin: 0 }}>{evt.msg}</p>
                <span style={{ fontSize: 9, color: t.textMuted, display: "block", marginTop: 2 }}>{evt.time}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Row 3: module cards */}
      <div className="grid grid-cols-3 gap-4 shrink-0">
        {modules.map(mod => (
          <div
            key={mod.name}
            className="p-3.5 rounded-lg"
            style={{
              background: mod.hasAlert ? `${mod.color}08` : t.surface,
              border: `1px solid ${mod.hasAlert ? mod.color + "60" : t.border}`,
            }}
          >
            <div className="flex items-center gap-2.5 mb-2.5">
              <div className="p-1.5 rounded-lg" style={{ background: mod.bg }}>
                <mod.icon style={{ width: 13, height: 13, color: mod.color }} />
              </div>
              <div>
                <h3 style={{ color: t.text, fontWeight: 500, fontSize: 12, margin: 0 }}>{mod.name}</h3>
                <p style={{ fontSize: 10, color: t.textSec, margin: 0 }}>{mod.desc}</p>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-2 pt-2.5 border-t" style={{ borderColor: t.borderLight }}>
              {mod.stats.map(s => (
                <div key={s.label} className="text-center">
                  <div className="tabular-nums" style={{ color: mod.color, fontWeight: 600, fontSize: 14 }}>{s.value}</div>
                  <div style={{ color: t.textMuted, fontSize: 9, marginTop: 1 }}>{s.label}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
