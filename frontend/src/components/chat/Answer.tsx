/**
 * The assistant's answer, rendered.
 *
 * The model writes markdown: headings, bullets, and — for anything with more
 * than one dimension — GitHub-flavoured tables. Numeric columns are detected
 * and right-aligned in a monospace face so figures line up, and a fenced
 * `kinetic-chart` block becomes a real chart.
 */

import { memo } from "react"
import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"

import { ChartBlock, parseChartSpec } from "./ChartBlock"
import { cn } from "@/lib/utils"

const NUMERIC = /^[\s(]*[+-]?[₹$€£]?[\d,]+\.?\d*\s*[%x×]?[\s)]*(USD|INR|Cr|L|B|M|K)?$/i

function looksNumeric(node: unknown): boolean {
  const text = String(node ?? "").trim()
  return text.length > 0 && NUMERIC.test(text)
}

export const Answer = memo(function Answer({
  content,
  streaming,
}: {
  content: string
  streaming?: boolean
}) {
  return (
    <div className="text-[0.88rem] leading-[1.72] text-ink">
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h3 className="section-title mb-2 mt-4 first:mt-0">{children}</h3>
          ),
          h2: ({ children }) => (
            <h3 className="section-title mb-2 mt-4 first:mt-0">{children}</h3>
          ),
          h3: ({ children }) => (
            <h4 className="mb-1.5 mt-4 text-[0.82rem] font-semibold uppercase tracking-[0.08em] text-lime first:mt-0">
              {children}
            </h4>
          ),
          p: ({ children }) => <p className="mb-2.5 last:mb-0">{children}</p>,
          strong: ({ children }) => (
            <strong className="font-semibold text-ink">{children}</strong>
          ),
          em: ({ children }) => <em className="text-ink-muted">{children}</em>,
          ul: ({ children }) => (
            <ul className="mb-2.5 space-y-1.5 last:mb-0">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="mb-2.5 list-decimal space-y-1.5 pl-5 last:mb-0">{children}</ol>
          ),
          li: ({ children, ...props }) =>
            "ordered" in props && props.ordered ? (
              <li>{children}</li>
            ) : (
              <li className="relative pl-4 before:absolute before:left-0 before:top-[0.65em] before:size-1 before:rounded-full before:bg-lime/70">
                {children}
              </li>
            ),
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className="text-lime underline decoration-lime/30 underline-offset-2 hover:decoration-lime"
            >
              {children}
            </a>
          ),
          blockquote: ({ children }) => (
            <blockquote className="my-2.5 border-l-2 border-lime/40 pl-3 text-ink-muted">
              {children}
            </blockquote>
          ),
          hr: () => <div className="hairline my-4" />,

          // -- tables ---------------------------------------------------------
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto rounded-xl border border-border/60">
              <table className="w-full border-collapse text-[0.8rem]">{children}</table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-white/[0.03]">{children}</thead>
          ),
          th: ({ children }) => (
            <th
              scope="col"
              className={cn(
                "label border-b border-border/60 px-3 py-2 font-normal",
                looksNumeric(children) ? "text-right" : "text-left",
              )}
            >
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td
              className={cn(
                "border-b border-border/30 px-3 py-2 text-ink-muted",
                looksNumeric(children) && "numeric text-right text-ink",
              )}
            >
              {children}
            </td>
          ),
          tr: ({ children }) => (
            <tr className="transition-colors last:border-0 hover:bg-lime/[0.04]">{children}</tr>
          ),

          // A code block renders its own container, so the default <pre> wrapper
          // is dropped — otherwise a chart would end up nested inside one.
          pre: ({ children }) => <>{children}</>,

          // -- code, and the chart escape hatch --------------------------------
          code: ({ className, children }) => {
            const language = /language-([\w-]+)/.exec(className ?? "")?.[1]
            const source = String(children).replace(/\n$/, "")

            if (language === "kinetic-chart") {
              const spec = parseChartSpec(source)
              if (spec) return <ChartBlock spec={spec} />
            }
            if (!language) {
              return (
                <code className="rounded bg-lime/10 px-1.5 py-0.5 font-mono text-[0.78rem] text-lime">
                  {children}
                </code>
              )
            }
            return (
              <pre className="my-2.5 overflow-x-auto rounded-lg border border-border/60 bg-void/50 p-3">
                <code className="font-mono text-[0.76rem] text-ink-muted">{source}</code>
              </pre>
            )
          },
        }}
      >
        {content}
      </Markdown>

      {streaming && (
        <span className="ml-0.5 inline-block h-[1em] w-[7px] translate-y-[2px] bg-lime align-baseline animate-[caret_1.05s_step-end_infinite]" />
      )}
    </div>
  )
})
