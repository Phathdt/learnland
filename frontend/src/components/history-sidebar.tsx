import { useQuery } from '@tanstack/react-query'
import { fetchTranscripts } from '@/api/transcripts'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { TranscriptResult } from '@/api/client'

interface HistorySidebarProps {
  selectedId: string | null
  onSelect: (transcript: TranscriptResult) => void
  /** Hide the built-in header (e.g. when the mobile drawer renders its own). */
  showHeader?: boolean
}

export function HistorySidebar({ selectedId, onSelect, showHeader = true }: HistorySidebarProps) {
  const { data: transcripts, isLoading } = useQuery({
    queryKey: ['transcripts'],
    queryFn: fetchTranscripts,
    refetchInterval: false,
  })

  return (
    <aside className="flex flex-col h-full border-r">
      {showHeader && (
        <div className="px-4 py-3 border-b">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
            History
          </h2>
        </div>
      )}

      <ScrollArea className="flex-1">
        {isLoading && (
          <div className="p-4 space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="space-y-1.5">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-3 w-2/3" />
              </div>
            ))}
          </div>
        )}

        {!isLoading && (!transcripts || transcripts.length === 0) && (
          <p className="p-4 text-sm text-muted-foreground">No transcripts yet.</p>
        )}

        {!isLoading && transcripts && transcripts.length > 0 && (
          <ul role="list" className="p-2 space-y-1">
            {transcripts.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => onSelect(item)}
                  className={cn(
                    'w-full min-h-11 md:min-h-0 text-left rounded-md px-3 py-2.5 md:py-2 text-sm transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    selectedId === item.id && 'bg-accent text-accent-foreground font-medium',
                  )}
                  aria-current={selectedId === item.id ? 'true' : undefined}
                >
                  <p className="truncate">{item.title ?? item.video_id}</p>
                  <div className="flex items-center gap-1 mt-0.5">
                    <Badge
                      variant={item.source === 'youtube_caption' ? 'default' : 'secondary'}
                      className="text-xs h-4 px-1"
                    >
                      {item.source === 'youtube_caption' ? 'Caption' : 'Whisper'}
                    </Badge>
                    {item.language && (
                      <span className="text-xs text-muted-foreground">
                        {item.language.toUpperCase()}
                      </span>
                    )}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </ScrollArea>
    </aside>
  )
}
