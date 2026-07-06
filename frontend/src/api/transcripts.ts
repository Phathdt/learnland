import { apiClient } from './client'
import type { TranscriptResult } from './client'

export async function fetchTranscripts(): Promise<TranscriptResult[]> {
  const { data } = await apiClient.get<TranscriptResult[]>('/transcripts')
  return data
}

export async function fetchTranscript(id: string): Promise<TranscriptResult> {
  const { data } = await apiClient.get<TranscriptResult>(`/transcripts/${id}`)
  return data
}
