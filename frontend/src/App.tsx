import { useCallback, useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Menu, X } from 'lucide-react'
import { Toaster } from '@/components/ui/sonner'
import { Button } from '@/components/ui/button'
import { TranscribeForm } from '@/components/transcribe-form'
import { TranscribeProgress } from '@/components/transcribe-progress'
import { TranscriptView } from '@/components/transcript-view'
import { HistorySidebar } from '@/components/history-sidebar'
import { useTranscribe } from '@/hooks/use-transcribe'
import { cn } from '@/lib/utils'
import type { TranscriptResult } from '@/api/client'

export default function App() {
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<TranscriptResult | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const handleDone = useCallback(
    (result: TranscriptResult) => {
      setSelected(result)
      // Refresh the history list
      queryClient.invalidateQueries({ queryKey: ['transcripts'] })
    },
    [queryClient],
  )

  const { isRunning, stage, percent, start } = useTranscribe(handleDone)

  // On mobile, selecting a history item should also close the drawer.
  const handleSelect = useCallback((transcript: TranscriptResult) => {
    setSelected(transcript)
    setDrawerOpen(false)
  }, [])

  // Close the drawer with Escape for keyboard users.
  useEffect(() => {
    if (!drawerOpen) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setDrawerOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [drawerOpen])

  return (
    <div className="flex h-dvh overflow-hidden">
      {/* Sidebar — persistent on desktop (md+) */}
      <div className="hidden md:flex md:w-72 flex-shrink-0 flex-col overflow-hidden">
        <HistorySidebar selectedId={selected?.id ?? null} onSelect={handleSelect} />
      </div>

      {/* Mobile drawer: scrim + sliding panel */}
      <div
        className={cn(
          'fixed inset-0 z-40 md:hidden motion-safe:transition-opacity motion-safe:duration-200',
          drawerOpen ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0',
        )}
        aria-hidden={!drawerOpen}
      >
        {/* Scrim */}
        <button
          type="button"
          className="absolute inset-0 bg-black/50"
          aria-label="Close history"
          tabIndex={drawerOpen ? 0 : -1}
          onClick={() => setDrawerOpen(false)}
        />
        {/* Panel */}
        <div
          className={cn(
            'absolute inset-y-0 left-0 flex w-[85%] max-w-xs flex-col bg-sidebar shadow-xl',
            'motion-safe:transition-transform motion-safe:duration-200 motion-safe:ease-out',
            'pl-[env(safe-area-inset-left)]',
            drawerOpen ? 'translate-x-0' : '-translate-x-full',
          )}
          role="dialog"
          aria-modal="true"
          aria-label="Transcript history"
        >
          <div className="flex items-center justify-between border-b px-4 py-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              History
            </h2>
            <Button
              variant="ghost"
              size="icon"
              className="h-11 w-11"
              onClick={() => setDrawerOpen(false)}
              aria-label="Close"
            >
              <X />
            </Button>
          </div>
          <div className="flex-1 overflow-hidden">
            <HistorySidebar
              selectedId={selected?.id ?? null}
              onSelect={handleSelect}
              showHeader={false}
            />
          </div>
        </div>
      </div>

      {/* Main panel */}
      <main className="flex flex-1 flex-col overflow-hidden gap-4 p-4 pt-[max(1rem,env(safe-area-inset-top))]">
        <header className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            className="h-11 w-11 md:hidden"
            onClick={() => setDrawerOpen(true)}
            aria-label="Open history"
          >
            <Menu />
          </Button>
          <h1 className="text-xl font-bold">learnland</h1>
        </header>

        <TranscribeForm isRunning={isRunning} onSubmit={start} />

        <TranscribeProgress stage={stage} percent={percent} isRunning={isRunning} />

        <div className="flex-1 overflow-auto">
          <TranscriptView transcript={selected} />
        </div>
      </main>

      <Toaster richColors position="top-right" />
    </div>
  )
}
