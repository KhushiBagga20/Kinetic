/**
 * Assistant — the answer being written, with its work shown.
 *
 * The interesting part of a local agent is not the text: it is watching it
 * retrieve, decide it needs a live number, fetch it, and only then write. Each
 * stage gets its own affordance so the reasoning is legible instead of magic.
 */

import { useCallback, useEffect, useRef, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { AnimatePresence, motion } from "motion/react"
import {
  Brain,
  ChevronDown,
  Cpu,
  Eraser,
  FileText,
  Radio,
  Send,
  Sparkles,
  Wrench,
} from "lucide-react"
import { toast } from "sonner"

import { Answer } from "@/components/chat/Answer"
import { Button } from "@/components/ui/button"
import { Rise } from "@/components/ui/motion-primitives"
import { Textarea } from "@/components/ui/textarea"
import { useLoadModel, useMovers, usePortfolio, useStatus } from "@/hooks/use-kinetic"
import { api } from "@/lib/api"
import { streamChat } from "@/lib/chat-stream"
import type { AgentEvent, Passage } from "@/lib/types"
import { cn } from "@/lib/utils"

interface Message {
  role: "user" | "assistant"
  content: string
  thought?: string
  passages?: Passage[]
  tools?: string[]
  footer?: string
}

export function AssistantPage() {
  const [params, setParams] = useSearchParams()
  const { data: status } = useStatus()
  const { data: portfolio } = usePortfolio()
  const { data: movers = [] } = useMovers("most_actives")
  const loadModel = useLoadModel()

  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState("")
  const [busy, setBusy] = useState(false)
  const [live, setLive] = useState<Message | null>(null)
  const [stage, setStage] = useState("")
  const [showThought, setShowThought] = useState(false)
  const scroller = useRef<HTMLDivElement>(null)
  const stickToBottom = useRef(true)
  const finalRef = useRef<Message | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const loaded = status?.model.loaded ?? false

  // The transcript scrolls inside its own box, so the answer can never slide
  // underneath the composer. It follows new text only while the reader is
  // already at the bottom — scrolling up to re-read is never yanked away.
  useEffect(() => {
    const box = scroller.current
    if (box && stickToBottom.current) box.scrollTop = box.scrollHeight
  }, [messages, live?.content, live?.tools?.length, live?.passages?.length, stage])

  // Leaving the page mid-answer stops the stream instead of leaking it.
  useEffect(() => () => abortRef.current?.abort(), [])

  const send = useCallback(
    async (question: string) => {
      if (!question.trim() || busy) return
      if (!loaded) {
        toast.error("Load the model first — it is the button in the top bar.")
        return
      }

      setMessages((prior) => [...prior, { role: "user", content: question }])
      setDraft("")
      setBusy(true)
      stickToBottom.current = true

      const draftReply: Message = { role: "assistant", content: "", tools: [], passages: [] }
      finalRef.current = draftReply
      setLive({ ...draftReply })

      const controller = new AbortController()
      abortRef.current = controller

      try {
        await streamChat(question, (event: AgentEvent) => {
          setStage(event.kind === "status" ? event.text : stageOf(event))
          setLive((current) => {
            if (!current) return current
            const next = { ...current }
            switch (event.kind) {
              case "sources":
                next.passages = event.data.passages ?? []
                break
              case "thought":
                next.thought = (next.thought ?? "") + event.text
                break
              case "token":
                next.content += event.text
                break
              case "step_reset":
                next.content = ""
                break
              case "tool_call":
                next.tools = [...(next.tools ?? []), event.text]
                break
              case "done":
                next.content = event.text || next.content
                next.footer = [
                  `${event.data.seconds}s`,
                  `${event.data.tokens} tokens at ${event.data.tokens_per_sec} tok/s`,
                  `${next.passages?.length ?? 0} passages retrieved`,
                  event.data.tools_used?.length
                    ? `tools: ${[...new Set(event.data.tools_used)].join(", ")}`
                    : "",
                ]
                  .filter(Boolean)
                  .join(" · ")
                break
              case "error":
                next.content = `⚠️ ${event.text}`
                break
            }
            finalRef.current = next
            return next
          })
        }, controller.signal)
      } catch (error) {
        if (!controller.signal.aborted) toast.error(String(error))
      } finally {
        abortRef.current = null
        // The finished turn is committed here, outside any state updater:
        // updaters run twice under StrictMode and would duplicate the message.
        const finished = finalRef.current
        setStage("")
        setBusy(false)
        setLive(null)
        finalRef.current = null
        if (finished) setMessages((prior) => [...prior, finished])
      }
    },
    [busy, loaded],
  )

  // A question can arrive from another view via ?q=
  useEffect(() => {
    const question = params.get("q")
    if (question && loaded && !busy && messages.length === 0) {
      setParams({}, { replace: true })
      void send(question)
    }
  }, [params, loaded, busy, messages.length, send, setParams])

  const suggestions = buildSuggestions(
    portfolio?.positions.map((row) => row.symbol) ?? [],
    movers.map((row) => row.symbol),
  )

  return (
    // A fixed-height column: header on top, transcript scrolling in the
    // middle, composer pinned at the bottom. Nothing can overlap anything.
    <div className="mx-auto flex h-[calc(100dvh-15.5rem)] min-h-[26rem] max-w-4xl flex-col gap-4">
      <Rise className="flex shrink-0 items-center justify-between">
        <div>
          <h1 className="text-[1.8rem] font-semibold tracking-[-0.035em] text-ink">Assistant</h1>
          <p className="mt-1 flex items-center gap-1.5 text-[0.76rem] text-ink-muted">
            <Radio className="size-3 text-lime" />
            Retrieves your documents first · calls live tools · runs on this machine
          </p>
        </div>
        {messages.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              void api.resetChat()
              setMessages([])
            }}
          >
            <Eraser className="size-3.5" />
            Clear
          </Button>
        )}
      </Rise>

      {!loaded && (
        <Rise className="glass flex shrink-0 flex-wrap items-center gap-4 border-lime/20 bg-lime/[0.04] p-5">
          <Cpu className="size-5 text-lime" strokeWidth={1.7} />
          <div className="flex-1">
            <h2 className="text-[0.92rem] font-medium text-ink">
              {status?.model.loading ? "Gemma 4 is loading in the background" : "Gemma 4 is not loaded yet"}
            </h2>
            <p className="mt-1 text-[0.79rem] leading-relaxed text-ink-muted">
              26B parameters, 4-bit, on Apple Silicon. About a minute and 15 GB of unified memory —
              and then nothing you ask it leaves this laptop.
            </p>
          </div>
          <Button
            onClick={() => loadModel.mutate("load")}
            disabled={loadModel.isPending || status?.model.loading}
          >
            {loadModel.isPending || status?.model.loading ? "Loading…" : "Load model"}
          </Button>
        </Rise>
      )}

      {/* -- transcript: the only part of the page that scrolls -------------- */}
      <div
        ref={scroller}
        onScroll={(event) => {
          const box = event.currentTarget
          stickToBottom.current = box.scrollHeight - box.scrollTop - box.clientHeight < 120
        }}
        className="min-h-0 flex-1 space-y-5 overflow-y-auto overscroll-contain pr-1"
      >
      {messages.length === 0 && !live && (
        <Rise delay={0.05} className="grid gap-2 sm:grid-cols-2">
          {suggestions.map((question, index) => (
            <motion.button
              key={question}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.06 * index }}
              onClick={() => send(question)}
              className="group flex items-start gap-2.5 rounded-xl border border-border/60 bg-white/[0.015] p-3.5 text-left transition-colors hover:border-lime/30 hover:bg-lime/[0.05]"
            >
              <Sparkles className="mt-0.5 size-3.5 shrink-0 text-ink-dim transition-colors group-hover:text-lime" />
              <span className="text-[0.82rem] leading-relaxed text-ink-muted transition-colors group-hover:text-ink">
                {question}
              </span>
            </motion.button>
          ))}
        </Rise>
      )}

      {/* -- transcript ----------------------------------------------------- */}
      <div className="space-y-5">
        {[...messages, ...(live ? [live] : [])].map((message, index) => (
          <MessageBlock
            key={index}
            message={message}
            streaming={live !== null && index === messages.length}
            showThought={showThought}
            onToggleThought={() => setShowThought((value) => !value)}
          />
        ))}

        <AnimatePresence>
          {stage && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex items-center gap-2 font-mono text-[0.72rem] text-ink-dim"
            >
              <span className="live-dot" />
              {stage}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      </div>

      {/* -- composer: a normal block under the transcript, never floating --- */}
      <div className="shrink-0">
        <form
          onSubmit={(event) => {
            event.preventDefault()
            send(draft)
          }}
          className="glass flex items-end gap-2 bg-raised p-2"
        >
          <Textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault()
                send(draft)
              }
            }}
            placeholder="Ask about a company, a filing, or your own portfolio…"
            rows={1}
            className="max-h-40 min-h-[2.5rem] resize-none border-0 bg-transparent text-[0.88rem] focus-visible:ring-0"
          />
          <Button type="submit" size="icon" disabled={busy || !draft.trim()} className="size-9 shrink-0">
            <Send className="size-4" />
          </Button>
        </form>
      </div>
    </div>
  )
}

