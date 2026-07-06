import axios from 'axios'

// Backend origin, baked at build time. Defaults to the local dev backend.
// The backend mounts all routes under /api, so append it once here.
export const API_BASE = `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/api`

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

// --- SSE types ---

export interface ProgressEvent {
  stage: 'caption_check' | 'download' | 'transcribe' | 'ipa'
  percent: number
}

export interface TranscriptSegment {
  start: number
  end: number
  text: string
  ipa?: string | null
}

export interface TranscriptResult {
  id: string
  video_url: string
  video_id: string
  title: string | null
  source: string
  language: string | null
  content: string
  segments?: TranscriptSegment[] | null
  duration_sec: number | null
  created_at: string
}

export interface SSEHandlers {
  onProgress: (evt: ProgressEvent) => void
  onDone: (result: TranscriptResult) => void
  onError: (message: string) => void
}

/**
 * POST /api/transcribe and consume the SSE response.
 * Uses fetch + ReadableStream because EventSource doesn't support POST.
 * Buffers partial chunks and only emits complete SSE messages (delimited by \n\n).
 */
export async function streamTranscribe(
  url: string,
  handlers: SSEHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE}/transcribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
    signal,
  })

  if (!response.ok) {
    handlers.onError(`Server error: ${response.status} ${response.statusText}`)
    return
  }

  const reader = response.body?.getReader()
  if (!reader) {
    handlers.onError('No response body')
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // SSE messages are delimited by double newlines
      const messages = buffer.split('\n\n')
      // Keep the last (potentially incomplete) chunk in the buffer
      buffer = messages.pop() ?? ''

      for (const message of messages) {
        if (!message.trim()) continue

        let eventType = 'message'
        let data = ''

        for (const line of message.split('\n')) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            data = line.slice(6).trim()
          }
        }

        if (!data) continue

        try {
          const parsed = JSON.parse(data)
          if (eventType === 'progress') {
            handlers.onProgress(parsed as ProgressEvent)
          } else if (eventType === 'done') {
            handlers.onDone(parsed as TranscriptResult)
          } else if (eventType === 'error') {
            handlers.onError((parsed as { message: string }).message)
          }
        } catch {
          // Malformed JSON — skip
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}
