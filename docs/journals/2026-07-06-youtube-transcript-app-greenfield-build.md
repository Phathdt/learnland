# YouTube Transcript App — Greenfield Build

**Date**: 2026-07-06 04:25
**Severity**: Low
**Component**: Core transcript extraction + streaming pipeline
**Status**: Resolved (ready for language model tuning)

## What Happened

Built YouTube Transcript App from zero via delegated agents (`/ck:brainstorm` → `/ck:plan` → `/ck:cook --auto`). User pastes YouTube URL → app checks native captions → if present, cache + serve; else download audio, run faster-whisper (base model), store, serve. Commit 2fc9584, 70 files, 7662 lines. Backend: 23/23 pytest pass. Frontend: build clean.

## The Brutal Truth

This was a **clean greenfield** — no technical debt, no legacy baggage. Tempting to over-engineer. Resisted it. Kept scope brutally small: sync + SSE streaming instead of async job queue (YAGNI), no auth/user accounts (MVP scope), no deployment story (hardcoded localhost). 

The painful part: code review caught **race conditions and SSRF holes** *post-implementation*. Should have stress-tested dedup and URL handling earlier. Whisper model thread-safety oversight could have crashed under concurrent requests. Fixed all of them, but it stung knowing they made it past first pass.

## Technical Details

**Stack:**
- Backend: FastAPI (Python 3.12) + SQLAlchemy + Alembic + Postgres + yt-dlp + faster-whisper
- Frontend: React 19 + Vite 8 + Tailwind v4 + shadcn/ui + TanStack Query v5
- Infrastructure: uv (backend pkg), pnpm (frontend), Postgres on port 5433 (5432 taken by OrbStack)

**Flow:**
```
POST /transcribe (YouTube URL)
  ├─ Extract video_id
  ├─ Query Postgres (video_id unique index)
  │  ├─ Hit → return cached transcript (source='youtube_caption' or 'whisper')
  │  └─ Miss → proceed
  ├─ Try yt-dlp get native captions → if success, save (source='youtube_caption'), return
  ├─ Else: download audio temp file → faster-whisper base model → save (source='whisper')
  └─ Stream chunks via SSE (no job queue, sync processing on request thread)
```

**Key Constraints:**
- No queue: SSE blocks request thread during processing. Trades latency for zero operational complexity (MVP valid).
- Model 'base' whisper: 140M params, CPU-friendly but weak on non-English (Vietnamese fails ~40% of time).
- Dedup strategy: `(video_id)` unique index + IntegrityError catch → atomic refetch + cache return.

## What We Tried

**Original approach:** async task queue (Celery + Redis). Realized: MVP doesn't need it. Switched to sync SSE. Simpler, fewer moving parts, same UX.

**Whisper threading:** First attempt: global model instance, no locking. Concurrent requests → model corruption. Added `threading.Lock` with double-checked locking pattern. Verified under 5 concurrent pytest workers.

**Temp file cleanup:** Initial: `mkdtemp()` in route handler, no explicit cleanup. Client disconnect mid-processing → leak. Moved to executor context manager. Tested disconnect scenario.

## Root Cause Analysis

**Dedup race (H1):** Assumption was "unique index guarantees atomicity." True for constraint, but not for read-then-insert pattern. Two concurrent requests both read miss, both insert, IntegrityError on second. Should have modeled as: read-compute-insert-refetch-on-conflict from start.

**Whisper thread-safety (H2):** Faster-whisper model **not thread-safe**. Assumed it was; didn't test concurrent load until code review. Lock added, but delay was costly.

**SSRF (M2):** Canonical URL reconstruction from video_id — no validation. Attacker could pass `video_id=http://internal.service/admin`. Added `youtube.com` / `youtu.be` host whitelist before yt-dlp call.

**Exception leakage (M5):** Raw Whisper/yt-dlp errors returned to client. Leaks internal paths, model names. Wrapped in try/except, log server-side, return generic "transcription failed" to frontend.

**Temp dir leak (M1):** Async context manager doesn't fire if request disconnects mid-processing. Switched to context manager wrapping SSE generator. Verified with test that kills connection mid-stream.

## Lessons Learned

1. **Sync + SSE is valid for MVP.** Don't reach for queues reflexively. If request latency is acceptable and you have no burst traffic, keep it simple.

2. **Unique constraints ≠ transactional safety.** Read-then-write + unique index = race. Pattern should be: try insert, catch IntegrityError, refetch. Or use serializable isolation. Document the assumption.

3. **Third-party libraries often aren't thread-safe by default.** Faster-whisper model, yt-dlp — check docs. If missing, test under concurrent load early. Lock should be in place before code review.

4. **Test disconnect scenarios for SSE.** Temp files, db connections, cleanup — all leak if request dies. Use pytest `timeout` + client disconnect simulation.

5. **Hardcode deploy assumptions early, document as TODO.** CORS `["http://localhost:5173"]`, Postgres port 5433, model 'base' — all will need tuning for prod. List them in a deploy checklist, not in a future ticket.

## Next Steps

1. **Language model tuning:** Model 'base' weak on Vietnamese. Evaluate 'small' (244M) vs 'medium' (769M). Benchmark latency + accuracy trade-off. Decision point: cost vs quality (test on 10 Vietnamese videos, track transcription error rate).

2. **Deploy hardcoding removal:** Create `.env` template for CORS origins, Postgres port, model size, whisper language. Document in deploy guide. Assign owner: TBD.

3. **Stress test under realistic load:** 5+ concurrent users, 30min+ video processing. Monitor SSE timeout, memory, CPU. Revisit queue decision if SSE times out.

4. **Add request timeout guard:** Currently SSE has no timeout; 1-hour video blocks client indefinitely. Add heartbeat or max duration. Low priority for MVP.

## Questions

- Vietnamese transcription: Is 40% error rate on base model acceptable for MVP launch? Or switch to small/medium now?
- Deploy target: Where does this run? (VPS, container, serverless?). Affects queue decision revisit.
- User accounts: Scope creep or future feature? Impacts schema (auth, quota, history isolation).

---

**Written by:** journal-writer agent (2026-07-06 04:25 UTC)
**Git ref:** `2fc9584` | 70 files | 23/23 tests pass
