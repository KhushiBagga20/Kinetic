/**
 * The exposure radar — filled in automatically, every few minutes.
 *
 * The backend reads today's headlines, names the themes behind them, and
 * tests every holding against each one: how related the company is, how much
 * of its own news is about it, and whether that news reads good or bad. This
 * component only shows the result; the user never has to type a topic.
 */

import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { AnimatePresence, motion } from "motion/react"
import { ChevronDown, ExternalLink, Loader2, Radar, RefreshCw, ShieldAlert, Sparkles } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Rise } from "@/components/ui/motion-primitives"
import { useAutoExposure, useRefreshAutomation } from "@/hooks/use-kinetic"
import { ago } from "@/lib/format"
import type { ExposureDirection } from "@/lib/types"
import { cn } from "@/lib/utils"

const DIRECTION_STYLE: Record<ExposureDirection, { label: string; className: string }> = {
  tailwind: { label: "▲ tailwind", className: "border-lime/35 text-lime" },
  headwind: { label: "▼ headwind", className: "border-ember/45 text-ember" },
  mixed: { label: "◆ mixed", className: "border-border text-ink-muted" },
  watch: { label: "● watch", className: "border-border text-ink-dim" },
}

const SOURCE_LABEL = {
  model: "named by Gemma from today's news",
  news: "in today's headlines",
  baseline: "standing macro check",
} as const

export function DirectionTag({ direction }: { direction: ExposureDirection }) {
  const style = DIRECTION_STYLE[direction] ?? DIRECTION_STYLE.watch
  return (
    <span className={cn("whitespace-nowrap rounded-full border px-2 py-0.5 font-mono text-[0.62rem]", style.className)}>
      {style.label}
    </span>
  )
}

