/**
 * Wrapper div that hosts the YT.Player DOM node.
 * The hook replaces this element's content — keep this component thin.
 */

import type { RefObject } from 'react'
import { cn } from '@/lib/utils'

interface YouTubePlayerProps {
  containerRef: RefObject<HTMLDivElement | null>
  className?: string
}

export function YouTubePlayer({ containerRef, className }: YouTubePlayerProps) {
  return (
    <div
      ref={containerRef}
      className={cn('w-full overflow-hidden rounded-lg bg-black aspect-video', className)}
      aria-label="YouTube video player"
    />
  )
}
