---
name: wc-frontend-skill
description: Initializes and develops WalletConnect frontend applications using the custom Shadcn UI registry. Use when setting up new projects with WalletConnect UI, adding registry components, or creating layouts/pages following dashboard-new conventions.
---

# WalletConnect Frontend Skill

## Goal

Set up and develop frontend applications using the WalletConnect UI registry with consistent patterns from dashboard-new.

## When to use

- Initializing a new project with WalletConnect UI registry
- Adding components from `@walletconnect` registry
- Creating layouts (auth, dashboard, pages)
- Creating pages with proper Suspense boundaries
- Setting up navigation patterns

## When not to use

- Projects not using Next.js/React
- Projects that don't need WalletConnect design system
- Backend-only services

## CRITICAL: Never Manually Write Components

**NEVER attempt to manually write, recreate, or copy component code from the registry.** Always use the shadcn CLI to install components:

```bash
# Install via direct URL
pnpm dlx shadcn@latest add https://dashboard.walletconnect.com/r/button.json

# Or via registry alias (if components.json is configured)
pnpm dlx shadcn@latest add @walletconnect/button
```

The registry components contain complex styling, accessibility features, and animations that must not be manually recreated.

## Important: Tailwind Version

**This registry requires Tailwind CSS v3.4.x** (NOT v4). The ui-foundation package and all registry components are built for Tailwind v3's JavaScript configuration format.

## Registry URL

```
https://dashboard.walletconnect.com/r/{name}.json
```

## Default workflow

### 1. Initialize project with registry

Create `components.json` in project root:

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/styles/globals.css",
    "baseColor": "slate",
    "cssVariables": true
  },
  "iconLibrary": "lucide",
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "registries": {
    "@walletconnect": "https://dashboard.walletconnect.com/r/{name}.json"
  }
}
```

**Important**: The `@/` aliases require corresponding tsconfig.json paths configuration:

```json
// tsconfig.json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

This maps `@/components/ui/button` → `src/components/ui/button.tsx`

### 2. Install dependencies (Tailwind v3)

```bash
# Core Tailwind v3 and plugins
pnpm add -D tailwindcss@^3.4.16 postcss autoprefixer
pnpm add -D tailwindcss-animate@^1.0.7 tailwindcss-react-aria-components@^1.2.0 tailwind-scrollbar@3.1.0

# Runtime dependencies
pnpm add react-aria-components@^1.4.0 react-aria@^3.37.0
pnpm add @phosphor-icons/react tailwind-merge tailwind-variants
pnpm add sonner next-themes motion
```

### 3. Download and install KHTeka fonts

```bash
# Create fonts directory
mkdir -p src/lib/fonts

# Download KHTeka font files
curl -o src/lib/fonts/KHTeka-Light.otf "https://videocontentai-e18a313a.s3.eu-central-1.amazonaws.com/khteka/KHTeka-Light.otf"
curl -o src/lib/fonts/KHTeka-Regular.otf "https://videocontentai-e18a313a.s3.eu-central-1.amazonaws.com/khteka/KHTeka-Regular.otf"
curl -o src/lib/fonts/KHTeka-Medium.otf "https://videocontentai-e18a313a.s3.eu-central-1.amazonaws.com/khteka/KHTeka-Medium.otf"
```

See [REFERENCE.md](./REFERENCE.md) for Next.js font configuration.

### 4. Create Tailwind config (v3 format)

See [REFERENCE.md](./REFERENCE.md) for the complete `tailwind.config.ts`.

### 5. Create globals.css with design tokens

See [REFERENCE.md](./REFERENCE.md) for the complete CSS variables.

### 6. Add components from registry

**CRITICAL: NEVER manually write or recreate registry components.** Always install them using shadcn CLI.

```bash
# Method 1: Using registry alias (requires components.json with registry configured)
pnpm dlx shadcn@latest add @walletconnect/button
pnpm dlx shadcn@latest add @walletconnect/input
pnpm dlx shadcn@latest add @walletconnect/card

# Method 2: Direct URL (works without components.json registry config)
pnpm dlx shadcn@latest add https://dashboard.walletconnect.com/r/button.json
pnpm dlx shadcn@latest add https://dashboard.walletconnect.com/r/input.json
pnpm dlx shadcn@latest add https://dashboard.walletconnect.com/r/card.json

# Common starter set
pnpm dlx shadcn@latest add @walletconnect/tw-utils @walletconnect/globals @walletconnect/button @walletconnect/input @walletconnect/card @walletconnect/toast
```

### 7. Update imports to absolute paths