export function ExposureRadar() {
  const navigate = useNavigate()
  const { data, isError } = useAutoExposure()
  const refresh = useRefreshAutomation()
  const [open, setOpen] = useState<string | null>(null)

  const themes = data?.ready ? data.themes : []
  const largest = Math.max(1, ...themes.map((theme) => theme.impact))
  const building = data?.automation?.building || refresh.isPending
  const minutes = Math.round((data?.automation?.slow_every_sec ?? 300) / 60)

  return (
    <Rise delay={0.04} className="glass p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Radar className="size-4 text-lime" strokeWidth={1.8} />
          <h2 className="text-[1rem] font-semibold text-ink">Live exposure radar</h2>
          <span className="label">
            automatic · {data?.ready && data.as_of ? `updated ${ago(data.as_of)}` : "scanning"} · every {minutes} min
          </span>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => refresh.mutate()}
          disabled={building}
          aria-label="Rescan now"
        >
          {building ? <Loader2 className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />}
          {building ? "Scanning" : "Rescan"}
        </Button>
      </div>
      <p className="mt-2 text-[0.78rem] leading-relaxed text-ink-muted">
        Themes are found in today&rsquo;s live news, then every holding is tested against them using its
        business profile, its own headlines, their tone, its size in your book and its beta. All on this
        machine.
      </p>

      {/* -- still building the first scan ---------------------------------- */}
      {!data?.ready && !isError && (
        <div className="mt-4 space-y-2">
          <p className="flex items-center gap-2 text-[0.78rem] text-ink-dim">
            <Loader2 className="size-3.5 animate-spin text-lime" />
            Reading today&rsquo;s headlines and matching them to your holdings…
          </p>
          {[0, 1, 2].map((index) => (
            <Skeleton key={index} className="h-12 rounded-lg" />
          ))}
        </div>
      )}

      {isError && (
        <p className="mt-4 text-[0.78rem] text-ink-dim">The exposure scan is not reachable right now.</p>
      )}

      {data?.ready && data.empty && (
        <p className="mt-4 text-[0.8rem] text-ink-dim">Add a holding and the radar starts scanning on its own.</p>
      )}

      {data?.ready && !data.empty && themes.length === 0 && (
        <p className="mt-4 text-[0.8rem] text-ink-dim">
          None of today&rsquo;s themes touch your holdings in a meaningful way.
        </p>
      )}

      {data?.ready && data.top_risk && (
        <div className="mt-4 flex items-center gap-2 rounded-lg border border-ember/35 bg-ember/[0.06] px-3 py-2 text-[0.78rem] text-ink">
          <ShieldAlert className="size-4 shrink-0 text-ember" />
          Biggest headwind today: <span className="font-medium">{data.top_risk}</span>
        </div>
      )}

      {/* -- themes ------------------------------------------------------------ */}
      <div className="mt-4 space-y-2">
        {themes.map((theme, index) => {
          const isOpen = open === theme.theme
          return (
            <motion.div
              key={theme.theme}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.04 }}
              className="rounded-lg border border-border/50 bg-white/[0.015]"
            >
              <button
                onClick={() => setOpen(isOpen ? null : theme.theme)}
                aria-expanded={isOpen}
                className="flex w-full flex-wrap items-center gap-x-3 gap-y-1.5 px-3.5 py-3 text-left"
              >
                <span className="min-w-0 flex-1">
                  <span className="block text-[0.85rem] font-medium capitalize text-ink">{theme.theme}</span>
                  <span className="block text-[0.68rem] text-ink-dim">
                    {SOURCE_LABEL[theme.source] ?? theme.source}
                    {theme.headline_count > 0 ? ` · ${theme.headline_count} headlines` : ""}
                  </span>
                </span>
                <DirectionTag direction={theme.direction} />
                <span className="numeric w-24 text-right text-[0.72rem] text-ink-muted">
                  {theme.book_share.toFixed(0)}% of book
                </span>
                <ChevronDown className={cn("size-3.5 text-ink-dim transition-transform", isOpen && "rotate-180")} />
                <span className="h-1 w-full overflow-hidden rounded-full bg-surface">
                  <motion.span
                    initial={{ width: 0 }}
                    animate={{ width: `${(theme.impact / largest) * 100}%` }}
                    transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                    className={cn(
                      "block h-full rounded-full",
                      theme.direction === "headwind"
                        ? "bg-ember/70"
                        : theme.direction === "tailwind"
                          ? "bg-lime/70"
                          : "bg-ink-dim/60",
                    )}
                  />
                </span>
              </button>

              <AnimatePresence initial={false}>
                {isOpen && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                    className="overflow-hidden"
                  >
                    <div className="space-y-2.5 border-t border-border/40 px-3.5 py-3">
                      {theme.holdings.map((match) => (
                        <div key={match.symbol} className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2 text-[0.78rem]">
                            <button
                              onClick={() => navigate(`/research?symbol=${encodeURIComponent(match.symbol)}`)}
                              className="font-mono text-ink transition-colors hover:text-lime"
                            >
                              {match.symbol}
                            </button>
                            <DirectionTag direction={match.direction} />
                            <span className="numeric text-ink-dim">{match.weight.toFixed(1)}% of book</span>
                            <span className="numeric ml-auto text-ink-dim">
                              match {match.score.toFixed(2)} · tone {match.tone >= 0 ? "+" : ""}
                              {match.tone.toFixed(2)}
                            </span>
                          </div>
                          {match.evidence.map((article) => (
                            <a
                              key={article.url || article.title}
                              href={article.url || undefined}
                              target="_blank"
                              rel="noreferrer"
                              className="group mt-1 flex items-start gap-1.5 border-l border-lime/25 pl-2.5 text-[0.72rem] leading-relaxed text-ink-muted hover:text-ink"
                            >
                              <span className="min-w-0 flex-1 [overflow-wrap:anywhere]">
                                {article.title}
                                <span className="text-ink-dim"> — {article.publisher}</span>
                              </span>
                              <ExternalLink className="mt-0.5 size-3 shrink-0 opacity-0 transition-opacity group-hover:opacity-100" />
                            </a>
                          ))}
                        </div>
                      ))}

                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full"
                        onClick={() =>
                          navigate(
                            `/assistant?q=${encodeURIComponent(
                              `How is my portfolio exposed to ${theme.theme}? Use my holdings and today's news.`,
                            )}`,
                          )
                        }
                      >
                        <Sparkles className="size-3.5" />
                        Ask the assistant to explain this
                      </Button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )
        })}
      </div>
    </Rise>
  )
}
