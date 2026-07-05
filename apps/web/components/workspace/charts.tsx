"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/** Chart palette, derived from the product tokens (tailwind.config.ts). */
export const CHART_COLORS = {
  ink: "#10211b",
  forest: "#3f6e1f",
  moss: "#1f6f52",
  lime: "#d7f075",
  coral: "#ff7657",
} as const;

const SERIES_PALETTE = [
  CHART_COLORS.forest,
  CHART_COLORS.moss,
  CHART_COLORS.lime,
  CHART_COLORS.coral,
  "#6b7f76",
];

const TOOLTIP_STYLE = { fontSize: 12, borderRadius: 8 } as const;

/** Shared calm/minimal horizontal bar chart — single forest accent, no gridlines, value
 * in a tooltip. The template for migrating list-of-bars surfaces to Recharts. */
export function RankedBarChart({
  data,
  labelKey,
  valueKey,
  unit = "",
  height = 120,
  labelWidth = 92,
  color = CHART_COLORS.forest,
}: {
  data: Record<string, string | number>[];
  labelKey: string;
  valueKey: string;
  unit?: string;
  height?: number;
  labelWidth?: number;
  color?: string;
}) {
  if (!data || data.length === 0) return null;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ left: 4, right: 12, top: 2, bottom: 2 }}
      >
        <XAxis type="number" hide />
        <YAxis
          type="category"
          dataKey={labelKey}
          width={labelWidth}
          tick={{ fontSize: 11, fill: "#10211b" }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          cursor={{ fill: "rgba(63,110,31,0.06)" }}
          formatter={(value) => [`${value}${unit}`, valueKey]}
          contentStyle={TOOLTIP_STYLE}
        />
        <Bar dataKey={valueKey} fill={color} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Donut of shares (e.g. signups by platform) with the total in the hole. */
export function ShareDonut({
  data,
  totalLabel,
  height = 180,
}: {
  data: { name: string; value: number }[];
  totalLabel: string;
  height?: number;
}) {
  const rows = (data ?? []).filter((row) => row.value > 0);
  if (rows.length === 0) return null;
  const total = rows.reduce((sum, row) => sum + row.value, 0);
  return (
    <div className="relative" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={rows}
            dataKey="value"
            nameKey="name"
            innerRadius="62%"
            outerRadius="88%"
            paddingAngle={2}
            strokeWidth={0}
          >
            {rows.map((row, index) => (
              <Cell
                key={row.name}
                fill={SERIES_PALETTE[index % SERIES_PALETTE.length]}
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value, name) => {
              const v = Number(value ?? 0);
              return [
                `${v.toLocaleString()} (${((v / total) * 100).toFixed(0)}%)`,
                String(name),
              ];
            }}
            contentStyle={TOOLTIP_STYLE}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <p className="text-xl font-semibold text-ink">{total.toLocaleString()}</p>
        <p className="font-mono text-[10px] uppercase tracking-wide text-ink/50">
          {totalLabel}
        </p>
      </div>
    </div>
  );
}

/** Grouped conversion-rate bars per platform: CTR and click→signup, in percent. */
export function ConversionBars({
  data,
  height = 190,
}: {
  data: { platform: string; ctr: number; conv: number }[];
  height?: number;
}) {
  if (!data || data.length === 0) return null;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ left: 0, right: 8, top: 8, bottom: 0 }} barGap={3}>
        <XAxis
          dataKey="platform"
          tick={{ fontSize: 11, fill: "#10211b" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 10, fill: "#6b7f76" }}
          tickFormatter={(value: number) => `${value}%`}
          axisLine={false}
          tickLine={false}
          width={34}
        />
        <Tooltip
          cursor={{ fill: "rgba(63,110,31,0.06)" }}
          formatter={(value, name) => [
            `${Number(value ?? 0).toFixed(1)}%`,
            String(name) === "ctr" ? "Impressions → clicks" : "Clicks → signups",
          ]}
          contentStyle={TOOLTIP_STYLE}
        />
        <Legend
          formatter={(value: string) =>
            value === "ctr" ? "Impressions → clicks" : "Clicks → signups"
          }
          wrapperStyle={{ fontSize: 11 }}
        />
        <Bar dataKey="ctr" fill={CHART_COLORS.moss} radius={[4, 4, 0, 0]} />
        <Bar
          dataKey="conv"
          fill={CHART_COLORS.lime}
          stroke={CHART_COLORS.forest}
          strokeWidth={1}
          radius={[4, 4, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Cumulative momentum area — e.g. signups accumulating as posts ship. */
export function MomentumArea({
  data,
  height = 170,
  unit = "signups",
}: {
  data: { date: string; cumulative: number }[];
  height?: number;
  unit?: string;
}) {
  if (!data || data.length < 2) return null;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ left: 0, right: 12, top: 8, bottom: 0 }}>
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10, fill: "#6b7f76" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 10, fill: "#6b7f76" }}
          axisLine={false}
          tickLine={false}
          width={34}
          allowDecimals={false}
        />
        <Tooltip
          formatter={(value) => [`${Number(value ?? 0).toLocaleString()} ${unit}`, "Total"]}
          contentStyle={TOOLTIP_STYLE}
        />
        <Area
          type="monotone"
          dataKey="cumulative"
          stroke={CHART_COLORS.forest}
          strokeWidth={2}
          fill="rgba(215, 240, 117, 0.45)"
          dot={{ r: 2.5, fill: CHART_COLORS.forest, strokeWidth: 0 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
