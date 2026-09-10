/**
 * The price chart, drawn with TradingView's lightweight-charts.
 *
 * Candles rather than a line, because the intraday range is information; two
 * moving averages for structure; volume as a low histogram so it reads as
 * ground rather than as a second series competing for attention.
 */

import { useEffect, useRef } from "react"
import {
  AreaSeries,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  createChart,
  type IChartApi,
  type UTCTimestamp,
} from "lightweight-charts"

import type { Candle } from "@/lib/types"

interface Props {
  candles: Candle[]
  currency: string
  variant?: "candles" | "area"
  height?: number
}

const LIME = "#cdff9a"
const EMBER = "#ff5a2b"

export function PriceChart({ candles, currency, variant = "candles", height = 380 }: Props) {
  const holder = useRef<HTMLDivElement>(null)
  const chart = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!holder.current || !candles.length) return

    const instance = createChart(holder.current, {
      height,
      layout: {
        background: { color: "transparent" },
        textColor: "#63797c",
        fontFamily: "'IBM Plex Mono', monospace",
        fontSize: 11,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "rgba(30,58,63,0.45)" },
        horzLines: { color: "rgba(30,58,63,0.45)" },
      },
      rightPriceScale: { borderColor: "rgba(30,58,63,0.8)" },
      timeScale: { borderColor: "rgba(30,58,63,0.8)", rightOffset: 4 },
      crosshair: {
        vertLine: { color: "rgba(205,255,154,0.35)", labelBackgroundColor: "#16292d" },
        horzLine: { color: "rgba(205,255,154,0.35)", labelBackgroundColor: "#16292d" },
      },
      localization: { priceFormatter: (price: number) => `${price.toFixed(2)}` },
    })
    chart.current = instance

    const time = (value: string) => (Date.parse(value) / 1000) as UTCTimestamp

    if (variant === "candles") {
      const series = instance.addSeries(CandlestickSeries, {
        upColor: "rgba(205,255,154,0.55)",
        downColor: "rgba(255,90,43,0.5)",
        borderUpColor: LIME,
        borderDownColor: EMBER,
        wickUpColor: LIME,
        wickDownColor: EMBER,
      })
      series.setData(
        candles.map((candle) => ({
          time: time(candle.time),
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close,
        })),
      )
    } else {
      const series = instance.addSeries(AreaSeries, {
        lineColor: LIME,
        topColor: "rgba(205,255,154,0.28)",
        bottomColor: "rgba(205,255,154,0.01)",
        lineWidth: 2,
      })
      series.setData(candles.map((candle) => ({ time: time(candle.time), value: candle.close })))
    }

    for (const [key, color] of [
      ["sma20", "rgba(157,180,182,0.9)"],
      ["sma50", "rgba(99,121,124,0.9)"],
    ] as const) {
      const points = candles
        .filter((candle) => candle[key] !== null)
        .map((candle) => ({ time: time(candle.time), value: candle[key] as number }))
      if (!points.length) continue
      const line = instance.addSeries(LineSeries, {
        color,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      })
      line.setData(points)
    }

    const volume = instance.addSeries(HistogramSeries, {
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    })
    volume.setData(
      candles.map((candle) => ({
        time: time(candle.time),
        value: candle.volume,
        color: candle.close >= candle.open ? "rgba(205,255,154,0.16)" : "rgba(255,90,43,0.16)",
      })),
    )
    instance.priceScale("volume").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } })

    instance.timeScale().fitContent()

    const resize = new ResizeObserver(([entry]) =>
      instance.applyOptions({ width: entry.contentRect.width }),
    )
    resize.observe(holder.current)

    return () => {
      resize.disconnect()
      instance.remove()
      chart.current = null
    }
  }, [candles, variant, height])

  return (
    <div className="relative">
      <div ref={holder} className="w-full" />
      <span className="label absolute right-1 top-1">{currency}</span>
    </div>
  )
}
