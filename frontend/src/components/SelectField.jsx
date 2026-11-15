import { forwardRef } from "react";

export const SelectField = forwardRef(function SelectField(
  { id, label, error, children, ...props },
  ref,
) {
  const fieldId = id || props.name;
  return (
    <label className="block text-sm" htmlFor={fieldId}>
      <span className="mb-1 block font-medium text-ink-900">{label}</span>
      <select
        ref={ref}
        id={fieldId}
        className="field"
        aria-invalid={error ? "true" : "false"}
        {...props}
      >
        {children}
      </select>
      {error ? <span className="mt-1 block text-danger">{error}</span> : null}
    </label>
  );
});
