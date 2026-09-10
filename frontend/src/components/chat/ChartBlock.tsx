/**
 * A chart the model asked for.
 *
 * The assistant can emit a fenced ```kinetic-chart block containing a small
 * JSON spec; anything it can compute from tool output — a book's allocation, a
 * comparison of returns, a sector split — becomes a real chart instead of a
 * list of numbers. Unparseable specs fall back to the raw code block rather
 * than breaking the message.
 */

import { useReducedMotion } from "motion/react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

const PALETTE = ["#cdff9a", "#8fd97a", "#5fb39b", "#3e8e96", "#2c6b78", "#7fd6a4"]

export interface ChartSpec {
  type: "bar" | "line" | "donut"
  title?: string
  unit?: string
  data: { label: string; value: number }[]
}

export function parseChartSpec(raw: string): ChartSpec | null {
  try {
    const parsed = JSON.parse(raw) as ChartSpec
    if (!parsed?.data?.length) return null
    if (!["bar", "line", "donut"].includes(parsed.type)) return null
    return {
      ...parsed,
      data: parsed.data
        .filter((row) => row && typeof row.value === "number" && Number.isFinite(row.value))
        .map((row) => ({ label: String(row.label), value: row.value })),
    }
  } catch {
    return null
  }
}

const AXIS = { stroke: "#7a9295", fontSize: 11, fontFamily: "IBM Plex Mono" }
const TOOLTIP = {
  background: "var(--raised)",
  border: "1px solid var(--line)",
  borderRadius: 10,
  fontFamily: "IBM Plex Mono",
  fontSize: 12,
  color: "var(--ink)",
}

export function ChartBlock({ spec }: { spec: ChartSpec }) {
  const negative = spec.data.some((row) => row.value < 0)
  // Charts draw themselves in; anyone who asked for less motion gets them static.
  const reduced = useReducedMotion()
  const animation = reduced ? 0 : 650

  return (
    <figure className="my-3 rounded-xl border border-border/60 bg-void/40 p-3">
      {spec.title && (
        <figcaption className="label mb-2">
          {spec.title}
          {spec.unit ? ` · ${spec.unit}` : ""}
        </figcaption>
      )}
      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          {spec.type === "donut" ? (
            <PieChart>
              <Pie
                data={spec.data}
                dataKey="value"
                nameKey="label"
                innerRadius="55%"
                outerRadius="85%"
                paddingAngle={2}
                stroke="var(--canvas)"
                strokeWidth={2}
                animationDuration={animation}
                label={({ name, percent }) =>
                  `${name} ${((percent ?? 0) * 100).toFixed(0)}%`
                }
              >
                {spec.data.map((row, index) => (
                  <Cell key={row.label} fill={PALETTE[index % PALETTE.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={TOOLTIP} />
            </PieChart>
          ) : spec.type === "line" ? (
            <LineChart data={spec.data} margin={{ top: 6, right: 8, bottom: 0, left: -14 }}>
              <CartesianGrid stroke="rgba(39,72,78,0.6)" strokeDasharray="3 3" />
              <XAxis dataKey="label" tick={AXIS} axisLine={false} tickLine={false} />
              <YAxis tick={AXIS} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={TOOLTIP} cursor={{ stroke: "rgba(205,255,154,0.3)" }} />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#cdff9a"
                strokeWidth={2}
                dot={{ r: 2.5, fill: "#cdff9a" }}
                animationDuration={reduced ? 0 : 700}
              />
            </LineChart>
          ) : (
            <BarChart data={spec.data} margin={{ top: 6, right: 8, bottom: 0, left: -14 }}>
              <CartesianGrid stroke="rgba(39,72,78,0.6)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" tick={AXIS} axisLine={false} tickLine={false} />
              <YAxis tick={AXIS} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={TOOLTIP} cursor={{ fill: "rgba(205,255,154,0.06)" }} />
              <Bar dataKey="value" radius={[4, 4, 0, 0]} animationDuration={animation}>
                {spec.data.map((row, index) => (
                  <Cell
                    key={row.label}
                    // Losses are ember, gains lime — colour carries meaning only
                    // when the series can actually go negative.
                    fill={negative ? (row.value >= 0 ? "#cdff9a" : "#ff5a2b") : PALETTE[index % PALETTE.length]}
                  />
                ))}
              </Bar>
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </figure>
  )
}
