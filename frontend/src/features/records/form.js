import { errorMessage, fieldErrors } from "../../utils/errors";

export function reportError(error, setError, push) {
  const fields = fieldErrors(error);
  Object.entries(fields).forEach(([field, message]) => setError(field, { message }));
  if (!Object.keys(fields).length) {
    push({ tone: "danger", message: errorMessage(error) });
  }
}

export function emptyToNull(value) {
  return value ? value : null;
}
