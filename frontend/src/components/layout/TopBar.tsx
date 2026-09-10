/**
 * The header: identity on the left, live state on the right.
 *
 * Everything here is true regardless of which view is open — what machine is
 * running the model, what is indexed, and what the user is watching.
 */

import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { AnimatePresence, motion } from "motion/react"
import { Cpu, Loader2, Plus, Search, Star, X } from "lucide-react"
import { toast } from "sonner"

import { Logo } from "./Logo"
import { CommandSearch } from "./CommandSearch"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useIndexStats, useLoadModel, usePreferences, useStatus, useWatchlist } from "@/hooks/use-kinetic"
import { cn } from "@/lib/utils"

export function TopBar() {
  const navigate = useNavigate()
  const { data: status } = useStatus()
  const { data: stats } = useIndexStats()
  const { data: prefs } = usePreferences()
  const loadModel = useLoadModel()
  const watchlist = useWatchlist()
  const [draft, setDraft] = useState("")
  const [searchOpen, setSearchOpen] = useState(false)

  const loaded = status?.model.loaded ?? false

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center gap-3 border-b border-border/60 bg-canvas/70 px-5 backdrop-blur-xl">
      <Logo />

      <span className="ml-1 hidden text-[0.7rem] text-ink-dim md:block">
        {prefs?.name ? `${prefs.name}'s desk` : "Local-first investment research"}
      </span>

      <div className="ml-auto flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setSearchOpen(true)}
          className="h-8 gap-2 text-ink-muted"
        >
          <Search className="size-3.5" />
          <span className="hidden sm:inline">Search a company</span>
          <kbd className="ml-1 hidden rounded border border-border px-1 font-mono text-[0.62rem] text-ink-dim sm:inline">
            ⌘K
          </kbd>
        </Button>

        {/* -- watchlist ---------------------------------------------------- */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="h-8 gap-2 text-ink-muted">
              <Star className="size-3.5" />
              <span className="numeric">{prefs?.watchlist.length ?? 0}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-64 p-2">
            <div className="label px-1 pb-1.5">Watchlist</div>
            <div className="max-h-64 space-y-1 overflow-y-auto">
              <AnimatePresence initial={false}>
                {(prefs?.watchlist ?? []).map((symbol) => (
                  <motion.div
                    key={symbol}
                    layout
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 6 }}
                    className="group flex items-center gap-1"
                  >
                    <button
                      onClick={() => navigate(`/research?symbol=${encodeURIComponent(symbol)}`)}
                      className="flex-1 truncate rounded-md px-2 py-1.5 text-left font-mono text-[0.75rem] text-ink-muted transition-colors hover:bg-lime/10 hover:text-lime"
                    >
                      {symbol}
                    </button>
                    <button
                      aria-label={`Remove ${symbol}`}
                      onClick={() => watchlist.remove(symbol)}
                      className="rounded-md p-1 text-ink-dim transition-colors hover:text-ember"
                    >
                      <X className="size-3" />
                    </button>
                  </motion.div>
                ))}
              </AnimatePresence>
              {!prefs?.watchlist.length && (
                <p className="px-2 py-3 text-[0.72rem] text-ink-dim">
                  Nothing here yet. Add a symbol to keep an eye on it.
                </p>
              )}
            </div>
            <form
              className="mt-2 flex gap-1"
              onSubmit={(event) => {
                event.preventDefault()
                if (!draft.trim()) return
                watchlist.add(draft.trim())
                setDraft("")
              }}
            >
              <Input
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="reliance, NVDA…"
                className="h-8 font-mono text-[0.74rem]"
              />
              <Button type="submit" size="icon" variant="outline" className="size-8 shrink-0">
                <Plus className="size-3.5" />
              </Button>
            </form>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* -- index -------------------------------------------------------- */}
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="hidden items-center gap-1.5 rounded-md border border-border/70 px-2.5 py-1.5 font-mono text-[0.68rem] text-ink-dim lg:flex">
              <span className="live-dot" />
              {(stats?.documents ?? 0) + (stats?.market_feed ?? 0)} chunks
            </div>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            {stats?.documents ?? 0} from your documents · {stats?.market_feed ?? 0} live market
            snapshots, embedded with {stats?.embedding_model.split("/").pop()}
          </TooltipContent>
        </Tooltip>

        {/* -- model -------------------------------------------------------- */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              size="sm"
              variant={loaded ? "outline" : "default"}
              disabled={loadModel.isPending}
              onClick={() =>
                loadModel.mutate(loaded ? "unload" : "load", {
                  onError: (error) => toast.error(String(error)),
                  onSuccess: () => toast.success(loaded ? "Model unloaded" : "Gemma 4 is ready"),
                })
              }
              className="h-8 gap-2"
            >
              {loadModel.isPending ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <span
                  className={cn(
                    "size-1.5 rounded-full",
                    loaded ? "bg-lime shadow-[0_0_0_3px_color-mix(in_oklab,var(--lime)_20%,transparent)]" : "bg-ink-dim",
                  )}
                />
              )}
              <span className="font-mono text-[0.7rem]">
                {loadModel.isPending ? "LOADING" : loaded ? "GEMMA READY" : "LOAD MODEL"}
              </span>
              {!loaded && !loadModel.isPending && <Cpu className="size-3.5" />}
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom" className="max-w-64">
            {status?.model.model} on {status?.model.backend}.{" "}
            {loaded
              ? `Loaded in ${status?.model.load_seconds}s. Nothing you ask it leaves this machine.`
              : "Roughly 15 GB of unified memory. Everything except chat works without it."}
          </TooltipContent>
        </Tooltip>
      </div>

      <CommandSearch open={searchOpen} onOpenChange={setSearchOpen} />
    </header>
  )
}
