import { useToastStore } from "../store/toastStore";

const TONES = {
  info: "border-line",
  success: "border-pine-600",
  danger: "border-danger",
};

export function ToastViewport() {
  const toasts = useToastStore((state) => state.toasts);
  const dismiss = useToastStore((state) => state.dismiss);
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className={`pointer-events-auto rounded-xl border-l-4 bg-card px-4 py-3 text-sm shadow-card ${TONES[toast.tone] || TONES.info}`}
        >
          <div className="flex items-start justify-between gap-3">
            <p>{toast.message}</p>
            <button type="button" className="text-ink-500" onClick={() => dismiss(toast.id)}>
              Close
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
