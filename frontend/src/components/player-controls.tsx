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
    <div className="flex items-center justify-center gap-2 py-2" role="toolbar" aria-label="Playback controls">
      <Button
        variant="outline"
        size="icon-sm"
        onClick={onPrevSegment}
        disabled={!ready || !hasPrev}
        aria-label="Previous sentence"
        title="Previous sentence"
      >
        <ChevronLeft />
      </Button>

      <Button
        variant="outline"
        size="icon-sm"
        onClick={onSeekBack}
        disabled={!ready}
        aria-label="Seek back 5 seconds"
        title="−5s"
      >
        <SkipBack />
      </Button>

      <Button
        variant="default"
        size="icon"
        onClick={isPlaying ? onPause : onPlay}
        disabled={!ready}
        aria-label={isPlaying ? 'Pause' : 'Play'}
        title={isPlaying ? 'Pause' : 'Play'}
      >
        {isPlaying ? <Pause /> : <Play />}
      </Button>

      <Button
        variant="outline"
        size="icon-sm"
        onClick={onSeekForward}
        disabled={!ready}
        aria-label="Seek forward 5 seconds"
        title="+5s"
      >
        <SkipForward />
      </Button>

      <Button
        variant="outline"
        size="icon-sm"
        onClick={onNextSegment}
        disabled={!ready || !hasNext}
        aria-label="Next sentence"
        title="Next sentence"
      >
        <ChevronRight />
      </Button>
    </div>
  )
}
