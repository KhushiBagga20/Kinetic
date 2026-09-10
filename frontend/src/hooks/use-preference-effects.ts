import { useEffect } from "react"

import { usePreferences } from "./use-kinetic"

const SCALES: Record<string, string> = { Normal: "1", Large: "1.12", Larger: "1.25" }

/** Applies the stored accessibility preferences to the document root. */
export function usePreferenceSideEffects() {
  const { data: prefs } = usePreferences()

  useEffect(() => {
    if (!prefs) return
    const root = document.documentElement
    root.style.setProperty("--text-scale", SCALES[prefs.text_size] ?? "1")
    root.dataset.contrast = prefs.high_contrast ? "high" : "normal"
    root.dataset.motion = prefs.reduce_motion ? "reduced" : "full"
  }, [prefs])
}
