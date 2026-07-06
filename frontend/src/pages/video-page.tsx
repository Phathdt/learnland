/**
 * Video page: loads a single transcript by id and renders the shadowing player.
 */

import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from '@tanstack/react-router'
import { fetchTranscript } from '@/api/transcripts'
import { TranscriptView } from '@/components/transcript-view'
import { Skeleton } from '@/components/ui/skeleton'
import { buttonVariants } from '@/components/ui/button'

export function VideoPage() {
  const { id } = useParams({ from: '/layout/video/$id' })

  const { data: transcript, isLoading, isError } = useQuery({
    queryKey: ['transcript', id],
    queryFn: () => fetchTranscript(id),
  })

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-6 w-2/3" />
        <Skeleton className="aspect-video w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  if (isError || !transcript) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-muted-foreground">
        <p className="text-lg font-medium">Transcript not found</p>
        <Link to="/" className={buttonVariants({ variant: 'outline' })}>
          Back to home
        </Link>
      </div>
    )
  }

  return <TranscriptView transcript={transcript} />
}
