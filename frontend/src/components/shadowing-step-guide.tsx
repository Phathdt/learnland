/**
 * Hướng dẫn 6 bước luyện shadowing.
 * Mỗi bước là một preset { speed, showTranscript } — click để áp ngay vào player.
 * State active được giữ ở ShadowingPlayer và truyền vào qua props.
 */

import { cn } from '@/lib/utils'

// Định nghĩa cấu trúc một bước shadowing
interface ShadowingStep {
  id: number
  label: string
  hint: string
  showTranscript: boolean
  speed: number
}

/**
 * Danh sách 6 bước shadowing theo thứ tự tăng dần độ khó.
 * Bước 1-2: làm quen, nghe chủ động (speed 1x, có sub).
 * Bước 3-4: shadowing có sub ở tốc độ chậm rồi chuẩn.
 * Bước 5-6: shadowing không sub ở tốc độ chậm rồi chuẩn.
 */
const STEPS: ShadowingStep[] = [
  { id: 1, label: 'Làm quen transcript', hint: 'Đọc & tra phát âm từng từ', showTranscript: true, speed: 1 },
  { id: 2, label: 'Active listening',    hint: 'Nghe cả clip, làm quen giọng', showTranscript: true, speed: 1 },
  { id: 3, label: 'Nghe + đọc (chậm)',   hint: 'Shadowing 0.75x, có sub', showTranscript: true, speed: 0.75 },
  { id: 4, label: 'Nghe + đọc (chuẩn)', hint: 'Shadowing 1.0x, có sub', showTranscript: true, speed: 1 },
  { id: 5, label: 'Bỏ sub (chậm)',       hint: 'Không sub, 0.75x', showTranscript: false, speed: 0.75 },
  { id: 6, label: 'Bỏ sub (chuẩn)',      hint: 'Không sub, 1.0x', showTranscript: false, speed: 1 },
]

interface ShadowingStepGuideProps {
  /** Bước đang active (null = chưa chọn) */
  activeStep: number | null
  /** Callback khi user click một bước — truyền preset để player áp ngay */
  onSelectStep: (step: { id: number; showTranscript: boolean; speed: number }) => void
}

export function ShadowingStepGuide({ activeStep, onSelectStep }: ShadowingStepGuideProps) {
  return (
    <div className="w-full">
      <p className="text-xs text-muted-foreground mb-2 font-medium uppercase tracking-wide">
        Lộ trình luyện tập
      </p>
      {/* Grid 2 cột mobile, 3 cột sm+, 6 cột lg+ để hiện tất cả bước trên 1 hàng */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        {STEPS.map((step) => {
          const isActive = step.id === activeStep
          return (
            <button
              key={step.id}
              type="button"
              onClick={() => onSelectStep({ id: step.id, showTranscript: step.showTranscript, speed: step.speed })}
              aria-current={isActive ? 'step' : undefined}
              aria-label={`Bước ${step.id}: ${step.label}`}
              className={cn(
                // min-h-[44px] đảm bảo touch target ≥44px; p-2 cho không gian nội dung
                'flex flex-col items-start text-left rounded-lg border p-2 min-h-[44px] transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                isActive
                  ? 'bg-primary/10 text-primary border-primary'
                  : 'bg-background text-foreground border-border hover:bg-muted',
              )}
            >
              {/* Số bước nhỏ + label chính */}
              <span className="flex items-center gap-1.5 mb-0.5">
                <span className={cn(
                  'text-xs font-bold leading-none rounded-full flex items-center justify-center size-5 shrink-0',
                  isActive ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground',
                )}>
                  {step.id}
                </span>
                <span className="text-xs font-semibold leading-tight">{step.label}</span>
              </span>
              {/* Gợi ý ngắn */}
              <span className={cn(
                'text-xs leading-tight',
                isActive ? 'text-primary/80' : 'text-muted-foreground',
              )}>
                {step.hint}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
