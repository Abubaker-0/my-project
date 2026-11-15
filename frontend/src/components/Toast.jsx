/** Renders the toast stack from ToastContext. */
import { useToast } from '../context/ToastContext';

export function ToastViewport() {
  const { items, dismiss } = useToast();
  return (
    <div className="toasts" aria-live="polite">
      {items.map((item) => (
        <button key={item.id} type="button" className={`toast ${item.tone}`} onClick={() => dismiss(item.id)}>
          {item.message}
        </button>
      ))}
    </div>
  );
}
