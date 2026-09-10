/**
 * A number that animates to its new value.
 *
 * Live prices change under the reader's eye; interpolating the digits makes an
 * update legible instead of a flicker, and the brief tint says which way it
 * went without needing a separate indicator.
 */

import { useEffect, useRef, useState } from "react"
import { animate, useReducedMotion } from "motion/react"

import { cn } from "@/lib/utils"

interface Props {
  value: number | null | undefined
  format?: (value: number) => string
  className?: string
  duration?: number
}

export function NumberFlow({ value, format, className, duration = 0.6 }: Props) {
  const [shown, setShown] = useState(value ?? 0)
  const previous = useRef(value ?? 0)
  const [tone, setTone] = useState<"up" | "down" | null>(null)
  const reduced = useReducedMotion()

  useEffect(() => {
    if (value === null || value === undefined) return
    const from = previous.current
    if (from === value) return

    setTone(value > from ? "up" : "down")
    const timer = window.setTimeout(() => setTone(null), 900)

    if (reduced) {
      setShown(value)
      previous.current = value
      return () => window.clearTimeout(timer)
    }

    const controls = animate(from, value, {
      duration,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: setShown,
    })
    previous.current = value
    return () => {
      controls.stop()
      window.clearTimeout(timer)
    }
  }, [value, duration, reduced])

  if (value === null || value === undefined) {
    return <span className={cn("numeric text-ink-dim", className)}>—</span>
  }

  return (
    <span
      className={cn(
        "numeric transition-colors duration-500",
        tone === "up" && "text-lime",
        tone === "down" && "text-ember",
        className,
      )}
    >
      {format ? format(shown) : shown.toFixed(2)}
    </span>
  )
}
