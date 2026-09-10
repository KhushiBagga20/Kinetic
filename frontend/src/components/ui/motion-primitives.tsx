/**
 * The motion vocabulary of the app.
 *
 * Three rules keep it feeling designed rather than animated: everything moves
 * on the same easing curve, nothing travels more than a few pixels, and lists
 * stagger so the eye is led down them instead of hit all at once.
 */

import { motion, type HTMLMotionProps, type Transition } from "motion/react"
import type { ReactNode } from "react"

export const EASE: Transition["ease"] = [0.16, 1, 0.3, 1]

export const fade: Transition = { duration: 0.35, ease: EASE }
export const spring: Transition = { type: "spring", stiffness: 320, damping: 30, mass: 0.7 }

/** A block that rises into place. Used for panels and cards. */
export function Rise({
  children,
  delay = 0,
  y = 10,
  ...props
}: { children: ReactNode; delay?: number; y?: number } & HTMLMotionProps<"div">) {
  return (
    <motion.div
      initial={{ opacity: 0, y }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ ...fade, delay }}
      {...props}
    >
      {children}
    </motion.div>
  )
}

/** Wraps a list so its children arrive one after another. */
export function Stagger({
  children,
  gap = 0.045,
  ...props
}: { children: ReactNode; gap?: number } & HTMLMotionProps<"div">) {
  return (
    <motion.div
      initial="hidden"
      animate="shown"
      variants={{ shown: { transition: { staggerChildren: gap } } }}
      {...props}
    >
      {children}
    </motion.div>
  )
}

export const stagger_item = {
  hidden: { opacity: 0, y: 8 },
  shown: { opacity: 1, y: 0, transition: fade },
}

/** One item inside a Stagger. */
export function StaggerItem({ children, ...props }: { children: ReactNode } & HTMLMotionProps<"div">) {
  return (
    <motion.div variants={stagger_item} {...props}>
      {children}
    </motion.div>
  )
}
