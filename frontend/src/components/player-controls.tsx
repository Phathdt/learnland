/**
 * Transport controls for the shadowing player:
 * play/pause, seek ±5s, prev/next segment.
 */

import { Pause, Play, SkipBack, SkipForward, ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'

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
}: PlayerControlsProps) {
  return (
    // gap-2 (8px) satisfies ≥8px spacing requirement between touch targets
    <div className="flex items-center justify-center gap-2 py-2" role="toolbar" aria-label="Playback controls">
      {/* Secondary buttons: 44px on mobile (≥44px touch target), 36px on md+ */}
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

      {/* Primary play button: 48px on mobile, 40px on md+ — larger than secondary */}
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
  )
}
