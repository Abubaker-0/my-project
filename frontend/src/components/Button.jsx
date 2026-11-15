const VARIANTS = {
  primary: "bg-pine-700 text-white hover:bg-pine-800",
  secondary: "border border-line bg-white text-ink-950 hover:bg-paper",
  ghost: "text-ink-700 hover:bg-white/10",
  danger: "bg-danger text-white hover:bg-red-800",
};

export function Button({
  variant = "primary",
  type = "button",
  className = "",
  disabled,
  children,
  ...props
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-60 ${VARIANTS[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
