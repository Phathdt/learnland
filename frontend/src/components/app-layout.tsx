/**
 * Root layout: persistent history sidebar (desktop) + mobile drawer,
 * with the routed page rendered in the main panel via <Outlet>.
 */

import { useEffect, useState } from 'react'
import { Outlet, useNavigate, useParams } from '@tanstack/react-router'
import { Menu, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { HistorySidebar } from '@/components/history-sidebar'
import { cn } from '@/lib/utils'
import type { TranscriptResult } from '@/api/client'

export function AppLayout() {
  const navigate = useNavigate()
  const [drawerOpen, setDrawerOpen] = useState(false)

  // Highlight the sidebar item matching the current /video/$id route, if any.
  const params = useParams({ strict: false }) as { id?: string }
  const selectedId = params.id ?? null

  function handleSelect(transcript: TranscriptResult) {
    navigate({ to: '/video/$id', params: { id: transcript.id } })
    setDrawerOpen(false)
  }

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
        <HistorySidebar selectedId={selectedId} onSelect={handleSelect} />
      </div>

      {/* Mobile drawer: scrim + sliding panel */}
      <div
        className={cn(
          'fixed inset-0 z-40 md:hidden motion-safe:transition-opacity motion-safe:duration-200',
          drawerOpen
            ? 'pointer-events-auto opacity-100'
            : 'pointer-events-none opacity-0'
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
            drawerOpen ? 'translate-x-0' : '-translate-x-full'
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
              selectedId={selectedId}
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
          <button
            type="button"
            onClick={() => navigate({ to: '/' })}
            className="text-xl font-bold"
          >
            learnland
          </button>
        </header>

        <div className="flex-1 overflow-auto">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
