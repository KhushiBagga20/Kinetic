/**
 * The Monte Carlo simulation, drawn as a fan of possible futures.
 *
 * The dark band is where about two thirds of the simulated paths ended up,
 * the faint band nine in ten; the thin grey lines are individual futures and
 * the lime line is the middle one. Under it sits the backtest: how often this
 * kind of signal was right on this stock before. Neither is a promise.
 */

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { useReducedMotion } from "motion/react"
import { History, ShieldAlert } from "lucide-react"

import type { Backtest, Forecast, Simulation } from "@/lib/types"
import { money } from "@/lib/format"
import { cn } from "@/lib/utils"

const SHOWN_PATHS = 12

const pct = (value: number | undefined | null) =>
  value === undefined || value === null ? "—" : `${Math.round(value * 100)}%`

interface FanRow {
  day: number
  outer: [number, number]
  inner: [number, number]
  median: number
  [path: string]: number | [number, number]
}

/** The backend sends {} when there was too little history to simulate. */
function isSimulation(sim: Simulation | Record<string, never>): sim is Simulation {
  return "bands" in sim && Array.isArray(sim.bands) && sim.bands.length > 0
}

/** One chart row per day: both bands, the median and a few sample paths. */
function toRows(sim: Simulation): FanRow[] {
  return sim.bands.map((band, day) => {
    const row: FanRow = {
      day: band.day,
      outer: [band.p5, band.p95],
      inner: [band.p16, band.p84],
      median: band.p50,
    }
    sim.sample_paths.slice(0, SHOWN_PATHS).forEach((path, index) => {
      if (path[day] !== undefined) row[`path${index}`] = path[day]
    })
    return row
  })
}

/** The "no guarantee" notice. Shown wherever a prediction is. */
export function NoGuarantee({ text, className }: { text?: string; className?: string }) {
  return (
    <div
      role="note"
      className={cn(
        "flex items-start gap-2 rounded-lg border border-ember/40 bg-ember/[0.07] px-3 py-2 text-[0.74rem] leading-relaxed text-ember-soft",
        className,
      )}
    >
      <ShieldAlert className="mt-0.5 size-3.5 shrink-0" />
      <span>
        <strong className="font-semibold">No guarantee.</strong>{" "}
        {text ??
          "These are statistical estimates from past prices and today's data. Real prices can move outside every range shown."}
      </span>
    </div>
  )
}

export function NoGuaranteePill() {
  return (
    <span className="rounded-full border border-ember/45 px-2 py-0.5 font-mono text-[0.6rem] uppercase tracking-[0.14em] text-ember-soft">
      No guarantee
    </span>
  )
}

function Odds({
  label,
  value,
  detail,
  tone,
}: {
  label: string
  value: string
  detail?: string
  tone?: "up" | "down"
}) {
  return (
    <div className="rounded-lg border border-border/50 bg-white/[0.015] px-3.5 py-3">
      <div className="label">{label}</div>
      <div
        className={cn(
          "numeric mt-1 text-[1.15rem] text-ink",
          tone === "up" && "text-lime",
          tone === "down" && "text-ember",
        )}
      >
        {value}
      </div>
      {detail && <div className="mt-0.5 text-[0.68rem] text-ink-dim">{detail}</div>}
    </div>
  )
}

function FanTooltip({ row, currency }: { row?: FanRow; currency: string }) {
  if (!row) return null
  return (
    <div className="rounded-lg border border-border bg-raised px-3 py-2 font-mono text-[0.7rem] text-ink-muted">
      <div className="text-ink">{row.day === 0 ? "Today" : `Session +${row.day}`}</div>
      <div>median {money(row.median)} {currency}</div>
      <div>
        68% {money(row.inner[0])} – {money(row.inner[1])}
      </div>
      <div>
        90% {money(row.outer[0])} – {money(row.outer[1])}
      </div>
    </div>
  )
}

