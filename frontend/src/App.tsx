import { useCallback, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Toaster } from '@/components/ui/sonner'
import { TranscribeForm } from '@/components/transcribe-form'
import { TranscribeProgress } from '@/components/transcribe-progress'
import { TranscriptView } from '@/components/transcript-view'
import { HistorySidebar } from '@/components/history-sidebar'
import { useTranscribe } from '@/hooks/use-transcribe'
import type { TranscriptResult } from '@/api/client'

export default function App() {
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<TranscriptResult | null>(null)

  const handleDone = useCallback(
    (result: TranscriptResult) => {
      setSelected(result)
      // Refresh the history list
      queryClient.invalidateQueries({ queryKey: ['transcripts'] })
    },
    [queryClient],
  )

  const { isRunning, stage, percent, start } = useTranscribe(handleDone)

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar — hidden on mobile, visible md+ */}
      <div className="hidden md:flex md:w-72 flex-shrink-0 flex-col overflow-hidden">
        <HistorySidebar
          selectedId={selected?.id ?? null}
          onSelect={setSelected}
        />
      </div>

      {/* Main panel */}
      <main className="flex flex-1 flex-col overflow-hidden p-4 gap-4">
        <header>
          <h1 className="text-xl font-bold">YouTube Transcript</h1>
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
