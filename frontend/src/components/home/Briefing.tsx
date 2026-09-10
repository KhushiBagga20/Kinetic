/**
 * Today's briefing — assembled by the backend on its own timer.
 *
 * A written note from the local model (once it has loaded), today's themes
 * and a simulated outlook for every holding. The user opens the app and it
 * is already there; nothing to search for.
 */

import { useNavigate } from "react-router-dom"
import { Loader2, Newspaper, RefreshCw } from "lucide-react"

import { Answer } from "@/components/chat/Answer"
import { NoGuaranteePill } from "@/components/market/SimulationPanel"
import { DirectionTag } from "@/components/portfolio/ExposureRadar"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Rise } from "@/components/ui/motion-primitives"
import { useBriefing, useRefreshAutomation, useStatus } from "@/hooks/use-kinetic"
import { ago, money, signalTone } from "@/lib/format"
import { cn } from "@/lib/utils"

export function Briefing() {
  const navigate = useNavigate()
  const { data } = useBriefing()
  const { data: status } = useStatus()
  const refresh = useRefreshAutomation()

  if (!data?.ready) {
    return (
      <Rise delay={0.04} className="glass p-5">
        <div className="flex items-center gap-2">
          <Newspaper className="size-4 text-lime" strokeWidth={1.8} />
          <h2 className="text-[1rem] font-semibold text-ink">Today&rsquo;s briefing</h2>
        </div>
        <p className="mt-3 flex items-center gap-2 text-[0.8rem] text-ink-muted">
          <Loader2 className="size-3.5 animate-spin text-lime" />
          Pricing your book, reading today&rsquo;s news and simulating each holding…
        </p>
        <div className="mt-3 grid gap-3 lg:grid-cols-2">
          <Skeleton className="h-32 rounded-lg" />
          <Skeleton className="h-32 rounded-lg" />
        </div>
      </Rise>
    )
  }

  const forecasts = data.forecasts ?? []
  const themes = (data.exposure?.themes ?? []).slice(0, 3)
  const building = data.automation?.building || refresh.isPending

  const noteFallback = status?.model.loading
    ? "Gemma is loading in the background — a written note will appear here on its own."
    : status?.model.loaded
      ? "The written note is on its way with the next refresh."
      : "Load the model for a written note. Everything else here updates on its own."

  return (
    <Rise delay={0.04} className="glass p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Newspaper className="size-4 text-lime" strokeWidth={1.8} />
          <h2 className="text-[1rem] font-semibold text-ink">Today&rsquo;s briefing</h2>
          <span className="label">
            automatic · {data.generated_at ? `updated ${ago(data.generated_at)}` : ""}
          </span>
        </div>
        <Button size="sm" variant="outline" onClick={() => refresh.mutate()} disabled={building}>
          {building ? <Loader2 className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />}
          {building ? "Updating" : "Update now"}
        </Button>
      </div>

      <div className="mt-4 grid items-start gap-5 lg:grid-cols-[1.25fr_1fr]">
        {/* -- the written note and today's themes ------------------------------ */}
        <div className="min-w-0 space-y-4">
          {data.note ? (
            <div className="rounded-xl border border-border/50 bg-white/[0.015] px-4 py-3">
              <Answer content={data.note} />
            </div>
          ) : (
            <p className="rounded-xl border border-dashed border-border/60 px-4 py-3 text-[0.8rem] text-ink-dim">
              {noteFallback}
            </p>
          )}

          {themes.length > 0 && (
            <div>
              <div className="label mb-2">Today&rsquo;s themes in your book</div>
              <div className="space-y-1.5">
                {themes.map((theme) => (
                  <button
                    key={theme.theme}
                    onClick={() => navigate("/portfolio")}
                    className="flex w-full items-center gap-2 rounded-lg border border-border/50 px-3 py-2 text-left transition-colors hover:border-lime/30 hover:bg-lime/[0.04]"
                  >
                    <span className="min-w-0 flex-1 truncate text-[0.8rem] capitalize text-ink">{theme.theme}</span>
                    <DirectionTag direction={theme.direction} />
                    <span className="numeric w-20 text-right text-[0.7rem] text-ink-dim">
                      {theme.book_share.toFixed(0)}% of book
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* -- simulated outlook per holding ------------------------------------ */}
        <div className="min-w-0">
          <div className="mb-2 flex items-center gap-2">
            <span className="label">Simulated outlook</span>
            <NoGuaranteePill />
          </div>
          {forecasts.length === 0 ? (
            <p className="text-[0.78rem] text-ink-dim">Add holdings to see an outlook for each one.</p>
          ) : (
            <div className="space-y-1">
              {forecasts.map((item) => (
                <button
                  key={item.symbol}
                  onClick={() => navigate(`/research?symbol=${encodeURIComponent(item.symbol)}`)}
                  className="w-full rounded-lg px-2.5 py-2 text-left transition-colors hover:bg-lime/[0.06]"
                >
                  <div className="flex items-baseline gap-2">
                    <span className="font-mono text-[0.8rem] text-ink">{item.symbol}</span>
                    <span className={cn("text-[0.7rem] font-medium", signalTone(item.signal))}>{item.signal}</span>
                    <span className="numeric ml-auto text-[0.78rem] text-ink">
                      {item.probability_up !== null ? `${Math.round(item.probability_up * 100)}% ▲` : "—"}
                    </span>
                  </div>
                  <div className="mt-0.5 flex justify-between text-[0.68rem] text-ink-dim">
                    <span className="numeric">
                      {item.horizon_days}d range {money(item.expected_low)} – {money(item.expected_high)} {item.currency}
                    </span>
                    <span>risk {item.risk_label.toLowerCase()}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </Rise>
  )
}
