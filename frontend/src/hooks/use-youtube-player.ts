/**
 * Hook that loads the YouTube IFrame Player API (idempotent — one script tag) and
 * creates/destroys a YT.Player bound to a container div ref.
 *
 * Handles:
 * - React Strict Mode double-mount via `destroyed` flag
 * - videoId changes: destroys old player, creates new one
 * - isPlaying state derived from onStateChange events
 */

import { useCallback, useEffect, useRef, useState } from 'react'

// Module-level singleton so multiple hook instances share one script load
let apiReadyPromise: Promise<void> | null = null

function loadYouTubeApi(): Promise<void> {
  if (apiReadyPromise) return apiReadyPromise

  apiReadyPromise = new Promise<void>((resolve) => {
    // Already loaded (e.g. hot-reload)
    if (window.YT?.Player) {
      resolve()
      return
    }
    // Register callback before injecting script tag
    const prev = window.onYouTubeIframeAPIReady
    window.onYouTubeIframeAPIReady = () => {
      prev?.()
      resolve()
    }
    if (!document.getElementById('yt-iframe-api')) {
      const script = document.createElement('script')
      script.id = 'yt-iframe-api'
      script.src = 'https://www.youtube.com/iframe_api'
      script.async = true
      document.head.appendChild(script)
    }
  })

  return apiReadyPromise
}

export interface UseYouTubePlayerReturn {
  containerRef: React.RefObject<HTMLDivElement | null>
  ready: boolean
  isPlaying: boolean
  play: () => void
  pause: () => void
  seekTo: (seconds: number) => void
  getCurrentTime: () => number
  setPlaybackRate: (rate: number) => void
}

export function useYouTubePlayer(videoId: string | undefined): UseYouTubePlayerReturn {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const playerRef = useRef<YT.Player | null>(null)
  const [ready, setReady] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)

  useEffect(() => {
    if (!videoId) return

    let destroyed = false

    loadYouTubeApi().then(() => {
      if (destroyed || !containerRef.current) return

      // Destroy previous player before creating a new one
      if (playerRef.current) {
        playerRef.current.destroy()
        playerRef.current = null
      }

      // YT.Player replaces the target element — give it a fresh div
      const mount = document.createElement('div')
      containerRef.current.innerHTML = ''
      containerRef.current.appendChild(mount)

      playerRef.current = new YT.Player(mount, {
        videoId,
        width: '100%',
        height: '100%',
        playerVars: { rel: 0, modestbranding: 1, controls: 1 },
        events: {
          onReady: () => {
            if (!destroyed) setReady(true)
          },
          onStateChange: (evt) => {
            if (!destroyed) setIsPlaying(evt.data === 1) // 1 = PLAYING
          },
        },
      })
    })

    return () => {
      destroyed = true
      setReady(false)
      setIsPlaying(false)
      if (playerRef.current) {
        playerRef.current.destroy()
        playerRef.current = null
      }
    }
  }, [videoId])

  const play = useCallback(() => playerRef.current?.playVideo(), [])
  const pause = useCallback(() => playerRef.current?.pauseVideo(), [])
  const seekTo = useCallback((seconds: number) => {
    playerRef.current?.seekTo(seconds, true)
  }, [])
  const getCurrentTime = useCallback(() => playerRef.current?.getCurrentTime() ?? 0, [])
  const setPlaybackRate = useCallback((rate: number) => {
    playerRef.current?.setPlaybackRate(rate)
  }, [])

  return { containerRef, ready, isPlaying, play, pause, seekTo, getCurrentTime, setPlaybackRate }
}
