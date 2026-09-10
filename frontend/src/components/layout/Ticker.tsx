/**
 * The index ribbon.
 *
 * Two identical halves scroll as one strip, so the loop is seamless, and it
 * pauses on hover because a moving number is hard to read.
 */

import { useIndices } from "@/hooks/use-kinetic"
import { compact, percent, toneOf } from "@/lib/format"
import { cn } from "@/lib/utils"

export function Ticker() {
  const { data: indices = [] } = useIndices()
  if (!indices.length) return <div className="h-8" />

  const strip = [...indices, ...indices]

  return (
    <div className="group relative overflow-hidden border-y border-border/50 bg-void/40">
      {/* Fade the strip into the page instead of cutting it off */}
      <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-16 bg-gradient-to-r from-canvas to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-16 bg-gradient-to-l from-canvas to-transparent" />

      <div className="flex w-max animate-[ticker_48s_linear_infinite] group-hover:[animation-play-state:paused]">
        {strip.map((quote, index) => {
          const tone = toneOf(quote.change_percent)
          return (
            <div
              key={`${quote.symbol}-${index}`}
              className="flex items-baseline gap-2 whitespace-nowrap px-5 py-2 text-[0.74rem]"
            >
              <span className="font-mono text-ink-dim">{quote.name.slice(0, 20)}</span>
              <span className="numeric text-ink">{compact(quote.price)}</span>
              <span
                className={cn(
                  "numeric",
                  tone === "up" && "text-lime",
                  tone === "down" && "text-ember",
                  tone === "flat" && "text-ink-dim",
                )}
              >
                {tone === "up" ? "▲" : tone === "down" ? "▼" : "—"} {percent(quote.change_percent)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
