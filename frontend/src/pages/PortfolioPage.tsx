/**
 * Portfolio — the holdings, and the question only a local model can answer:
 * *what in my book does this event actually touch?*
 */

import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { AnimatePresence, motion, useReducedMotion } from "motion/react"
import { Lock, Plus, Radar, Sparkles, Trash2 } from "lucide-react"
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip as ReTooltip } from "recharts"
import { toast } from "sonner"

import { Delta } from "@/components/market/Delta"
import { StatCard } from "@/components/market/StatCard"
import { NumberFlow } from "@/components/ui/number-flow"
import { Rise, Stagger, StaggerItem } from "@/components/ui/motion-primitives"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { usePortfolio, usePortfolioMutations } from "@/hooks/use-kinetic"
import { compact, money, percent } from "@/lib/format"
import { cn } from "@/lib/utils"

const SLICE_COLORS = ["#cdff9a", "#8fd97a", "#5fb39b", "#3e8e96", "#2c6b78", "#203d43"]

export function PortfolioPage() {
  const navigate = useNavigate()
  const { data, isLoading } = usePortfolio()
  const reduced = useReducedMotion()
  const { add, remove, exposure } = usePortfolioMutations()

  const [symbol, setSymbol] = useState("")
  const [quantity, setQuantity] = useState("")
  const [cost, setCost] = useState("")
  const [topic, setTopic] = useState("")

  const positions = data?.positions ?? []
  const summary = data?.summary
  const base = summary?.base_currency ?? "INR"

  const slices = positions.map((row, index) => ({
    name: row.symbol,
    value: row.value_in_base ?? 0,
    fill: SLICE_COLORS[index % SLICE_COLORS.length],
  }))

  return (
    <div className="space-y-6">
      <Rise className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[1.8rem] font-semibold tracking-[-0.035em] text-ink">Portfolio</h1>
          <p className="mt-1.5 flex items-center gap-1.5 text-[0.78rem] text-ink-muted">
            <Lock className="size-3" />
            Stored on this machine · priced live · base {base}
          </p>
        </div>
      </Rise>

      {summary && positions.length > 0 && (
        <Stagger className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StaggerItem>
            <StatCard
              label="Market value"
              accent
              value={<NumberFlow value={summary.market_value} format={(v) => compact(v)} />}
              detail={`${summary.holdings} holdings`}
            />
          </StaggerItem>
          <StaggerItem>
            <StatCard
              label="Unrealised"
              value={
                <NumberFlow
                  value={summary.unrealised}
                  format={(v) => `${v >= 0 ? "+" : ""}${money(v, "", 0)}`}
                />
              }
              detail={<Delta value={summary.unrealised_percent} />}
            />
          </StaggerItem>
          <StaggerItem>
            <StatCard
              label="Today"
              value={
                <NumberFlow
                  value={summary.day_change}
                  format={(v) => `${v >= 0 ? "+" : ""}${money(v, "", 0)}`}
                />
              }
              detail={<Delta value={summary.day_change_percent} />}
            />
          </StaggerItem>
          <StaggerItem>
            <StatCard
              label="Largest position"
              value={summary.largest_position ?? "—"}
              detail={`${summary.largest_weight?.toFixed(1)}% of the book`}
            />
          </StaggerItem>
        </Stagger>
      )}

      <div className="grid items-start gap-5 lg:grid-cols-[1.5fr_1fr]">
        {/* -- holdings ---------------------------------------------------- */}
        <Rise delay={0.05} className="glass overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4">
            <h2 className="section-title">Holdings</h2>
            <span className="label">{positions.length} positions</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-[0.8rem]">
              <thead>
                <tr className="border-y border-border/50 text-left">
                  {["Symbol", "Qty", "Avg cost", "Last", "Unrealised", "Today", "Weight", ""].map(
                    (heading) => (
                      <th key={heading} scope="col" className="label px-4 py-2 font-normal">
                        {heading}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                <AnimatePresence initial={false}>
                  {positions.map((row) => (
                    <motion.tr
                      key={row.symbol}
                      layout
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0, height: 0 }}
                      className="group border-b border-border/30 transition-colors hover:bg-lime/[0.04]"
                    >
                      <th scope="row" className="px-4 py-3 text-left font-normal">
                        <button
                          onClick={() =>
                            navigate(`/research?symbol=${encodeURIComponent(row.symbol)}`)
                          }
                          className="text-left"
                        >
                          <div className="font-mono text-[0.82rem] text-ink transition-colors group-hover:text-lime">
                            {row.symbol}
                          </div>
                          <div className="max-w-40 truncate text-[0.7rem] text-ink-dim">
                            {row.name}
                          </div>
                        </button>
                      </th>
                      <td className="numeric px-4 py-3 text-ink-muted">{row.quantity}</td>
                      <td className="numeric px-4 py-3 text-ink-muted">
                        {money(row.average_cost)}
                      </td>
                      <td className="numeric px-4 py-3 text-ink">
                        {money(row.price)} <span className="text-ink-dim">{row.currency}</span>
                      </td>
                      <td
                        className={cn(
                          "numeric px-4 py-3",
                          (row.unrealised ?? 0) >= 0 ? "text-lime" : "text-ember",
                        )}
                      >
                        {row.unrealised === null ? "—" : `${row.unrealised >= 0 ? "+" : ""}${money(row.unrealised, "", 0)}`}
                        <span className="ml-1 text-[0.7rem] opacity-70">
                          {percent(row.unrealised_percent, 1)}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <Delta value={row.day_change_percent} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Progress value={row.weight} className="h-1 w-12" />
                          <span className="numeric text-[0.72rem] text-ink-muted">
                            {row.weight.toFixed(1)}%
                          </span>
                        </div>
                      </td>
                      <td className="px-2 py-3">
                        <button
                          aria-label={`Remove ${row.symbol}`}
                          onClick={() =>
                            remove.mutate(row.symbol, {
                              onSuccess: () => toast.success(`${row.symbol} removed`),
                            })
                          }
                          className="rounded-md p-1.5 text-ink-dim opacity-0 transition-all hover:text-ember group-hover:opacity-100"
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              </tbody>
            </table>

            {!positions.length && !isLoading && (
              <p className="px-5 py-10 text-center text-[0.84rem] text-ink-dim">
                No holdings yet. Add one below — it stays on this machine.
              </p>
            )}
          </div>

          {/* -- add ------------------------------------------------------- */}
          <form
            className="grid gap-3 border-t border-border/50 px-5 py-4 sm:grid-cols-[2fr_1fr_1fr_auto]"
            onSubmit={(event) => {
              event.preventDefault()
              add.mutate(
                {
                  symbol,
                  quantity: Number(quantity),
                  average_cost: Number(cost) || 0,
                },
                {
                  onSuccess: () => {
                    toast.success(`${symbol.toUpperCase()} added`)
                    setSymbol("")
                    setQuantity("")
                    setCost("")
                  },
                  onError: (error) => toast.error(String(error)),
                },
              )
            }}
          >
            <div>
              <Label htmlFor="symbol" className="label">
                Symbol or company
              </Label>
              <Input
                id="symbol"
                value={symbol}
                onChange={(event) => setSymbol(event.target.value)}
                placeholder="reliance, INFY.NS…"
                className="mt-1 h-9"
              />
            </div>
            <div>
              <Label htmlFor="qty" className="label">
                Quantity
              </Label>
              <Input
                id="qty"
                type="number"
                step="any"
                value={quantity}
                onChange={(event) => setQuantity(event.target.value)}
                className="mt-1 h-9 font-mono"
              />
            </div>
            <div>
              <Label htmlFor="cost" className="label">
                Avg cost
              </Label>
              <Input
                id="cost"
                type="number"
                step="any"
                value={cost}
                onChange={(event) => setCost(event.target.value)}
                className="mt-1 h-9 font-mono"
              />
            </div>
            <Button type="submit" className="mt-auto h-9" disabled={add.isPending}>
              <Plus className="size-4" />
              Add
            </Button>
          </form>
        </Rise>

        {/* -- allocation + exposure --------------------------------------- */}
        <div className="space-y-5">
          {positions.length > 0 && (
            <Rise delay={0.1} className="glass p-5">
              <h2 className="section-title">Allocation</h2>
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={slices}
                      dataKey="value"
                      innerRadius="58%"
                      outerRadius="88%"
                      paddingAngle={2}
                      stroke="var(--canvas)"
                      strokeWidth={2}
                      animationDuration={reduced ? 0 : 700}
                    >
                      {slices.map((slice) => (
                        <Cell key={slice.name} fill={slice.fill} />
                      ))}
                    </Pie>
                    <ReTooltip
                      contentStyle={{
                        background: "var(--raised)",
                        border: "1px solid var(--line)",
                        borderRadius: 10,
                        fontFamily: "IBM Plex Mono",
                        fontSize: 12,
                      }}
                      formatter={(value) => [compact(Number(value), base), ""] as [string, string]}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-1 space-y-1">
                {Object.entries(summary?.sectors ?? {}).map(([sector, share]) => (
                  <div key={sector} className="flex items-center justify-between text-[0.76rem]">
                    <span className="text-ink-muted">{sector}</span>
                    <span className="numeric text-ink-dim">{share.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </Rise>
          )}

          <Rise delay={0.15} className="glass p-5">
            <div className="flex items-center gap-2">
              <Radar className="size-4 text-lime" strokeWidth={1.8} />
              <h2 className="text-[0.95rem] font-semibold text-ink">Exposure check</h2>
            </div>
            <p className="mt-2 text-[0.78rem] leading-relaxed text-ink-muted">
              Describe an event in plain words. Each holding's live profile is embedded on this
              machine and compared against it — so the match is semantic, not a keyword rule.
            </p>

            <form
              className="mt-3 flex gap-2"
              onSubmit={(event) => {
                event.preventDefault()
                if (topic.trim()) exposure.mutate(topic.trim())
              }}
            >
              <Input
                value={topic}
                onChange={(event) => setTopic(event.target.value)}
                placeholder="rupee weakness, oil prices rising…"
                className="h-9"
              />
              <Button type="submit" size="sm" className="h-9" disabled={exposure.isPending}>
                {exposure.isPending ? "Scanning…" : "Check"}
              </Button>
            </form>

            <div className="mt-4 space-y-3">
              <AnimatePresence mode="popLayout">
                {(exposure.data?.matches ?? []).map((match, index) => (
                  <motion.div
                    key={match.symbol}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ delay: index * 0.05 }}
                  >
                    <div className="flex items-baseline justify-between text-[0.78rem]">
                      <span className="font-mono text-ink">{match.symbol}</span>
                      <span className="numeric text-ink-dim">
                        {match.weight.toFixed(1)}% of book
                      </span>
                    </div>
                    <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min(100, match.relevance * 160)}%` }}
                        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1], delay: index * 0.05 }}
                        className="h-full rounded-full bg-gradient-to-r from-lime-deep to-lime"
                      />
                    </div>
                    <div className="mt-1 flex justify-between text-[0.7rem] text-ink-dim">
                      <span>{match.sector}</span>
                      <span className="numeric">relevance {match.relevance.toFixed(2)}</span>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {exposure.data && exposure.data.matches.length === 0 && (
                <p className="text-[0.78rem] text-ink-dim">
                  No holding shows meaningful exposure to that.
                </p>
              )}
            </div>

            {exposure.data && exposure.data.matches.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                className="mt-4 w-full"
                onClick={() =>
                  navigate(
                    `/assistant?q=${encodeURIComponent(
                      `How is my portfolio exposed to ${exposure.data!.topic}? Use my holdings and today's news.`,
                    )}`,
                  )
                }
              >
                <Sparkles className="size-3.5" />
                Ask the assistant to explain this
              </Button>
            )}
          </Rise>
        </div>
      </div>
    </div>
  )
}
