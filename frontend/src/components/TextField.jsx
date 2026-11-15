import { forwardRef } from "react";

export const TextField = forwardRef(function TextField({ id, label, error, hint, ...props }, ref) {
  const fieldId = id || props.name;
  return (
    <label className="block text-sm" htmlFor={fieldId}>
      <span className="mb-1 block font-medium text-ink-900">{label}</span>
      <input
        ref={ref}
        id={fieldId}
        className="field"
        aria-invalid={error ? "true" : "false"}
        {...props}
      />
      {error ? <span className="mt-1 block text-danger">{error}</span> : null}
      {!error && hint ? <span className="mt-1 block text-ink-500">{hint}</span> : null}
    </label>
  );
});
