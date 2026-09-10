/** Number and time formatting. Financial figures must never look approximate. */

export function money(value: number | null | undefined, currency = "", digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—"
  const formatted = value.toLocaleString("en-IN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
  return currency ? `${formatted} ${currency}` : formatted
}

/** Large values lose their decimals once those decimals stop carrying meaning. */
export function compact(value: number | null | undefined, currency = ""): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—"
  const abs = Math.abs(value)
  const units: [number, string][] = [
    [1e12, "T"],
    [1e9, "B"],
    [1e7, "Cr"],
    [1e5, "L"],
    [1e3, "K"],
  ]
  for (const [threshold, suffix] of units) {
    if (abs >= threshold) {
      return `${(value / threshold).toFixed(2)}${suffix}${currency ? ` ${currency}` : ""}`
    }
  }
  return money(value, currency, 2)
}

export function percent(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—"
  return `${value >= 0 ? "+" : ""}${value.toFixed(digits)}%`
}

export function signed(value: number | null | undefined, currency = ""): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—"
  return `${value >= 0 ? "+" : ""}${money(value, currency, 0)}`
}

export function toneOf(value: number | null | undefined): "up" | "down" | "flat" {
  if (value === null || value === undefined || Number.isNaN(value) || value === 0) return "flat"
  return value > 0 ? "up" : "down"
}

/** "2026-09-10 04:21 UTC" reads better as a relative age in a live interface. */
export function ago(stamp: string): string {
  const parsed = Date.parse(stamp.replace(" UTC", "Z").replace(" ", "T"))
  if (Number.isNaN(parsed)) return stamp
  const seconds = Math.max(0, (Date.now() - parsed) / 1000)
  if (seconds < 45) return "just now"
  if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h ago`
  return `${Math.round(seconds / 86400)}d ago`
}

export function titleCase(text: string): string {
  return text.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
}
