/**
 * Full shadowing player: embeds the YouTube video, transport controls,
 * time-synced transcript, và hướng dẫn 6 bước shadowing.
 * Wires useYouTubePlayer + useActiveSegment.
 */

import { useCallback, useEffect, useState } from 'react'
import { useYouTubePlayer } from '@/hooks/use-youtube-player'
import { useActiveSegment } from '@/hooks/use-active-segment'
import type { Segment } from '@/hooks/use-active-segment'
import { YouTubePlayer } from '@/components/youtube-player'
import { PlayerControls } from '@/components/player-controls'
import { ShadowingTranscript } from '@/components/shadowing-transcript'
import { ShadowingStepGuide } from '@/components/shadowing-step-guide'

const SEEK_DELTA = 5 // giây

interface ShadowingPlayerProps {
  videoId: string
  segments: Segment[]
}

export function ShadowingPlayer({ videoId, segments }: ShadowingPlayerProps) {
  const { containerRef, ready, isPlaying, play, pause, seekTo, getCurrentTime, setPlaybackRate } =
    useYouTubePlayer(videoId)

  // Tốc độ phát (0.5 / 0.75 / 1.0); mặc định 1x
  const [speed, setSpeed] = useState(1)
  // Hiển thị hay ẩn transcript
  const [showTranscript, setShowTranscript] = useState(true)
  // Bước shadowing đang active (null = chưa chọn bước nào)
  const [activeStep, setActiveStep] = useState<number | null>(null)

  // Re-apply tốc độ sau khi player sẵn sàng hoặc tốc độ thay đổi
  useEffect(() => {
    if (ready) setPlaybackRate(speed)
  }, [ready, speed, setPlaybackRate])

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

  // Áp preset từ step guide: set speed, showTranscript, và đánh dấu bước active
  const applyStep = useCallback((s: { id: number; showTranscript: boolean; speed: number }) => {
    setSpeed(s.speed)
    setShowTranscript(s.showTranscript)
    setActiveStep(s.id)
  }, [])

  return (
    <div className="flex flex-col gap-3">
      {/* Hướng dẫn 6 bước — hiển thị phía trên player */}
      <ShadowingStepGuide activeStep={activeStep} onSelectStep={applyStep} />

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
        speed={speed}
        onSpeedChange={setSpeed}
        showTranscript={showTranscript}
        onToggleTranscript={() => setShowTranscript((v) => !v)}
      />

      {/* Ẩn hoàn toàn (không render) khi showTranscript = false */}
      {showTranscript && (
        <ShadowingTranscript
          segments={segments}
          activeIndex={activeIndex}
          onSegmentClick={handleSegmentClick}
        />
      )}
    </div>
  )
}
