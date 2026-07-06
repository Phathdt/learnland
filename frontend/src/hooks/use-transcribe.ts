import { useCallback, useRef, useState } from 'react'
import { toast } from 'sonner'
import { streamTranscribe, type ProgressEvent, type TranscriptResult } from '@/api/client'

export type TranscribeStage = 'caption_check' | 'download' | 'transcribe' | 'ipa' | null

interface TranscribeState {
  isRunning: boolean
  stage: TranscribeStage
  percent: number
  result: TranscriptResult | null
  error: string | null
}

interface UseTranscribeReturn extends TranscribeState {
  start: (url: string) => Promise<void>
  reset: () => void
}

export function useTranscribe(onDone?: (result: TranscriptResult) => void): UseTranscribeReturn {
  const [state, setState] = useState<TranscribeState>({
    isRunning: false,
    stage: null,
    percent: 0,
    result: null,
    error: null,
  })

  const abortRef = useRef<AbortController | null>(null)

  const reset = useCallback(() => {
    setState({ isRunning: false, stage: null, percent: 0, result: null, error: null })
  }, [])

  const start = useCallback(
    async (url: string) => {
      // Cancel any in-flight request
      abortRef.current?.abort()
      abortRef.current = new AbortController()

      setState({ isRunning: true, stage: 'caption_check', percent: 0, result: null, error: null })

      try {
        await streamTranscribe(
          url,
          {
            onProgress: (evt: ProgressEvent) => {
              setState((prev) => ({
                ...prev,
                stage: evt.stage,
                percent: evt.percent,
              }))
            },
            onDone: (result: TranscriptResult) => {
              setState({ isRunning: false, stage: null, percent: 100, result, error: null })
              onDone?.(result)
            },
            onError: (message: string) => {
              setState((prev) => ({ ...prev, isRunning: false, error: message }))
              toast.error(message)
            },
          },
          abortRef.current.signal,
        )
      } catch (err: unknown) {
        if (err instanceof Error && err.name === 'AbortError') return
        const msg = err instanceof Error ? err.message : 'Unknown error'
        setState((prev) => ({ ...prev, isRunning: false, error: msg }))
        toast.error(msg)
      }
    },
    [onDone],
  )

  return { ...state, start, reset }
}