function MessageBlock({
  message,
  streaming,
  showThought,
  onToggleThought,
}: {
  message: Message
  streaming: boolean
  showThought: boolean
  onToggleThought: () => void
}) {
  if (message.role === "user") {
    return (
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end">
        <div className="max-w-[80%] whitespace-pre-wrap rounded-2xl rounded-br-md border border-lime/20 bg-lime/[0.08] px-4 py-2.5 text-[0.88rem] text-ink [overflow-wrap:anywhere]">
          {message.content}
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="min-w-0 space-y-2.5">
      {/* retrieved sources */}
      {!!message.passages?.length && (
        <div className="flex flex-wrap gap-1.5">
          {message.passages.map((passage, index) => (
            <motion.span
              key={`${passage.label}-${index}`}
              initial={{ opacity: 0, scale: 0.94 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.04 }}
              title={passage.text.slice(0, 400)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[0.66rem]",
                passage.kind === "live"
                  ? "border-lime/30 text-lime"
                  : "border-border text-ink-muted",
              )}
            >
              {passage.kind === "live" ? <Radio className="size-2.5" /> : <FileText className="size-2.5" />}
              S{index + 1} · {passage.label.slice(0, 40)}
            </motion.span>
          ))}
        </div>
      )}

      {/* tools called */}
      {!!message.tools?.length && (
        <div className="flex flex-wrap gap-1.5">
          {[...new Set(message.tools)].map((tool) => (
            <motion.span
              key={tool}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center gap-1.5 rounded-full border border-ember/30 px-2.5 py-1 font-mono text-[0.66rem] text-ember-soft"
            >
              <Wrench className="size-2.5" />
              {tool}
            </motion.span>
          ))}
        </div>
      )}

      {/* reasoning */}
      {message.thought && (
        <div>
          <button
            onClick={onToggleThought}
            className="flex items-center gap-1.5 font-mono text-[0.68rem] text-ink-dim transition-colors hover:text-ink-muted"
          >
            <Brain className="size-3" />
            reasoning
            <ChevronDown className={cn("size-3 transition-transform", showThought && "rotate-180")} />
          </button>
          <AnimatePresence>
            {showThought && (
              <motion.p
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="mt-1.5 overflow-hidden whitespace-pre-wrap border-l border-border pl-3 text-[0.75rem] leading-relaxed text-ink-dim"
              >
                {message.thought}
              </motion.p>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* the answer */}
      <div className="min-w-0 rounded-2xl rounded-bl-md border border-border/60 border-l-lime/50 bg-white/[0.015] px-4 py-3">
        <Answer content={message.content} streaming={streaming} />
      </div>

      {message.footer && <p className="font-mono text-[0.66rem] text-ink-dim">{message.footer}</p>}
    </motion.div>
  )
}

function stageOf(event: AgentEvent): string {
  switch (event.kind) {
    case "sources":
      return `retrieved ${event.data.passages?.length ?? 0} passages in ${event.data.ms?.toFixed(0)} ms`
    case "tool_call":
      return `calling ${event.text}`
    case "tool_result":
      return `${event.text} returned`
    case "done":
      return ""
    default:
      return ""
  }
}

/** Suggestions are built from this user's book and today's tape, never canned. */
function buildSuggestions(held: string[], active: string[]): string[] {
  const prompts: string[] = []
  if (held.length) {
    prompts.push("How is my portfolio doing today, and which position is dragging it?")
    prompts.push(`What is the news on ${held[0]}, and does it change anything for me?`)
    prompts.push("Where is my biggest concentration risk right now?")
  }
  if (active[0]) {
    prompts.push(`Why is ${active[0]} moving today, and what do its fundamentals look like?`)
  }
  if (!held.length) {
    prompts.push("What are the biggest gainers on the market right now?")
    prompts.push("Summarise what my indexed documents say about revenue growth and margins.")
  }
  return prompts.slice(0, 4)
}
