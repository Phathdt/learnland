#!/usr/bin/env bash
#
# smoke-test.sh — kiểm tra tự động end-to-end YouTube Transcript App.
#
# Luồng kiểm tra:
#   1. Postgres (docker compose) sẵn sàng
#   2. Alembic migration đã áp dụng
#   3. Backend khởi động, GET /health = 200
#   4. POST /api/transcribe (SSE) với 1 URL thật → nhận event `done`
#   5. GET /api/transcripts (list) chứa bản ghi vừa tạo
#   6. GET /api/transcripts/{id} trả đúng transcript
#   7. Dedup: submit lại cùng URL → trả cache tức thì (dưới ngưỡng thời gian)
#
# Dùng: ./scripts/smoke-test.sh [YOUTUBE_URL]
#   - Không truyền URL → dùng URL mặc định (video ngắn có caption).
#
# Script tự khởi động backend nếu chưa chạy và tự dọn khi kết thúc.

set -uo pipefail

# ── Cấu hình ────────────────────────────────────────────────────────────────
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
BASE_URL="${BASE_URL:-http://localhost:8000}"
# URL mặc định: "Me at the zoo" — 19s, có caption en (nhanh, không cần whisper).
DEFAULT_URL="https://www.youtube.com/watch?v=jNQXAC9IVRw"
TEST_URL="${1:-$DEFAULT_URL}"
DEDUP_MAX_SEC="${DEDUP_MAX_SEC:-10}"   # dedup phải trả nhanh hơn ngưỡng này

# ── Trạng thái ──────────────────────────────────────────────────────────────
PASS=0
FAIL=0
STARTED_BACKEND=0
BACKEND_PID=""
TMP_DIR="$(mktemp -d)"

# ── Tiện ích in kết quả ───────────────────────────────────────────────────────
c_green="\033[32m"; c_red="\033[31m"; c_yellow="\033[33m"; c_reset="\033[0m"
ok()   { echo -e "${c_green}✓${c_reset} $*"; PASS=$((PASS + 1)); }
bad()  { echo -e "${c_red}✗${c_reset} $*"; FAIL=$((FAIL + 1)); }
info() { echo -e "${c_yellow}•${c_reset} $*"; }

