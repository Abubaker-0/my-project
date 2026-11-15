import { useAuthStore } from "../store/authStore";

export function usePermission(code) {
  const permissions = useAuthStore((state) => state.user?.permissions ?? []);
  return permissions.includes(code);
}
