/**
 * Knowledge — the corpus, and the retriever with its lid off.
 *
 * Anyone can claim their app "uses RAG". This page lets you run the retriever
 * alone and see the exact passages and similarity scores a query returns, with
 * no model involved.
 */

import { useCallback, useState } from "react"
import { useDropzone } from "react-dropzone"
import { AnimatePresence, motion } from "motion/react"
import {
  Database,
  FileText,
  FolderInput,
  Loader2,
  Radio,
  Search,
  Trash2,
  Upload,
} from "lucide-react"
import { toast } from "sonner"

import { StatCard } from "@/components/market/StatCard"
import { Rise, Stagger, StaggerItem } from "@/components/ui/motion-primitives"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useIndexStats, useKnowledgeMutations, useSources } from "@/hooks/use-kinetic"
import { cn } from "@/lib/utils"

export function KnowledgePage() {
  const { data: stats } = useIndexStats()
  const { data: sources = [] } = useSources()
  const { upload, ingestDirectory, capture, remove, reset, search } = useKnowledgeMutations()

  const [symbol, setSymbol] = useState("")
  const [query, setQuery] = useState("")

  const onDrop = useCallback(
    (files: File[]) => {
      if (!files.length) return
      upload.mutate(files, {
        onSuccess: (result) => {
          const total = result.results.reduce((sum, row) => sum + (row.chunks ?? 0), 0)
          toast.success(`Indexed ${total} chunks from ${result.results.length} file(s)`)
        },
        onError: (error) => toast.error(String(error)),
      })
    },
    [upload],
  )

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop })

  return (
    <div className="space-y-6">
      <Rise>
        <h1 className="text-[1.8rem] font-semibold tracking-[-0.035em] text-ink">Knowledge</h1>
        <p className="mt-1.5 text-[0.78rem] text-ink-muted">
          Hybrid retrieval — dense vectors and BM25, fused, filtered and diversified. Everything is
          embedded and stored on this machine.
        </p>
      </Rise>

      <Stagger className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StaggerItem>
          <StatCard label="Document chunks" accent value={stats?.documents ?? 0} detail="your own files" />
        </StaggerItem>
        <StaggerItem>
          <StatCard label="Live market chunks" value={stats?.market_feed ?? 0} detail="timestamped snapshots" />
        </StaggerItem>
        <StaggerItem>
          <StatCard label="Retrieval" value={`top ${stats?.retrieval_k ?? 5}`} detail="after RRF + MMR" />
        </StaggerItem>
        <StaggerItem>
          <StatCard
            label="Chunking"
            value={`${stats?.chunk_size ?? 0}/${stats?.chunk_overlap ?? 0}`}
            detail="finance-aware splitter"
          />
        </StaggerItem>
      </Stagger>

      <Tabs defaultValue="add">
        <TabsList>
          <TabsTrigger value="add">Add</TabsTrigger>
          <TabsTrigger value="sources">Indexed sources</TabsTrigger>
          <TabsTrigger value="retrieval">Test retrieval</TabsTrigger>
        </TabsList>

        {/* -- add ---------------------------------------------------------- */}
        <TabsContent value="add" className="mt-4 grid gap-5 lg:grid-cols-2">
          <div
            {...getRootProps()}
            className={cn(
              "glass flex cursor-pointer flex-col items-center justify-center gap-3 p-10 text-center transition-colors",
              isDragActive && "border-lime/50 bg-lime/[0.07]",
            )}
          >
            <input {...getInputProps()} />
            <motion.div
              animate={isDragActive ? { y: -4, scale: 1.06 } : { y: 0, scale: 1 }}
              transition={{ type: "spring", stiffness: 320, damping: 22 }}
              className="flex size-12 items-center justify-center rounded-2xl border border-lime/25 bg-lime/10"
            >
              {upload.isPending ? (
                <Loader2 className="size-5 animate-spin text-lime" />
              ) : (
                <Upload className="size-5 text-lime" strokeWidth={1.7} />
              )}
            </motion.div>
            <div>
              <p className="text-[0.9rem] font-medium text-ink">
                {isDragActive ? "Drop them here" : "Drop annual reports, fact sheets, notes"}
              </p>
              <p className="mt-1 text-[0.76rem] text-ink-dim">
                PDF, TXT, MD, CSV, HTML, JSON · re-ingesting a file replaces its chunks
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={(event) => {
                event.stopPropagation()
                ingestDirectory.mutate(undefined, {
                  onSuccess: (result) =>
                    toast.success(`Indexed ${Object.keys(result.results).length} file(s) from disk`),
                })
              }}
            >
              <FolderInput className="size-3.5" />
              Ingest the documents folder
            </Button>
          </div>

          <div className="glass p-6">
            <div className="flex items-center gap-2">
              <Radio className="size-4 text-lime" strokeWidth={1.8} />
              <h2 className="text-[0.95rem] font-semibold text-ink">Capture live data</h2>
            </div>
            <p className="mt-2 text-[0.8rem] leading-relaxed text-ink-muted">
              Writes a symbol's live quote, fundamentals and recent headlines into the store, each
              stamped with the moment it was fetched. It is what lets the assistant retrieve
              <em> current</em> evidence rather than only a filing from last quarter.
            </p>
            <form
              className="mt-4 flex gap-2"
              onSubmit={(event) => {
                event.preventDefault()
                capture.mutate(symbol, {
                  onSuccess: (result) => {
                    toast.success(`Indexed ${result.chunks} passages for ${result.symbol}`)
                    setSymbol("")
                  },
                  onError: (error) => toast.error(String(error)),
                })
              }}
            >
              <Input
                value={symbol}
                onChange={(event) => setSymbol(event.target.value)}
                placeholder="reliance, NVDA…"
                className="h-9"
              />
              <Button type="submit" size="sm" className="h-9" disabled={capture.isPending}>
                {capture.isPending ? <Loader2 className="size-3.5 animate-spin" /> : <Database className="size-3.5" />}
                Capture
              </Button>
            </form>
          </div>
        </TabsContent>

        {/* -- sources ------------------------------------------------------ */}
        <TabsContent value="sources" className="mt-4">
          <div className="glass divide-y divide-border/40">
            <AnimatePresence initial={false}>
              {sources.map((source) => (
                <motion.div
                  key={source.source}
                  layout
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0, height: 0 }}
                  className="group flex items-center gap-3 px-5 py-3"
                >
                  <FileText className="size-4 shrink-0 text-ink-dim" strokeWidth={1.7} />
                  <span className="flex-1 truncate text-[0.84rem] text-ink">{source.source}</span>
                  <span className="numeric text-[0.74rem] text-ink-dim">{source.chunks} chunks</span>
                  <button
                    aria-label={`Remove ${source.source}`}
                    onClick={() =>
                      remove.mutate(source.source, { onSuccess: () => toast.success("Removed") })
                    }
                    className="rounded-md p-1.5 text-ink-dim opacity-0 transition-all hover:text-ember group-hover:opacity-100"
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                </motion.div>
              ))}
            </AnimatePresence>

            {!sources.length && (
              <p className="px-5 py-10 text-center text-[0.82rem] text-ink-dim">
                Nothing indexed yet.
              </p>
            )}
          </div>

          {sources.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={() => reset.mutate(undefined, { onSuccess: () => toast.success("Index cleared") })}
            >
              <Trash2 className="size-3.5" />
              Reset the entire index
            </Button>
          )}
        </TabsContent>

        {/* -- retrieval ---------------------------------------------------- */}
        <TabsContent value="retrieval" className="mt-4 space-y-4">
          <div className="glass p-5">
            <p className="text-[0.8rem] leading-relaxed text-ink-muted">
              Run a query through the retriever alone — no model involved. The fastest way to check
              whether a number is actually retrievable before asking about it.
            </p>
            <form
              className="mt-3 flex gap-2"
              onSubmit={(event) => {
                event.preventDefault()
                if (query.trim()) search.mutate({ query: query.trim() })
              }}
            >
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="e.g. operating margin fiscal 2024"
                className="h-9"
              />
              <Button type="submit" size="sm" className="h-9" disabled={search.isPending}>
                {search.isPending ? <Loader2 className="size-3.5 animate-spin" /> : <Search className="size-3.5" />}
                Retrieve
              </Button>
            </form>

            {search.data && (
              <p className="mt-3 font-mono text-[0.7rem] text-ink-dim">
                {search.data.passages.length} passages in {search.data.ms} ms
              </p>
            )}
          </div>

          <Stagger className="space-y-3">
            {(search.data?.passages ?? []).map((passage, index) => (
              <StaggerItem key={`${passage.label}-${index}`}>
                <div className="glass p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[0.72rem] text-lime">S{index + 1}</span>
                    <span className="text-[0.8rem] text-ink">{passage.label}</span>
                    <span
                      className={cn(
                        "rounded-full border px-2 py-0.5 font-mono text-[0.62rem]",
                        passage.kind === "live"
                          ? "border-lime/30 text-lime"
                          : "border-border text-ink-dim",
                      )}
                    >
                      {passage.kind === "live" ? "live market feed" : "document"}
                    </span>
                    <span className="numeric ml-auto text-[0.72rem] text-ink-dim">
                      similarity {passage.score.toFixed(3)}
                    </span>
                  </div>
                  <p className="mt-2.5 whitespace-pre-wrap text-[0.76rem] leading-relaxed text-ink-muted">
                    {passage.text.slice(0, 700)}
                  </p>
                </div>
              </StaggerItem>
            ))}
          </Stagger>
        </TabsContent>
      </Tabs>
    </div>
  )
}
