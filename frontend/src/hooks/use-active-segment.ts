/**
 * Hook that polls getCurrentTime() on a 250ms interval while playing,
 * finds the active segment index (last segment with start <= currentTime),
 * and provides a seekToSegment helper.
 *
 * Interval is cleared when paused to avoid unnecessary CPU usage.
 */

import { useCallback, useEffect, useRef, useState } from 'react'

export interface Segment {
  start: number
  end: number
  text: string
  ipa?: string | null
}

interface UseActiveSegmentOptions {
  segments: Segment[]
  isPlaying: boolean
  getCurrentTime: () => number
  seekTo: (seconds: number) => void
}

interface UseActiveSegmentReturn {
  activeIndex: number
  seekToSegment: (index: number) => void
}

export function useActiveSegment({
  segments,
  isPlaying,
  getCurrentTime,
  seekTo,
}: UseActiveSegmentOptions): UseActiveSegmentReturn {
  const [activeIndex, setActiveIndex] = useState(-1)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const findActiveIndex = useCallback(
    (t: number): number => {
      // Binary search for last segment with start <= t
      if (!segments.length) return -1
      let lo = 0
      let hi = segments.length - 1
      let result = -1
      while (lo <= hi) {
        const mid = (lo + hi) >> 1
        if (segments[mid].start <= t) {
          result = mid
          lo = mid + 1
        } else {
          hi = mid - 1
        }
      }
      return result
    },
    [segments],
  )

  useEffect(() => {
    if (!isPlaying) {
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      return
    }

    intervalRef.current = setInterval(() => {
      const t = getCurrentTime()
      setActiveIndex(findActiveIndex(t))
    }, 250)

    return () => {
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [isPlaying, getCurrentTime, findActiveIndex])

  // Reset when segments change (different transcript selected)
  useEffect(() => {
    setActiveIndex(-1)
  }, [segments])

  const seekToSegment = useCallback(
    (index: number) => {
      if (index < 0 || index >= segments.length) return
      seekTo(segments[index].start)
      setActiveIndex(index)
    },
    [segments, seekTo],
  )

  return { activeIndex, seekToSegment }
}
