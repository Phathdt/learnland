import type { FormEvent } from 'react'
import { useState } from 'react'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface TranscribeFormProps {
  isRunning: boolean
  onSubmit: (url: string) => void
}

export function TranscribeForm({ isRunning, onSubmit }: TranscribeFormProps) {
  const [url, setUrl] = useState('')

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const trimmed = url.trim()
    if (!trimmed) return
    onSubmit(trimmed)
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <label htmlFor="yt-url" className="sr-only">
        YouTube URL
      </label>
      <Input
        id="yt-url"
        type="url"
        placeholder="https://www.youtube.com/watch?v=..."
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        disabled={isRunning}
        className="flex-1"
        aria-label="YouTube video URL"
      />
      <Button type="submit" disabled={isRunning || !url.trim()}>
        {isRunning ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
            Đang xử lý…
          </>
        ) : (
          'Transcribe'
        )}
      </Button>
    </form>
  )
}