cleanup() {
  if [[ "$STARTED_BACKEND" == "1" && -n "$BACKEND_PID" ]]; then
    info "Dừng backend (pid $BACKEND_PID) do script tự khởi động"
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

# ── Bước 1: Postgres ──────────────────────────────────────────────────────────
info "Bước 1: Đảm bảo Postgres đang chạy"
if docker compose -f "$ROOT_DIR/docker-compose.yml" up -d >/dev/null 2>&1; then
  # đợi Postgres sẵn sàng nhận kết nối
  for i in $(seq 1 20); do
    if docker compose -f "$ROOT_DIR/docker-compose.yml" exec -T postgres \
         pg_isready -U ytapp >/dev/null 2>&1; then
      ok "Postgres sẵn sàng"
      break
    fi
    sleep 1
    [[ "$i" == "20" ]] && bad "Postgres không sẵn sàng sau 20s"
  done
else
  bad "Không khởi động được docker compose (postgres)"
fi

# ── Bước 2: Migration ─────────────────────────────────────────────────────────
info "Bước 2: Áp dụng Alembic migration"
[[ -f "$BACKEND_DIR/.env" ]] || cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
if (cd "$BACKEND_DIR" && uv run alembic upgrade head >/dev/null 2>&1); then
  ok "Migration áp dụng (alembic upgrade head)"
else
  bad "Migration thất bại"
fi

# ── Bước 3: Backend + /health ─────────────────────────────────────────────────
info "Bước 3: Kiểm tra backend /health"
if curl -sf -o /dev/null "$BASE_URL/health" 2>/dev/null; then
  ok "Backend đã chạy sẵn tại $BASE_URL"
else
  info "Backend chưa chạy → tự khởi động"
  (cd "$BACKEND_DIR" && uv run uvicorn app.main:app --port 8000 >"$TMP_DIR/uvicorn.log" 2>&1 &)
  # lấy pid của tiến trình uvicorn vừa spawn
  for i in $(seq 1 30); do
    if curl -sf -o /dev/null "$BASE_URL/health" 2>/dev/null; then break; fi
    sleep 1
  done
  BACKEND_PID="$(pgrep -f 'uvicorn app.main:app' | head -1)"
  [[ -n "$BACKEND_PID" ]] && STARTED_BACKEND=1
fi

health="$(curl -s -w '\n%{http_code}' "$BASE_URL/health" 2>/dev/null)"
code="$(echo "$health" | tail -1)"
if [[ "$code" == "200" ]]; then
  ok "GET /health = 200 ($(echo "$health" | head -1))"
else
  bad "GET /health = $code (backend không lên — xem $TMP_DIR/uvicorn.log)"
  echo "── uvicorn.log ──"; tail -15 "$TMP_DIR/uvicorn.log" 2>/dev/null
  echo "Tổng: $PASS pass, $FAIL fail"; exit 1
fi

# ── Hàm: chạy SSE transcribe, trả về file chứa raw stream ────────────────────
# $1 = url, $2 = file output. In ra thời gian chạy (giây, số nguyên).
run_transcribe() {
  local url="$1" out="$2" start end
  start="$(date +%s)"
  curl -sN -X POST "$BASE_URL/api/transcribe" \
    -H 'Content-Type: application/json' \
    -d "{\"url\": \"$url\"}" >"$out" 2>/dev/null
  end="$(date +%s)"
  echo $((end - start))
}

# trích payload JSON của event `done` từ SSE stream ($1 = file)
extract_done() {
  # lấy dòng `data:` ngay sau `event: done`
  awk '/^event: done$/{getline; sub(/^data: /,""); print; exit}' "$1"
}
extract_error() {
  awk '/^event: error$/{getline; sub(/^data: /,""); print; exit}' "$1"
}

# ── Bước 4: Transcribe (SSE) ──────────────────────────────────────────────────
info "Bước 4: POST /api/transcribe (SSE) — $TEST_URL"
sse1="$TMP_DIR/sse1.txt"
elapsed1="$(run_transcribe "$TEST_URL" "$sse1")"
done1="$(extract_done "$sse1")"
err1="$(extract_error "$sse1")"

if [[ -n "$done1" ]]; then
  ok "Nhận event 'done' (${elapsed1}s)"
  # kiểm tra các field bắt buộc trong payload
  id1="$(echo "$done1" | jq -r '.id // empty' 2>/dev/null)"
  src1="$(echo "$done1" | jq -r '.source // empty' 2>/dev/null)"
  clen="$(echo "$done1" | jq -r '(.content // "") | length' 2>/dev/null)"
  if [[ -n "$id1" ]]; then ok "  payload.id = $id1"; else bad "  thiếu payload.id"; fi
  if [[ "$src1" == "youtube_caption" || "$src1" == "whisper" ]]; then
    ok "  payload.source = $src1"
  else
    bad "  source không hợp lệ: '$src1'"
  fi
  if [[ "${clen:-0}" -gt 0 ]]; then ok "  content dài $clen ký tự"; else bad "  content rỗng"; fi
  # kiểm tra segments non-empty với đúng shape
  slen="$(echo "$done1" | jq 'if .segments then (.segments | length) else 0 end' 2>/dev/null)"
  if [[ "${slen:-0}" -gt 0 ]]; then
    ok "  segments: $slen cue"
    seg0_ok="$(echo "$done1" | jq '
      if .segments and (.segments | length) > 0 then
        (.segments[0] | has("start") and has("end") and has("text"))
      else false end' 2>/dev/null)"
    if [[ "$seg0_ok" == "true" ]]; then
      ok "  segments[0] có đủ start/end/text"
    else
      bad "  segments[0] thiếu trường start/end/text"
    fi
    monotonic="$(echo "$done1" | jq '
      [.segments[].start] as $s
      | if ($s | length) > 1
        then [range(1; $s | length)] | all(. as $i | $s[$i] >= $s[$i-1])
        else true end' 2>/dev/null)"
    if [[ "$monotonic" == "true" ]]; then
      ok "  segments.start tăng dần (monotonic)"
    else
      bad "  segments.start không tăng dần"
    fi
  else
    bad "  segments rỗng hoặc null trong payload done"
  fi
  # kiểm tra có ít nhất 1 event progress
  if grep -q '^event: progress$' "$sse1"; then
    ok "  có event 'progress' (stream hoạt động)"
  else
    info "  không có 'progress' (có thể là cache/caption nhanh)"
  fi
elif [[ -n "$err1" ]]; then
  bad "Transcribe trả error: $err1"
  info "  (kiểm tra mạng / yt-dlp / URL. Bỏ qua các bước phụ thuộc.)"
  id1=""
else
  bad "Không nhận được event 'done' hay 'error'"
  echo "── raw SSE (20 dòng đầu) ──"; head -20 "$sse1"
  id1=""
fi

# ── Bước 5: List ──────────────────────────────────────────────────────────────
if [[ -n "${id1:-}" ]]; then
  info "Bước 5: GET /api/transcripts (list)"
  list="$(curl -s "$BASE_URL/api/transcripts" 2>/dev/null)"
  if echo "$list" | jq -e --arg id "$id1" 'map(.id) | index($id) != null' >/dev/null 2>&1; then
    ok "List chứa bản ghi vừa tạo (tổng $(echo "$list" | jq 'length') bản ghi)"
  else
    bad "List không chứa id $id1"
  fi

  # ── Bước 6: Detail ──────────────────────────────────────────────────────────
  info "Bước 6: GET /api/transcripts/{id}"
  detail="$(curl -s -w '\n%{http_code}' "$BASE_URL/api/transcripts/$id1" 2>/dev/null)"
  dcode="$(echo "$detail" | tail -1)"
  dbody="$(echo "$detail" | sed '$d')"
  if [[ "$dcode" == "200" ]] && [[ "$(echo "$dbody" | jq -r '.id')" == "$id1" ]]; then
    ok "Detail trả đúng transcript (200)"
  else
    bad "Detail lỗi (code=$dcode)"
  fi
  # 404 cho id không tồn tại
  fake="00000000-0000-0000-0000-000000000000"
  ncode="$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/api/transcripts/$fake" 2>/dev/null)"
  if [[ "$ncode" == "404" ]]; then ok "  id không tồn tại → 404"; else bad "  id không tồn tại → $ncode (mong đợi 404)"; fi

  # ── Bước 7: Dedup ─────────────────────────────────────────────────────────────
  info "Bước 7: Dedup — submit lại cùng URL"
  sse2="$TMP_DIR/sse2.txt"
  elapsed2="$(run_transcribe "$TEST_URL" "$sse2")"
  done2="$(extract_done "$sse2")"
  id2="$(echo "$done2" | jq -r '.id // empty' 2>/dev/null)"
  if [[ "$id2" == "$id1" ]]; then
    ok "Trả về cùng id (cache hit)"
  else
    bad "Dedup trả id khác: '$id2' (mong đợi '$id1')"
  fi
  if [[ "$elapsed2" -le "$DEDUP_MAX_SEC" ]]; then
    ok "  cache nhanh (${elapsed2}s ≤ ${DEDUP_MAX_SEC}s)"
  else
    bad "  cache chậm (${elapsed2}s > ${DEDUP_MAX_SEC}s) — có thể không hit cache"
  fi
  # dedup không được tạo event progress mới (trả thẳng done)
  if ! grep -q '^event: progress$' "$sse2"; then
    ok "  không có 'progress' ở lần 2 (đúng luồng cache)"
  else
    bad "  có 'progress' ở lần 2 — nghi ngờ xử lý lại thay vì cache"
  fi
else
  info "Bỏ qua bước 5-7 (không có id hợp lệ từ transcribe)"
fi

# ── Tổng kết ──────────────────────────────────────────────────────────────────
echo
echo "══════════════════════════════════════════"
echo -e "Kết quả: ${c_green}${PASS} pass${c_reset}, ${c_red}${FAIL} fail${c_reset}"
echo "══════════════════════════════════════════"
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
