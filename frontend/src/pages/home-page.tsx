/**
 * Homepage: submit a YouTube URL to transcribe. On success, navigate to the
 * video page for the new transcript.
 */

import { useNavigate } from '@tanstack/react-router'
import { useQueryClient } from '@tanstack/react-query'
import { TranscribeForm } from '@/components/transcribe-form'
import { TranscribeProgress } from '@/components/transcribe-progress'
import { useTranscribe } from '@/hooks/use-transcribe'
import type { TranscriptResult } from '@/api/client'

export function HomePage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { isRunning, stage, percent, start } = useTranscribe((result: TranscriptResult) => {
    // Refresh the history list, then jump to the shadowing player.
    queryClient.invalidateQueries({ queryKey: ['transcripts'] })
    queryClient.setQueryData(['transcript', result.id], result)
    navigate({ to: '/video/$id', params: { id: result.id } })
  })

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold">Transcribe a YouTube video</h1>
        <p className="text-sm text-muted-foreground">
          Paste a URL to pull its transcript, generate IPA phonetics, and start shadowing.
        </p>
      </div>

      <TranscribeForm isRunning={isRunning} onSubmit={start} />

      <TranscribeProgress stage={stage} percent={percent} isRunning={isRunning} />
    </div>
  )
}
