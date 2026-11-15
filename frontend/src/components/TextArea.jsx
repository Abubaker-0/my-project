import { forwardRef } from "react";

export const TextArea = forwardRef(function TextArea({ id, label, error, ...props }, ref) {
  const fieldId = id || props.name;
  return (
    <label className="block text-sm" htmlFor={fieldId}>
      <span className="mb-1 block font-medium text-ink-900">{label}</span>
      <textarea
        ref={ref}
        id={fieldId}
        className="field min-h-24"
        aria-invalid={error ? "true" : "false"}
        {...props}
      />
      {error ? <span className="mt-1 block text-danger">{error}</span> : null}
    </label>
  );
});