function BacktestCard({ backtest, skill }: { backtest: Backtest; skill: number }) {
  const edge = skill >= 0.1
  return (
    <div className="rounded-lg border border-border/50 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <History className="size-4 text-lime" strokeWidth={1.8} />
        <h3 className="text-[0.86rem] font-semibold text-ink">Track record on this stock</h3>
        <span className="label">walk-forward backtest · no peeking ahead</span>
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <div>
          <div className="label">Signal hit rate</div>
          <div className="numeric mt-1 text-[1.05rem] text-ink">{pct(backtest.hit_rate)}</div>
          <p className="text-[0.68rem] text-ink-dim">
            right on {backtest.calls ?? 0} past calls · 50% is a coin flip
          </p>
        </div>
        <div>
          <div className="label">Range accuracy</div>
          <div className="numeric mt-1 text-[1.05rem] text-ink">{pct(backtest.band_coverage)}</div>
          <p className="text-[0.68rem] text-ink-dim">
            of real outcomes landed in the likely range · target 68%
          </p>
        </div>
        <div>
          <div className="label">Trust given to the signal</div>
          <div className="numeric mt-1 text-[1.05rem] text-ink">{skill.toFixed(2)}</div>
          <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-surface">
            <div className="h-full rounded-full bg-lime/70" style={{ width: `${skill * 100}%` }} />
          </div>
        </div>
      </div>

      <p className="mt-3 text-[0.72rem] leading-relaxed text-ink-muted">
        {edge
          ? "The signal has had a real edge here, so the simulation leans with it — gently."
          : "On this stock the signal has been close to a coin flip, so the simulation barely tilts the odds. Read the range, not the direction."}
      </p>
    </div>
  )
}

export function SimulationPanel({ forecast }: { forecast: Forecast }) {
  const reduced = useReducedMotion()
  const sim = forecast.simulation

  if (!isSimulation(sim)) {
    return (
      <p className="text-[0.78rem] text-ink-dim">
        Not enough price history to simulate this symbol honestly.
      </p>
    )
  }

  const rows = toRows(sim)
  const currency = forecast.currency
  const up = sim.probability_up

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Odds
          label={`Chance higher in ${sim.horizon} sessions`}
          value={pct(up)}
          tone={up >= 0.5 ? "up" : "down"}
          detail={`from ${sim.paths.toLocaleString()} simulated futures`}
        />
        <Odds label="Middle outcome" value={money(sim.median_price)} detail={currency} />
        <Odds
          label="Likely range · 68%"
          value={`${money(sim.low_16)} – ${money(sim.high_84)}`}
          detail={currency}
        />
        <Odds
          label="Wide range · 90%"
          value={`${money(sim.low_5)} – ${money(sim.high_95)}`}
          detail={currency}
        />
      </div>

      <div className="h-72 w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={rows} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="var(--line)" strokeOpacity={0.35} vertical={false} />
            <XAxis
              dataKey="day"
              tickFormatter={(day) => (day === 0 ? "now" : `+${day}`)}
              stroke="var(--ink-dim)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              domain={["auto", "auto"]}
              tickFormatter={(value) => money(Number(value), "", 0)}
              stroke="var(--ink-dim)"
              fontSize={11}
              width={70}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              content={({ payload }) => (
                <FanTooltip row={payload?.[0]?.payload as FanRow | undefined} currency={currency} />
              )}
            />
            <Area dataKey="outer" stroke="none" fill="var(--lime)" fillOpacity={0.08} isAnimationActive={!reduced} />
            <Area dataKey="inner" stroke="none" fill="var(--lime)" fillOpacity={0.17} isAnimationActive={!reduced} />
            {sim.sample_paths.slice(0, SHOWN_PATHS).map((_, index) => (
              <Line
                key={index}
                dataKey={`path${index}`}
                stroke="var(--ink-dim)"
                strokeOpacity={0.35}
                strokeWidth={1}
                dot={false}
                activeDot={false}
                isAnimationActive={false}
              />
            ))}
            <Line dataKey="median" stroke="var(--lime)" strokeWidth={2} dot={false} isAnimationActive={!reduced} />
            <ReferenceLine y={sim.start_price} stroke="var(--ink-muted)" strokeDasharray="4 4" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="flex flex-wrap gap-x-5 gap-y-1 font-mono text-[0.7rem] text-ink-dim">
        <span>▲ chance of +5% or more: {pct(sim.probability_up_5)}</span>
        <span>▼ chance of −5% or more: {pct(sim.probability_down_5)}</span>
        <span>daily volatility {(sim.daily_volatility * 100).toFixed(2)}%</span>
        <span>dashed line = today&rsquo;s price</span>
      </div>

      {forecast.backtest.available && <BacktestCard backtest={forecast.backtest} skill={forecast.skill} />}
    </div>
  )
}
