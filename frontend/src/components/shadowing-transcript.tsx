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

  // Auto-scroll active sentence into view whenever it changes.
  // Respect prefers-reduced-motion: use 'auto' (instant) when user has reduced motion enabled.
  useEffect(() => {
    if (activeRef.current) {
      const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
      activeRef.current.scrollIntoView({
        block: 'center',
        behavior: reducedMotion ? 'auto' : 'smooth',
      })
    }
  }, [activeIndex])

  return (
    // h-[50dvh] on mobile to use more screen real estate; h-72 on md+
    <ScrollArea className="h-[50dvh] md:h-72 rounded-md border">
      <div className="p-3 flex flex-col gap-1">
        {segments.map((seg, i) => {
          const isActive = i === activeIndex
          return (
            <button
              key={i}
              ref={isActive ? activeRef : null}
              type="button"
              onClick={() => onSegmentClick(i)}
              className={cn(
                // min-h-11 ensures ≥44px touch target on mobile; py-3 for comfortable tap area
                'w-full text-left rounded px-3 py-3 md:py-1.5 min-h-11 text-sm leading-relaxed transition-colors',
                'hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                isActive
                  ? 'bg-primary/10 text-primary font-semibold'
                  : 'text-foreground',
              )}
              aria-label={`Seek to: ${seg.text}`}
              aria-current={isActive ? 'true' : undefined}
            >
              {seg.text}
              {seg.ipa && (
                <span className="block text-xs text-muted-foreground font-mono">{seg.ipa}</span>
              )}
            </button>
          )
        })}
      </div>
    </ScrollArea>
  )
}
