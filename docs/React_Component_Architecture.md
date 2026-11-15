# React component architecture

The redesign stays inside the existing folders. Shared pieces were restyled rather than replaced with a second component library.

| Piece | File | Role |
| --- | --- | --- |
| Appearance | `src/theme.js`, `src/context/ThemeContext.jsx` | Light, dark, and system theme, plus evergreen, sapphire, and indigo |
| Tokens | `src/styles/global.css` | Color, type, spacing, login, shell, tables, forms, dialogs |
| Shell | `src/components/Layout.jsx`, `Sidebar.jsx`, `Topbar.jsx` | Sidebar, header, profile menu, activity |
| Navigation | `src/nav.js` | Role links and groups |
| Controls | `src/components/ui.jsx` | Button, fields, table helpers, modal, drawer, badge, avatar, cards |
| Login | `src/pages/LoginPage.jsx` | Unified sign-in and lamp |
| Dashboards | `src/pages/DashboardPage.jsx` | One page, five role readings of the same API |
| Modules | `src/pages/*` | Existing create, edit, and list flows |

`Avatar` still loads profile photos with the access token. Initials are the fallback when a person has no photo.

Forms that already used React Hook Form and Zod were left on that path. The login schema still requires a username and a password. The password field forwards its ref so “Fill” updates the visible value.
