import { motion } from "motion/react"

import { cn } from "@/lib/utils"

/** The mark: a bolt whose stroke draws itself once on mount. */
export function Logo({ className, size = 22 }: { className?: string; size?: number }) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <motion.path
          d="M13.5 2 4 13.2h6.2L9.4 22l10-11.4h-6.4L13.5 2Z"
          stroke="var(--lime)"
          strokeWidth="1.6"
          strokeLinejoin="round"
          fill="color-mix(in oklab, var(--lime) 18%, transparent)"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
        />
      </svg>
      <span className="text-[1.05rem] font-bold tracking-[-0.03em] text-ink">KINETIC</span>
    </span>
  )
}
