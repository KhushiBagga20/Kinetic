import type { ReactNode } from "react"
import { motion } from "motion/react"

import { cn } from "@/lib/utils"

/**
 * The atom of every dashboard: a label, one number, one qualifier.
 *
 * The hover lift is small on purpose — enough to say the card is a surface,
 * not enough to make a wall of them feel restless.
 */
export function StatCard({
  label,
  value,
  detail,
  accent,
  className,
}: {
  label: string
  value: ReactNode
  detail?: ReactNode
  accent?: boolean
  className?: string
}) {
  return (
    <motion.div
      whileHover={{ y: -2 }}
      transition={{ type: "spring", stiffness: 400, damping: 28 }}
      className={cn(
        "glass group px-4 py-3.5",
        accent && "border-lime/25 bg-lime/[0.06]",
        className,
      )}
    >
      <div className="label">{label}</div>
      <div className="mt-1.5 text-[1.55rem] font-semibold leading-none tracking-[-0.02em] text-ink">
        {value}
      </div>
      {detail && <div className="mt-1.5 text-[0.74rem] text-ink-muted">{detail}</div>}

      {/* A hairline that lights up on hover: feedback without movement. */}
      <div className="mt-3 h-px w-full origin-left scale-x-0 bg-gradient-to-r from-lime/60 to-transparent transition-transform duration-500 group-hover:scale-x-100" />
    </motion.div>
  )
}
