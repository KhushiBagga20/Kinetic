/**
 * First run.
 *
 * The pitch, then the four things that make the app theirs. Each step is a
 * live control rather than a description, so setup happens on this screen.
 */

import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { motion } from "motion/react"
import { ArrowRight, Cpu, FileText, Sparkles, Wallet } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Rise, Stagger, StaggerItem } from "@/components/ui/motion-primitives"
import { useLoadModel, usePreferences, useSavePreferences, useStatus } from "@/hooks/use-kinetic"

const STEPS = [
  {
    icon: Wallet,
    title: "Add what you own",
    body: "Holdings are priced live and stored in a file on this machine. Nothing uploads them — that is the reason the model runs here too.",
    to: "/portfolio",
    cta: "Open portfolio",
  },
  {
    icon: FileText,
    title: "Feed it your documents",
    body: "Annual reports, fact sheets, your own notes. They are chunked, embedded and searched locally, and cited by name in every answer.",
    to: "/knowledge",
    cta: "Open knowledge",
  },
  {
    icon: Cpu,
    title: "Load Gemma 4",
    body: "26B parameters, 4-bit, on Apple Silicon. About a minute and 15 GB of unified memory. Everything else already works without it.",
    to: null,
    cta: "Load model",
  },
  {
    icon: Sparkles,
    title: "Ask something real",
    body: "“Is my portfolio exposed to a rupee fall?” — it reads your positions, pulls today's data, and tells you where every number came from.",
    to: "/assistant",
    cta: "Open assistant",
  },
] as const

export function Onboarding() {
  const navigate = useNavigate()
  const { data: prefs } = usePreferences()
  const { data: status } = useStatus()
  const save = useSavePreferences()
  const loadModel = useLoadModel()
  const [name, setName] = useState("")

  return (
    <div className="mx-auto max-w-3xl space-y-8 py-8">
      <Rise className="text-center">
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 220, damping: 20 }}
          className="mx-auto mb-5 flex size-14 items-center justify-center rounded-2xl border border-lime/25 bg-lime/10"
        >
          <Sparkles className="size-6 text-lime" strokeWidth={1.6} />
        </motion.div>

        <h1 className="text-[2.4rem] font-semibold leading-[1.05] tracking-[-0.04em] text-ink">
          Research your money
          <br />
          without handing it over.
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-[0.95rem] leading-relaxed text-ink-muted">
          Kinetic reads live market data and your own filings, and answers with a model running on
          this laptop. No API keys. Your positions, your documents and your questions never leave
          the machine.
        </p>
      </Rise>

      <Rise delay={0.1} className="glass mx-auto max-w-md p-5">
        <label htmlFor="name" className="label">
          What should it call you?
        </label>
        <form
          className="mt-2 flex gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            if (!name.trim()) return
            save.mutate(
              { name: name.trim() },
              { onSuccess: () => toast.success(`Welcome, ${name.trim().split(" ")[0]}`) },
            )
          }}
        >
          <Input
            id="name"
            value={name || prefs?.name || ""}
            onChange={(event) => setName(event.target.value)}
            placeholder="Your name"
            className="h-10"
          />
          <Button type="submit" disabled={save.isPending}>
            Continue
            <ArrowRight className="size-4" />
          </Button>
        </form>
      </Rise>

      <Stagger className="grid gap-3 sm:grid-cols-2">
        {STEPS.map(({ icon: Icon, title, body, to, cta }, index) => (
          <StaggerItem key={title}>
            <div className="glass group h-full p-5">
              <div className="flex items-center gap-2.5">
                <span className="flex size-8 items-center justify-center rounded-lg border border-lime/20 bg-lime/10 font-mono text-[0.72rem] text-lime">
                  {index + 1}
                </span>
                <Icon className="size-4 text-ink-dim" strokeWidth={1.7} />
                <h3 className="text-[0.92rem] font-medium text-ink">{title}</h3>
              </div>
              <p className="mt-2.5 text-[0.82rem] leading-relaxed text-ink-muted">{body}</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                disabled={!to && (loadModel.isPending || status?.model.loaded)}
                onClick={() => (to ? navigate(to) : loadModel.mutate("load"))}
              >
                {!to && status?.model.loaded ? "Model ready" : cta}
                <ArrowRight className="size-3.5" />
              </Button>
            </div>
          </StaggerItem>
        ))}
      </Stagger>
    </div>
  )
}
