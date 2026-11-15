# Design system and color palette

The interface uses one token set in `frontend/src/styles/global.css`. Evergreen Academic is the default. Sapphire Modern and Royal Indigo are optional and are stored as `ctcms-palette`.

## Evergreen Academic

| Token | Light | Dark | Use |
| --- | --- | --- | --- |
| Ink | `#1E3038` | `#E9F0EE` | Text |
| Primary | `#28594F` | `#78BBA9` | Buttons, active states |
| Accent | `#B18A54` | `#E2BD80` | Focus ring, lamp, small highlights |
| Canvas | `#F6F3EC` | `#101B20` | Page background |
| Surface | `#FFFEFA` | `#19292D` | Cards, header, forms |
| Sidebar | `#1B3336` | `#101F23` | Navigation |
| Line | `#E4E8E2` | `#304348` | Borders |
| Success | `#20805B` | `#8ED4AE` | Active and paid |
| Warning | `#AF7C2D` | `#E2BD80` | Pending and overdue |
| Danger | `#9C3B32` | `#FFAAA3` | Rejected and errors |

## Alternates

- Sapphire Modern: primary `#3B65E6`, accent `#36A8B5`.
- Royal Indigo: primary `#5A49D8`, accent `#1D9E92`.

Dark variants lighten the primary so text on buttons stays readable.

## Type and space

- UI text: Inter, with Vazirmatn when the language is Dari.
- Headings: Georgia / Palatino.
- Spacing steps: 8, 12, 14, 18, 28, 40.
- Cards and inputs use a 12–14px radius.
- Icons are Lucide outline icons at 16–18px.

## Theme behavior

`frontend/src/theme.js` applies `data-theme` and `data-palette` before React renders. The choice is `light`, `dark`, or `system`, stored in `ctcms-theme`. Motion is removed when the user prefers reduced motion.
