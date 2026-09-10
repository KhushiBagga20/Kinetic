/**
 * Company search, opened with ⌘K.
 *
 * The query is resolved against Yahoo's live symbol index rather than a local
 * list, so typing "infosys" finds INFY.NS without anyone maintaining a mapping.
 */

import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { AnimatePresence, motion } from "motion/react"
import { CornerDownLeft, Loader2, Search } from "lucide-react"

import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { useSymbolSearch } from "@/hooks/use-kinetic"

export function CommandSearch({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [query, setQuery] = useState("")
  const navigate = useNavigate()
  const { data: results = [], isFetching } = useSymbolSearch(query)

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault()
        onOpenChange(true)
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onOpenChange])

  const go = (symbol: string) => {
    navigate(`/research?symbol=${encodeURIComponent(symbol)}`)
    onOpenChange(false)
    setQuery("")
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="top-[22%] max-w-xl translate-y-0 gap-0 overflow-hidden p-0">
        <DialogTitle className="sr-only">Search for a company</DialogTitle>

        <div className="flex items-center gap-3 border-b border-border/60 px-4">
          {isFetching ? (
            <Loader2 className="size-4 animate-spin text-lime" />
          ) : (
            <Search className="size-4 text-ink-dim" />
          )}
          <Input
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && results[0]) go(results[0].symbol)
            }}
            placeholder="Search any company, index or fund…"
            className="h-14 border-0 bg-transparent px-0 text-base focus-visible:ring-0"
          />
        </div>

        <div className="max-h-80 overflow-y-auto p-2">
          <AnimatePresence mode="popLayout">
            {results.map((result, index) => (
              <motion.button
                key={result.symbol}
                layout
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ delay: index * 0.03 }}
                onClick={() => go(result.symbol)}
                className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-lime/8"
              >
                <span className="w-28 shrink-0 truncate font-mono text-[0.8rem] text-lime">
                  {result.symbol}
                </span>
                <span className="flex-1 truncate text-[0.84rem] text-ink">{result.name}</span>
                <span className="label">{result.exchange || result.type}</span>
                {index === 0 && <CornerDownLeft className="size-3.5 text-ink-dim" />}
              </motion.button>
            ))}
          </AnimatePresence>

          {query.length > 1 && !results.length && !isFetching && (
            <p className="px-3 py-6 text-center text-[0.8rem] text-ink-dim">
              Nothing matched “{query}”.
            </p>
          )}
          {query.length <= 1 && (
            <p className="px-3 py-6 text-center text-[0.8rem] text-ink-dim">
              Type a company name — it is resolved against a live symbol index.
            </p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
