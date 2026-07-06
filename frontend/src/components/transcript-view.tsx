import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { TranscriptResult } from '@/api/client'

interface TranscriptViewProps {
  transcript: TranscriptResult | null
}

const SOURCE_LABELS: Record<string, string> = {
  youtube_caption: 'YouTube Caption',
  whisper: 'Whisper AI',
}

const SOURCE_VARIANTS: Record<string, 'default' | 'secondary' | 'outline'> = {
  youtube_caption: 'default',
  whisper: 'secondary',
}

export function TranscriptView({ transcript }: TranscriptViewProps) {
  if (!transcript) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted-foreground gap-2">
        <p className="text-lg font-medium">Chưa có transcript</p>
        <p className="text-sm">Nhập URL YouTube và nhấn Transcribe để bắt đầu.</p>
      </div>
    )
  }

  const durationLabel = transcript.duration_sec
    ? `${Math.floor(transcript.duration_sec / 60)}m ${transcript.duration_sec % 60}s`
    : null

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <CardTitle className="text-base font-semibold leading-tight">
            {transcript.title ?? transcript.video_id}
          </CardTitle>
          <div className="flex items-center gap-2 flex-shrink-0">
            <Badge variant={SOURCE_VARIANTS[transcript.source] ?? 'outline'}>
              {SOURCE_LABELS[transcript.source] ?? transcript.source}
            </Badge>
            {transcript.language && (
              <Badge variant="outline">{transcript.language.toUpperCase()}</Badge>
            )}
            {durationLabel && (
              <span className="text-xs text-muted-foreground">{durationLabel}</span>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-96 rounded-md border p-4">
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{transcript.content}</p>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
