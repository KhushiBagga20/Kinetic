import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react"

import { percent, toneOf } from "@/lib/format"
import { cn } from "@/lib/utils"

/**
 * A change, shown with both a colour and an arrow.
 *
 * Colour alone fails for a colour-blind reader and in a screenshot, so the
 * glyph carries the same information independently.
 */
export function Delta({
  value,
  className,
  size = "sm",
}: {
  value: number | null | undefined
  className?: string
  size?: "sm" | "lg"
}) {
  const tone = toneOf(value)
  const Icon = tone === "up" ? ArrowUpRight : tone === "down" ? ArrowDownRight : Minus

  return (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 numeric",
        size === "lg" ? "text-sm" : "text-[0.74rem]",
        tone === "up" && "text-lime",
        tone === "down" && "text-ember",
        tone === "flat" && "text-ink-dim",
        className,
      )}
    >
      <Icon className={size === "lg" ? "size-4" : "size-3"} strokeWidth={2.2} />
      {percent(value)}
    </span>
  )
}
