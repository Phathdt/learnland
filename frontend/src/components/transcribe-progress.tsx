import { Progress } from '@/components/ui/progress'
import type { TranscribeStage } from '@/hooks/use-transcribe'

const STAGE_LABELS: Record<NonNullable<TranscribeStage>, string> = {
  caption_check: 'Kiểm tra phụ đề…',
  download: 'Tải audio…',
  transcribe: 'Đang nhận diện giọng nói…',
}

interface TranscribeProgressProps {
  stage: TranscribeStage
  percent: number
  isRunning: boolean
}

export function TranscribeProgress({ stage, percent, isRunning }: TranscribeProgressProps) {
  if (!isRunning || !stage) return null

  return (
    <div className="space-y-1" role="status" aria-live="polite">
      <p className="text-sm text-muted-foreground">{STAGE_LABELS[stage]}</p>
      <Progress value={percent} className="h-2" aria-label={`Tiến độ: ${Math.round(percent)}%`} />
      <p className="text-xs text-muted-foreground text-right">{Math.round(percent)}%</p>
    </div>
  )
}
