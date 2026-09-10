/**
 * The dock.
 *
 * A floating bar that magnifies around the cursor, the way the macOS dock
 * does: each item's size is a function of its distance from the pointer, run
 * through a spring so the whole row swells and settles as one object. The
 * active route keeps a lit underline that slides between items.
 */

import { useRef } from "react"
import { NavLink, useLocation } from "react-router-dom"
import {
  motion,
  useMotionValue,
  useSpring,
  useTransform,
  type MotionValue,
} from "motion/react"
import { BookOpen, Home, LineChart, MessageSquare, Wallet } from "lucide-react"

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

const ITEMS = [
  { to: "/", label: "Home", icon: Home },
  { to: "/portfolio", label: "Portfolio", icon: Wallet },
  { to: "/research", label: "Research", icon: LineChart },
  { to: "/assistant", label: "Assistant", icon: MessageSquare },
  { to: "/knowledge", label: "Knowledge", icon: BookOpen },
] as const

const BASE = 46
const PEAK = 74
const REACH = 130

function DockItem({
  item,
  pointerX,
  active,
}: {
  item: (typeof ITEMS)[number]
  pointerX: MotionValue<number>
  active: boolean
}) {
  const ref = useRef<HTMLAnchorElement>(null)

  // Distance from the pointer to this item's centre, in pixels.
  const distance = useTransform(pointerX, (x) => {
    const bounds = ref.current?.getBoundingClientRect()
    if (!bounds) return REACH
    return x - (bounds.x + bounds.width / 2)
  })

  const target = useTransform(distance, [-REACH, 0, REACH], [BASE, PEAK, BASE], { clamp: true })
  const size = useSpring(target, { stiffness: 260, damping: 22, mass: 0.5 })
  const lift = useTransform(size, [BASE, PEAK], [0, -10])
  const iconSize = useTransform(size, [BASE, PEAK], [18, 27])

  const Icon = item.icon

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <NavLink ref={ref} to={item.to} end={item.to === "/"} aria-label={item.label}>
          <motion.span
            style={{ width: size, height: size, y: lift }}
            className={cn(
              "relative flex items-center justify-center rounded-2xl border transition-colors",
              active
                ? "border-lime/40 bg-lime/15 text-lime"
                : "border-transparent bg-white/4 text-ink-muted hover:text-ink",
            )}
          >
            <motion.span style={{ width: iconSize, height: iconSize }} className="flex">
              <Icon className="size-full" strokeWidth={1.7} />
            </motion.span>

            {active && (
              <motion.span
                layoutId="dock-active"
                className="absolute -bottom-2 size-1 rounded-full bg-lime"
                transition={{ type: "spring", stiffness: 420, damping: 34 }}
              />
            )}
          </motion.span>
        </NavLink>
      </TooltipTrigger>
      <TooltipContent side="top" sideOffset={14}>
        {item.label}
      </TooltipContent>
    </Tooltip>
  )
}

export function Dock() {
  const pointerX = useMotionValue(Number.POSITIVE_INFINITY)
  const { pathname } = useLocation()

  return (
    <motion.nav
      aria-label="Main"
      initial={{ y: 60, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ delay: 0.15, type: "spring", stiffness: 240, damping: 26 }}
      className="pointer-events-none fixed inset-x-0 bottom-5 z-50 flex justify-center"
    >
      <div
        onMouseMove={(event) => pointerX.set(event.clientX)}
        onMouseLeave={() => pointerX.set(Number.POSITIVE_INFINITY)}
        className="pointer-events-auto flex items-end gap-2 rounded-[26px] border border-border/80 bg-void/70 px-3 pb-3 pt-2 shadow-[0_28px_60px_-24px_rgba(0,0,0,0.95)] backdrop-blur-2xl"
      >
        {ITEMS.map((item) => (
          <DockItem
            key={item.to}
            item={item}
            pointerX={pointerX}
            active={item.to === "/" ? pathname === "/" : pathname.startsWith(item.to)}
          />
        ))}
      </div>
    </motion.nav>
  )
}