**After installing components, check and update any relative imports to use absolute paths.** Registry components may contain relative imports that could conflict with your project structure.

```tsx
// ❌ Relative imports (may conflict)
import { cn } from '../lib/tw-utils'
import { Button } from './button'

// ✅ Absolute imports (correct)
import { cn } from '@/lib/tw-utils'
import { Button } from '@/components/ui/button'
```

**Common files to check after installation:**
- `src/components/ui/*.tsx` - UI components
- `src/lib/tw-utils.ts` - Utility imports
- `src/hooks/*.ts` - Hook imports

Search for relative imports and replace with `@/` absolute paths:
```bash
# Find relative imports in installed components
grep -r "from '\.\." src/components/ui/
grep -r "from '\./" src/components/ui/
```

## Available components

| Category | Components |
|----------|------------|
| Utilities | tw-utils, fixed-forward-ref, globals, use-prefetch |
| Icons | icons (app, file, wallet, walletconnect-logo, social-*) |
| Form | button, field, input, checkbox, radio, select, text-area, tag-group, switch, slider |
| Layout | card, accordion, scroll-area, native-scroll-area, sheet, tabs, separator, skeleton |
| Feedback | badge, tooltip, popover, contextual-help, progress-bar, toast |
| Navigation | link, link-default, menu, pagination |
| Other | overlay-arrow, portal |

## Important: Registry Components Have Built-in Styling

**Do NOT override component styles or attempt to manually recreate components.** The registry components from `@walletconnect` already include:

- Hover animations (buttons become more rounded: `rounded-3` → `rounded-9`)
- Active/selected states with accent colors
- Focus rings (`ring-4 ring-accent/40`)
- Loading/pending states
- Dark mode support via CSS variables
- Proper spacing and typography

Simply use the components as-is with their variant props. See [COMPONENTS.md](./COMPONENTS.md) for detailed patterns.

## Container classes

Always use these standard container classes:

```css
.container-base { @apply mx-auto flex w-full flex-1 flex-col items-center gap-12 px-5; }
.container-xl  { @apply container-base max-w-[1400px]; }
.container-lg  { @apply container-base max-w-[900px]; }
.container-sm  { @apply container-base max-w-[560px]; }
```

Usage: `<div className="container-lg">...</div>`

## Component imports pattern

```tsx
// UI components (after installing from registry)
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'

// Utilities
import { cn } from '@/lib/tw-utils'
```

## Validation checklist

- [ ] Using Tailwind CSS v3.4.x (NOT v4)
- [ ] `components.json` has `@walletconnect` registry configured with correct aliases
- [ ] `tsconfig.json` has `@/*` path alias pointing to `./src/*`
- [ ] `tailwind.config.ts` uses JS config format with correct plugins
- [ ] All 3 plugins installed: tailwindcss-animate, tailwindcss-react-aria-components, tailwind-scrollbar
- [ ] `globals.css` includes CSS variables for colors (HSL format without wrapper)
- [ ] Dark mode configured with `darkMode: "class"`
- [ ] KHTeka fonts downloaded to `src/lib/fonts/`
- [ ] Font loaded with `next/font/local` using `--font-KHTeka` variable
- [ ] `<html>` element has `${KHTeka.variable}` class and `suppressHydrationWarning` attribute
- [ ] `next-themes` ThemeProvider configured with `attribute="class"` and `enableSystem`
- [ ] Installed components updated to use `@/` absolute imports (no relative `../` paths)
- [ ] Layouts use proper Suspense boundaries
- [ ] Pages use correct container class (sm/lg/xl)

## Examples

### Example 1: Initialize new project

**Request**: "Set up WalletConnect UI in my Next.js project"

**Actions**:
1. Verify/install Tailwind v3.4.x (not v4)
2. Create `components.json` with registry config
3. Install all required plugins
4. Create `tailwind.config.ts` with full theme configuration
5. Create `globals.css` with CSS variables and container classes
6. Add starter components

### Example 2: Add form components

**Request**: "Add a form with input and button from WalletConnect registry"

**Actions**:
```bash
pnpm dlx shadcn@latest add @walletconnect/button @walletconnect/input @walletconnect/field
```

**Code**:
```tsx
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export function LoginForm() {
  return (
    <form className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <Label>Email</Label>
        <Input type="email" placeholder="you@example.com" />
      </div>
      <Button type="submit">Sign in</Button>
    </form>
  )
}
```

### Example 3: Create dashboard layout

**Request**: "Create a dashboard layout with navigation"

See [LAYOUTS.md](./LAYOUTS.md) for the full dashboard layout pattern.
