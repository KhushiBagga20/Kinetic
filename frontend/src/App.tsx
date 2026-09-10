import { Suspense } from "react"
import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { AnimatePresence, motion } from "motion/react"

import { Dock } from "@/components/layout/Dock"
import { Ticker } from "@/components/layout/Ticker"
import { TopBar } from "@/components/layout/TopBar"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { AssistantPage } from "@/pages/AssistantPage"
import { HomePage } from "@/pages/HomePage"
import { KnowledgePage } from "@/pages/KnowledgePage"
import { PortfolioPage } from "@/pages/PortfolioPage"
import { ResearchPage } from "@/pages/ResearchPage"
import { usePreferenceSideEffects } from "@/hooks/use-preference-effects"

const client = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

/** Views cross-fade rather than cut, so navigation feels continuous. */
function RoutedViews() {
  const location = useLocation()
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -6 }}
        transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
      >
        <Routes location={location}>
          <Route path="/" element={<HomePage />} />
          <Route path="/portfolio" element={<PortfolioPage />} />
          <Route path="/research" element={<ResearchPage />} />
          <Route path="/assistant" element={<AssistantPage />} />
          <Route path="/knowledge" element={<KnowledgePage />} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  )
}

function Shell() {
  usePreferenceSideEffects()
  return (
    <div className="min-h-screen">
      <TopBar />
      <Ticker />
      <main className="mx-auto w-full max-w-[1440px] px-5 pb-32 pt-6">
        <Suspense fallback={null}>
          <RoutedViews />
        </Suspense>
      </main>
      <Dock />
      <Toaster position="bottom-right" />
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={client}>
      <TooltipProvider delayDuration={200}>
        <BrowserRouter>
          <Shell />
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  )
}
