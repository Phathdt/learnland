/**
 * Full shadowing player: embeds the YouTube video, transport controls,
 * and the time-synced transcript. Wires useYouTubePlayer + useActiveSegment.
 */

import { useCallback } from 'react'
import { useYouTubePlayer } from '@/hooks/use-youtube-player'
import { useActiveSegment } from '@/hooks/use-active-segment'
import type { Segment } from '@/hooks/use-active-segment'
import { YouTubePlayer } from '@/components/youtube-player'
import { PlayerControls } from '@/components/player-controls'
import { ShadowingTranscript } from '@/components/shadowing-transcript'

const SEEK_DELTA = 5 // seconds

interface ShadowingPlayerProps {
  videoId: string
  segments: Segment[]
}

export function ShadowingPlayer({ videoId, segments }: ShadowingPlayerProps) {
  const { containerRef, ready, isPlaying, play, pause, seekTo, getCurrentTime } =
    useYouTubePlayer(videoId)

  const { activeIndex, seekToSegment } = useActiveSegment({
    segments,
    isPlaying,
    getCurrentTime,
    seekTo,
  })

  const handleSeekBack = useCallback(() => {
    seekTo(Math.max(0, getCurrentTime() - SEEK_DELTA))
  }, [seekTo, getCurrentTime])

  const handleSeekForward = useCallback(() => {
    seekTo(getCurrentTime() + SEEK_DELTA)
  }, [seekTo, getCurrentTime])

  const handleSegmentClick = useCallback(
    (index: number) => {
      seekToSegment(index)
      play()
    },
    [seekToSegment, play],
  )

  const handlePrevSegment = useCallback(() => {
    const target = activeIndex > 0 ? activeIndex - 1 : 0
    seekToSegment(target)
  }, [activeIndex, seekToSegment])

  const handleNextSegment = useCallback(() => {
    const target = activeIndex < segments.length - 1 ? activeIndex + 1 : segments.length - 1
    seekToSegment(target)
  }, [activeIndex, segments.length, seekToSegment])

  return (
    <div className="flex flex-col gap-3">
      <YouTubePlayer containerRef={containerRef} />

      <PlayerControls
        isPlaying={isPlaying}
        ready={ready}
        hasPrev={activeIndex > 0}
        hasNext={activeIndex < segments.length - 1}
        onPlay={play}
        onPause={pause}
        onSeekBack={handleSeekBack}
        onSeekForward={handleSeekForward}
        onPrevSegment={handlePrevSegment}
        onNextSegment={handleNextSegment}
      />

      <ShadowingTranscript
        segments={segments}
        activeIndex={activeIndex}
        onSegmentClick={handleSegmentClick}
      />
    </div>
  )
}
