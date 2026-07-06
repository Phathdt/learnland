/**
 * Scrollable transcript list for shadowing mode.
 * Highlights the active segment, auto-scrolls it into view,
 * and allows clicking any segment to seek the video there.
 */

import { useEffect, useRef } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import type { Segment } from '@/hooks/use-active-segment'

interface ShadowingTranscriptProps {
  segments: Segment[]
  activeIndex: number
  onSegmentClick: (index: number) => void
}

export function ShadowingTranscript({
  segments,
  activeIndex,
  onSegmentClick,
}: ShadowingTranscriptProps) {
  const activeRef = useRef<HTMLButtonElement | null>(null)

  // Auto-scroll active sentence into view whenever it changes
  useEffect(() => {
    if (activeRef.current) {
      activeRef.current.scrollIntoView({ block: 'center', behavior: 'smooth' })
    }
  }, [activeIndex])

  return (
    <ScrollArea className="h-72 rounded-md border">
      <div className="p-3 flex flex-col gap-0.5">
        {segments.map((seg, i) => {
          const isActive = i === activeIndex
          return (
            <button
              key={i}
              ref={isActive ? activeRef : null}
              type="button"
              onClick={() => onSegmentClick(i)}
              className={cn(
                'w-full text-left rounded px-3 py-1.5 text-sm leading-relaxed transition-colors',
                'hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                isActive
                  ? 'bg-primary/10 text-primary font-semibold'
                  : 'text-foreground',
              )}
              aria-label={`Seek to: ${seg.text}`}
              aria-current={isActive ? 'true' : undefined}
            >
              {seg.text}
            </button>
          )
        })}
      </div>
    </ScrollArea>
  )
}
