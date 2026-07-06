/**
 * Minimal type declarations for the YouTube IFrame Player API.
 * Reference: https://developers.google.com/youtube/iframe_api_reference
 */

declare namespace YT {
  /** -1=unstarted, 0=ended, 1=playing, 2=paused, 3=buffering, 5=cued */
  type PlayerState = -1 | 0 | 1 | 2 | 3 | 5

  interface PlayerVars {
    autoplay?: 0 | 1
    controls?: 0 | 1
    rel?: 0 | 1
    modestbranding?: 0 | 1
  }

  interface PlayerOptions {
    videoId: string
    width?: number | string
    height?: number | string
    playerVars?: PlayerVars
    events?: {
      onReady?: (event: PlayerEvent) => void
      onStateChange?: (event: OnStateChangeEvent) => void
      onError?: (event: PlayerEvent) => void
    }
  }

  interface PlayerEvent {
    target: Player
  }

  interface OnStateChangeEvent {
    target: Player
    data: PlayerState
  }

  class Player {
    constructor(elementOrId: HTMLElement | string, options: PlayerOptions)
    playVideo(): void
    pauseVideo(): void
    seekTo(seconds: number, allowSeekAhead?: boolean): void
    getCurrentTime(): number
    getPlayerState(): PlayerState
    destroy(): void
    setPlaybackRate(suggestedRate: number): void
    getPlaybackRate(): number
  }
}

interface Window {
  YT: typeof YT | undefined
  onYouTubeIframeAPIReady: (() => void) | undefined
}
