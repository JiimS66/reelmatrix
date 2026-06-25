"use client";

import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/** Shared calm/minimal horizontal bar chart — single forest accent, no gridlines, value
 * in a tooltip. The template for migrating list-of-bars surfaces to Recharts. */
export function RankedBarChart({
  data,
  labelKey,
  valueKey,
  unit = "",
  height = 120,
  labelWidth = 92,
}: {
  data: Record<string, string | number>[];
  labelKey: string;
  valueKey: string;
  unit?: string;
  height?: number;
  labelWidth?: number;
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
          contentStyle={{ fontSize: 12, borderRadius: 8 }}
        />
        <Bar dataKey={valueKey} fill="#3f6e1f" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
