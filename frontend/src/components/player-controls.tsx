/**
 * Transport controls cho shadowing player:
 * play/pause, seek ±5s, prev/next segment,
 * segmented speed control (0.5x / 0.75x / 1x), toggle ẩn/hiện transcript.
 */

import { Pause, Play, SkipBack, SkipForward, ChevronLeft, ChevronRight, Eye, EyeOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

// Các mức tốc độ hỗ trợ — YouTube IFrame API chấp nhận 0.5, 0.75, 1.0
const SPEEDS = [0.5, 0.75, 1] as const
type Speed = (typeof SPEEDS)[number]

interface PlayerControlsProps {
  isPlaying: boolean
  ready: boolean
  hasPrev: boolean
  hasNext: boolean
  onPlay: () => void
  onPause: () => void
  onSeekBack: () => void
  onSeekForward: () => void
  onPrevSegment: () => void
  onNextSegment: () => void
  speed: number
  onSpeedChange: (speed: Speed) => void
  showTranscript: boolean
  onToggleTranscript: () => void
}

export function PlayerControls({
  isPlaying,
  ready,
  hasPrev,
  hasNext,
  onPlay,
  onPause,
  onSeekBack,
  onSeekForward,
  onPrevSegment,
  onNextSegment,
  speed,
  onSpeedChange,
  showTranscript,
  onToggleTranscript,
}: PlayerControlsProps) {
  return (
    <div className="flex flex-col gap-2">
      {/* Hàng 1: transport controls — gap-2 (8px) đảm bảo khoảng cách giữa touch targets */}
      <div className="flex items-center justify-center gap-2 py-2" role="toolbar" aria-label="Playback controls">
        {/* Nút phụ: 44px mobile (≥44px touch target), 36px trên md+ */}
        <Button
          variant="outline"
          size="icon-sm"
          onClick={onPrevSegment}
          disabled={!ready || !hasPrev}
          aria-label="Previous sentence"
          title="Previous sentence"
          className="h-11 w-11 md:h-9 md:w-9"
        >
          <ChevronLeft className="size-5 md:size-4" />
        </Button>

        <Button
          variant="outline"
          size="icon-sm"
          onClick={onSeekBack}
          disabled={!ready}
          aria-label="Seek back 5 seconds"
          title="−5s"
          className="h-11 w-11 md:h-9 md:w-9"
        >
          <SkipBack className="size-5 md:size-4" />
        </Button>

        {/* Nút play chính: 48px mobile, 40px md+ — lớn hơn nút phụ */}
        <Button
          variant="default"
          size="icon"
          onClick={isPlaying ? onPause : onPlay}
          disabled={!ready}
          aria-label={isPlaying ? 'Pause' : 'Play'}
          title={isPlaying ? 'Pause' : 'Play'}
          className="h-12 w-12 md:h-10 md:w-10"
        >
          {isPlaying ? <Pause className="size-6 md:size-5" /> : <Play className="size-6 md:size-5" />}
        </Button>

        <Button
          variant="outline"
          size="icon-sm"
          onClick={onSeekForward}
          disabled={!ready}
          aria-label="Seek forward 5 seconds"
          title="+5s"
          className="h-11 w-11 md:h-9 md:w-9"
        >
          <SkipForward className="size-5 md:size-4" />
        </Button>

        <Button
          variant="outline"
          size="icon-sm"
          onClick={onNextSegment}
          disabled={!ready || !hasNext}
          aria-label="Next sentence"
          title="Next sentence"
          className="h-11 w-11 md:h-9 md:w-9"
        >
          <ChevronRight className="size-5 md:size-4" />
        </Button>
      </div>

      {/* Hàng 2: speed control + toggle transcript */}
      <div className="flex items-center justify-center gap-3">
        {/* Segmented speed control: 3 nút liền kề, touch target ≥44px mobile */}
        <div className="flex items-center" role="group" aria-label="Playback speed">
          {SPEEDS.map((s) => {
            const isActive = s === speed
            return (
              <button
                key={s}
                type="button"
                onClick={() => onSpeedChange(s)}
                aria-pressed={isActive}
                aria-label={`Speed ${s}x`}
                className={cn(
                  // h-11 mobile (≥44px), h-9 md+ — px-3 đủ rộng để bấm thoải mái
                  'h-11 md:h-9 px-3 text-sm font-medium border transition-colors',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  // bo góc chỉ đầu + cuối để tạo nhóm liền kề
                  s === SPEEDS[0] && 'rounded-l-lg',
                  s === SPEEDS[SPEEDS.length - 1] && 'rounded-r-lg',
                  // Loại bỏ border kép giữa các nút
                  s !== SPEEDS[0] && '-ml-px',
                  isActive
                    ? 'bg-primary text-primary-foreground border-primary z-10'
                    : 'bg-background text-foreground border-border hover:bg-muted',
                )}
              >
                {s}x
              </button>
            )
          })}
        </div>

        {/* Nút toggle transcript: Eye / EyeOff */}
        <Button
          variant="outline"
          size="icon-sm"
          onClick={onToggleTranscript}
          aria-pressed={showTranscript}
          aria-label={showTranscript ? 'Ẩn transcript' : 'Hiện transcript'}
          title={showTranscript ? 'Ẩn transcript' : 'Hiện transcript'}
          className="h-11 w-11 md:h-9 md:w-9"
        >
          {showTranscript ? (
            <Eye className="size-5 md:size-4" />
          ) : (
            <EyeOff className="size-5 md:size-4" />
          )}
        </Button>
      </div>
    </div>
  )
}
