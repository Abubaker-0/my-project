# Responsive design and accessibility

Breakpoints in `frontend/src/styles/global.css`:

- Above 1100px: four KPI cards and a two-column dashboard.
- 1100px and below: two KPI cards and a single content column. This covers a 1024px laptop.
- 860px and below: the login becomes one column, the sidebar becomes a drawer, the menu button appears, and the header name hides. This covers 768px and 390px.

Tables scroll inside their frame instead of widening the page. The weekly schedule does the same. Touch targets on buttons and the lamp cord are at least 32px.

Focus uses a 3px brass outline. Icon buttons have accessible names. The lamp cord exposes `aria-pressed`. Login errors use `role="alert"`. Profile and notification menus close on an outside click.

Color pairs are ink on parchment and ivory, and light text on the deep sidebar. Status badges use a tint plus text, not color alone.

`prefers-reduced-motion: reduce` disables transitions and the lamp glow animation. Dari sets `dir="rtl"` on the document, and spacing uses logical properties.
