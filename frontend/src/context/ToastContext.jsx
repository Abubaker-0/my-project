/**
 * Short-lived success and error notices. Pages call toast() after a save
 * instead of inventing their own banners.
 */
import { createContext, useCallback, useContext, useMemo, useState } from 'react';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [items, setItems] = useState([]);

  const dismiss = useCallback((id) => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const toast = useCallback((message, tone = 'info') => {
    const id = `${Date.now()}-${Math.random()}`;
    setItems((current) => [...current, { id, message, tone }]);
    window.setTimeout(() => dismiss(id), 4200);
  }, [dismiss]);

  const value = useMemo(() => ({ items, toast, dismiss }), [items, toast, dismiss]);
  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

export function useToast() {
  return useContext(ToastContext);
}
