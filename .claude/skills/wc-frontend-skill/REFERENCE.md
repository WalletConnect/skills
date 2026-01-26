# WalletConnect Frontend Reference

## KHTeka Font Installation

The WalletConnect design system uses the **KHTeka** font family. Follow these steps to install it:

### Step 1: Download font files

```bash
# Create fonts directory
mkdir -p src/lib/fonts

# Download all font weights
curl -o src/lib/fonts/KHTeka-Light.otf "https://videocontentai-e18a313a.s3.eu-central-1.amazonaws.com/khteka/KHTeka-Light.otf"
curl -o src/lib/fonts/KHTeka-Regular.otf "https://videocontentai-e18a313a.s3.eu-central-1.amazonaws.com/khteka/KHTeka-Regular.otf"
curl -o src/lib/fonts/KHTeka-Medium.otf "https://videocontentai-e18a313a.s3.eu-central-1.amazonaws.com/khteka/KHTeka-Medium.otf"
```

### Step 2: Configure Next.js local font (App Router)

```tsx
// src/app/layout.tsx
import localFont from "next/font/local";

const KHTeka = localFont({
  variable: "--font-KHTeka",
  src: [
    {
      path: "../lib/fonts/KHTeka-Light.otf",
      weight: "300",
      style: "normal",
    },
    {
      path: "../lib/fonts/KHTeka-Regular.otf",
      weight: "400",
      style: "normal",
    },
    {
      path: "../lib/fonts/KHTeka-Medium.otf",
      weight: "500",
      style: "normal",
    },
  ],
});

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${KHTeka.variable} antialiased`} suppressHydrationWarning>
      <body>
        {/* ... */}
      </body>
    </html>
  );
}
```

### Step 3: Reference in Tailwind config

The font CSS variable `--font-KHTeka` is referenced in the Tailwind config:

```ts
// tailwind.config.ts
theme: {
  fontFamily: {
    sans: ["var(--font-KHTeka)", ...fontFamily.sans],
  },
}
```

### Font Weights Reference

| Weight | File | CSS Value | Usage |
|--------|------|-----------|-------|
| Light | KHTeka-Light.otf | 300 | Subtle text, large displays |
| Regular | KHTeka-Regular.otf | 400 | Body text, default |
| Medium | KHTeka-Medium.otf | 500 | Headings, emphasis |

---

## Tailwind CSS Version Requirement

**IMPORTANT**: This registry requires **Tailwind CSS v3.4.x**. Do NOT use Tailwind v4.

| Package | Version |
|---------|---------|
| tailwindcss | ^3.4.16 |
| tailwindcss-animate | ^1.0.7 |
| tailwindcss-react-aria-components | ^1.2.0 |
| tailwind-scrollbar | 3.1.0 |
| postcss | ^8.4.49 |
| autoprefixer | ^10.4.20 |

## Complete Tailwind Config (v3 Format)

```ts
// tailwind.config.ts
import type { Config } from "tailwindcss";
import { fontFamily } from "tailwindcss/defaultTheme";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  darkMode: "class",
  theme: {
    fontFamily: {
      sans: ["var(--font-KHTeka)", ...fontFamily.sans],
    },

    fontSize: {
      sm: ["0.75rem", { lineHeight: "0.875rem", letterSpacing: "-0.01em" }],
      md: ["0.875rem", { lineHeight: "1rem", letterSpacing: "-0.01em" }],
      lg: ["1rem", { lineHeight: "1.125rem", letterSpacing: "-0.01em" }],
      xl: ["1.125rem", { lineHeight: "1.25rem", letterSpacing: "-0.01125rem" }],
      h6: ["1.25rem", { lineHeight: "1.25rem", letterSpacing: "-0.03em" }],
      h5: ["1.625rem", { lineHeight: "1.625rem", letterSpacing: "-0.01em" }],
      h4: ["2rem", { lineHeight: "2rem", letterSpacing: "-0.01em" }],
      h3: ["2.375rem", { lineHeight: "2.375rem", letterSpacing: "-0.02em" }],
      h2: ["2.75rem", { lineHeight: "2.75rem", letterSpacing: "-0.02em" }],
      h1: ["3.125rem", { lineHeight: "3.125rem", letterSpacing: "-0.02em" }],
    },

    borderRadius: {
      1: "0.25rem",
      2: "0.5rem",
      3: "0.75rem",
      4: "1rem",
      5: "1.25rem",
      6: "1.5rem",
      7: "1.75rem",
      8: "2rem",
      9: "2.25rem",
      10: "2.5rem",
      11: "3rem",
      12: "3.5rem",
      13: "4rem",
      full: "9999px",
    },

    colors: {
      transparent: "transparent",
      main: "hsl(var(--main))",
      white: "hsl(var(--white))",

      gray: {
        50: "hsl(var(--gray-50))",
        100: "hsl(var(--gray-100))",
        200: "hsl(var(--gray-200))",
        300: "hsl(var(--gray-300))",
        400: "hsl(var(--gray-400))",
        500: "hsl(var(--gray-500))",
        600: "hsl(var(--gray-600))",
        700: "hsl(var(--gray-700))",
        800: "hsl(var(--gray-800))",
        900: "hsl(var(--gray-900))",
        1000: "hsl(var(--gray-1000))",
      },

      foreground: {
        primary: "hsl(var(--foreground-primary))",
        secondary: "hsl(var(--foreground-secondary))",
        tertiary: "hsl(var(--foreground-tertiary))",
        accent: {
          10: "hsl(var(--foreground-accent), 0.1)",
          40: "hsl(var(--foreground-accent), 0.4)",
          60: "hsl(var(--foreground-accent), 0.6)",
          secondary: {
            10: "hsl(var(--foreground-accent-secondary), 0.1)",
            40: "hsl(var(--foreground-accent-secondary), 0.4)",
            60: "hsl(var(--foreground-accent-secondary), 0.6)",
          },
        },
      },

      icon: {
        primary: "hsl(var(--icon-primary))",
        inverse: "hsl(var(--icon-inverse))",
      },

      accent: "hsl(var(--accent), <alpha-value>)",
      "accent-secondary": "hsl(var(--accent-secondary), <alpha-value>)",
      success: "hsl(var(--success), <alpha-value>)",
      error: "hsl(var(--error), <alpha-value>)",
      warning: "hsl(var(--warning), <alpha-value>)",

      // Brand colors
      walletkit: "#FFB800",
      appkit: "#FF573B",
      dashboard: "#0988F0",
      docs: "#008847",
      premium: "#FFD700",
    },

    extend: {
      spacing: {
        "1.5": "0.375rem",
      },

      textColor: {
        primary: "hsl(var(--text-primary))",
        secondary: "hsl(var(--text-secondary))",
        tertiary: "hsl(var(--text-tertiary))",
        inverse: "hsl(var(--text-inverse))",
      },

      backgroundColor: {
        primary: "hsl(var(--bg-primary))",
        inverse: "hsl(var(--bg-inverse))",
        border: "hsl(var(--border-primary))",
      },

      backgroundImage: {
        "fade-top-foreground-primary": `linear-gradient(to bottom, theme(colors.foreground.primary) 30%, transparent)`,
        "fade-bottom-foreground-primary": `linear-gradient(to top, theme(colors.foreground.primary) 30%, transparent)`,
      },

      borderColor: {
        primary: "hsl(var(--border-primary))",
        secondary: "hsl(var(--border-secondary))",
      },

      boxShadowColor: {
        primary: "hsl(var(--border-primary))",
        secondary: "hsl(var(--border-secondary))",
      },

      animation: {
        "spin-fast": "spin 0.75s linear infinite",
        pulse: "pulse 1.5s cubic-bezier(0.4, 0, 0.2, 1) infinite",
      },

      transitionTimingFunction: {
        standard: "cubic-bezier(0.4,0,0.2,1)",
      },
    },
  },
  plugins: [
    require("tailwindcss-animate"),
    require("tailwindcss-react-aria-components"),
    require("tailwind-scrollbar"),
  ],
};

export default config;
```

## Complete globals.css

```css
/* src/styles/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

/* ============================================
   CSS Variables - Light Theme (Default)
   ============================================ */
:root {
  /* Base colors (HSL values without hsl() wrapper) */
  --main: 0 0% 12.5%;
  --white: 0 0% 100%;

  /* Semantic colors */
  --accent: 207, 93%, 49%;
  --accent-secondary: 44, 31%, 68%;
  --success: 151, 55%, 42%;
  --error: 8, 73%, 54%;
  --warning: 33, 88%, 60%;

  /* Gray scale */
  --gray-50: 0 0% 96.5%;
  --gray-100: 0 0% 95.3%;
  --gray-200: 0 0% 91.4%;
  --gray-300: 0 0% 81.6%;
  --gray-400: 0 0% 73.3%;
  --gray-500: 0 0% 60.4%;
  --gray-600: 0 0% 42.4%;
  --gray-700: 0 0% 31%;
  --gray-800: 0 0% 21.2%;
  --gray-900: 0 0% 16.5%;
  --gray-1000: 0 0% 14.5%;

  /* Background */
  --bg-primary: var(--white);
  --bg-inverse: var(--main);

  /* Text */
  --text-primary: var(--main);
  --text-secondary: var(--gray-500);
  --text-tertiary: var(--gray-600);
  --text-inverse: var(--white);

  /* Border */
  --border-primary: var(--gray-200);
  --border-secondary: var(--gray-300);

  /* Foreground (surfaces) */
  --foreground-primary: var(--gray-100);
  --foreground-secondary: var(--gray-200);
  --foreground-tertiary: var(--gray-300);
  --foreground-accent: var(--accent);
  --foreground-accent-secondary: var(--accent-secondary);

  /* Icons */
  --icon-primary: var(--gray-500);
  --icon-accent-primary: var(--accent);
  --icon-inverse: var(--main);
}

/* ============================================
   CSS Variables - Dark Theme
   ============================================ */
.dark {
  --bg-primary: var(--main);
  --bg-inverse: var(--white);

  --text-primary: var(--white);
  --text-secondary: var(--gray-500);
  --text-tertiary: var(--gray-400);
  --text-inverse: var(--main);

  --border-primary: var(--gray-800);
  --border-secondary: var(--gray-700);

  --foreground-primary: var(--gray-1000);
  --foreground-secondary: var(--gray-900);
  --foreground-tertiary: var(--gray-800);

  --icon-primary: var(--gray-500);
  --icon-inverse: var(--white);
}

/* ============================================
   Base Layer
   ============================================ */
@layer base {
  body {
    @apply bg-primary text-primary;
  }
}

/* ============================================
   Components Layer
   ============================================ */
@layer components {
  /* Typography defaults */
  a,
  p {
    @apply text-lg;
  }

  h6 {
    @apply text-h6;
  }

  h5 {
    @apply text-h5;
  }

  h4 {
    @apply text-h4;
  }

  h3 {
    @apply text-h3;
  }

  h2 {
    @apply text-h2;
  }

  h1 {
    @apply text-h1;
  }

  /* Hide scrollbar utility */
  .no-scrollbar::-webkit-scrollbar {
    display: none;
  }

  .no-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }

  /* Container utilities */
  .container-base {
    @apply mx-auto flex w-full flex-1 flex-col items-center gap-12 px-5;
  }

  .container-base > * {
    @apply w-full;
  }

  .container-xl {
    @apply container-base max-w-[1400px];
  }

  .container-lg {
    @apply container-base max-w-[900px];
  }

  .container-sm {
    @apply container-base max-w-[560px];
  }

  .container-plans {
    @apply container-base px-0 sm:px-8;
  }
}
```

## PostCSS Config

```js
// postcss.config.js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

## TypeScript Path Aliases

Configure `tsconfig.json` to enable the `@/` import alias:

```json
// tsconfig.json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": [
    "next-env.d.ts",
    "**/*.ts",
    "**/*.tsx",
    ".next/types/**/*.ts"
  ],
  "exclude": ["node_modules"]
}
```

This enables imports like:
- `import { Button } from '@/components/ui/button'`
- `import { cn } from '@/lib/tw-utils'`
- `import { Providers } from '@/components/providers'`

**Important**: The `@/` alias maps to the `src/` directory. Ensure your project structure follows:

```
src/
├── app/           # Next.js App Router
├── components/
│   ├── ui/        # Registry components installed here
│   └── providers/ # Provider components
├── lib/
│   ├── fonts/     # KHTeka font files
│   └── tw-utils.ts
├── hooks/
└── styles/
    └── globals.css
```

## tw-utils.ts (Class Merging Utility)

```ts
// src/lib/tw-utils.ts
import { extendTailwindMerge } from "tailwind-merge";
import { createTV, type VariantProps } from "tailwind-variants";

// Extended tailwind-merge for custom design tokens
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [
        {
          text: ["sm", "md", "lg", "xl", "h6", "h5", "h4", "h3", "h2", "h1"],
        },
      ],
      "border-radius": [
        {
          rounded: [
            "1", "2", "3", "4", "5", "6", "7",
            "8", "9", "10", "11", "12", "13", "full",
          ],
        },
      ],
    },
  },
});

// Utility for merging class names
export function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(inputs.filter(Boolean).join(" "));
}

// Tailwind Variants with custom merge config
export const tv = createTV({
  twMerge: true,
  twMergeConfig: {
    extend: {
      classGroups: {
        "font-size": [
          {
            text: ["sm", "md", "lg", "xl", "h6", "h5", "h4", "h3", "h2", "h1"],
          },
        ],
        "border-radius": [
          {
            rounded: [
              "1", "2", "3", "4", "5", "6", "7",
              "8", "9", "10", "11", "12", "13", "full",
            ],
          },
        ],
      },
    },
  },
});

export type { VariantProps };
```

## Provider Stack

```tsx
// src/components/providers/index.tsx
'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from 'next-themes'
import { RouterProvider } from 'react-aria-components'
import { useRouter } from 'next/navigation'
import { Toaster } from '@/components/ui/toast'
import { useState } from 'react'

export function Providers({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const [queryClient] = useState(() => new QueryClient())

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
      >
        <RouterProvider navigate={router.push}>
          <Toaster />
          {children}
        </RouterProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
```

## Root Layout

```tsx
// src/app/layout.tsx
import type { Metadata } from 'next'
import localFont from 'next/font/local'
import { Providers } from '@/components/providers'
import '@/styles/globals.css'

// KHTeka font - WalletConnect design system font
const KHTeka = localFont({
  variable: "--font-KHTeka",
  src: [
    {
      path: "../lib/fonts/KHTeka-Light.otf",
      weight: "300",
      style: "normal",
    },
    {
      path: "../lib/fonts/KHTeka-Regular.otf",
      weight: "400",
      style: "normal",
    },
    {
      path: "../lib/fonts/KHTeka-Medium.otf",
      weight: "500",
      style: "normal",
    },
  ],
})

export const metadata: Metadata = {
  title: 'My App',
  description: 'Built with WalletConnect UI',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${KHTeka.variable} antialiased`} suppressHydrationWarning>
      <body>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}
```

## Theme Switching with next-themes

### ThemeProvider Configuration

The `ThemeProvider` from next-themes is configured in the provider stack with these key settings:

```tsx
<ThemeProvider
  attribute="class"         // Uses CSS class for theming (.dark class)
  defaultTheme="system"     // Respects system preference by default
  enableSystem              // Enables system theme detection
  disableTransitionOnChange // Prevents flash during theme switch
>
```

**Important**: The `suppressHydrationWarning` attribute on `<html>` is required to prevent React hydration warnings when the theme differs between server and client.

### Theme Selector Component

```tsx
// src/components/theme-selector.tsx
'use client'

import { CaretDown, Monitor, Moon, Sun } from '@phosphor-icons/react'
import { useTheme } from 'next-themes'

import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Menu, MenuItem, MenuPopover, MenuTrigger } from '@/components/ui/menu'

export function ThemeSelector() {
  const { theme, setTheme } = useTheme()

  return (
    <Card className="h-[4.875rem]">
      <span className="text-primary">Theme</span>

      <MenuTrigger>
        <Button variant="neutral-secondary" type="button" size="md">
          <span className="capitalize">{theme}</span>
          <CaretDown />
        </Button>

        <MenuPopover>
          <Menu>
            <MenuItem onAction={() => setTheme('system')}>
              <Monitor weight="duotone" className="size-4 text-icon-primary" /> System
            </MenuItem>

            <MenuItem onAction={() => setTheme('light')}>
              <Sun weight="fill" className="size-4 text-icon-primary" /> Light
            </MenuItem>

            <MenuItem onAction={() => setTheme('dark')}>
              <Moon weight="fill" className="size-4 text-icon-primary" /> Dark
            </MenuItem>
          </Menu>
        </MenuPopover>
      </MenuTrigger>
    </Card>
  )
}
```

### useTheme Hook API

```tsx
import { useTheme } from 'next-themes'

function MyComponent() {
  const {
    theme,         // Current theme: 'light' | 'dark' | 'system'
    setTheme,      // Function to set theme
    resolvedTheme, // Actual theme being used (resolves 'system')
    themes,        // List of available themes
  } = useTheme()

  // Check actual theme (useful when theme is 'system')
  const isDark = resolvedTheme === 'dark'

  return (
    <button onClick={() => setTheme(isDark ? 'light' : 'dark')}>
      Toggle Theme
    </button>
  )
}
```

### Avoiding Hydration Mismatch

When rendering theme-dependent UI, use the `mounted` pattern to avoid hydration mismatches:

```tsx
'use client'

import { useTheme } from 'next-themes'
import { useEffect, useState } from 'react'
import { Moon, Sun } from '@phosphor-icons/react'

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  // Only render after mounting to avoid hydration mismatch
  useEffect(() => setMounted(true), [])

  if (!mounted) {
    return <div className="size-9" /> // Placeholder with same dimensions
  }

  return (
    <button onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}>
      {resolvedTheme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
    </button>
  )
}
```

---

## Design Token Quick Reference

### Colors

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `bg-primary` | white | main (dark gray) | Page backgrounds |
| `bg-inverse` | main | white | Inverted backgrounds |
| `text-primary` | main | white | Primary text |
| `text-secondary` | gray-500 | gray-500 | Secondary text |
| `text-tertiary` | gray-600 | gray-400 | Tertiary text |
| `border-primary` | gray-200 | gray-800 | Primary borders |
| `foreground-primary` | gray-100 | gray-1000 | Card/surface backgrounds |

### Typography Scale

| Class | Size | Line Height | Use For |
|-------|------|-------------|---------|
| `text-sm` | 12px | 14px | Small labels, captions |
| `text-md` | 14px | 16px | Body text, buttons |
| `text-lg` | 16px | 18px | Default body, links |
| `text-h6` | 20px | 20px | Small headings |
| `text-h5` | 26px | 26px | Section headings |
| `text-h4` | 32px | 32px | Page headings |
| `text-h3` | 38px | 38px | Large headings |
| `text-h2` | 44px | 44px | Hero headings |
| `text-h1` | 50px | 50px | Display headings |

### Border Radius Scale

| Class | Value | Use For |
|-------|-------|---------|
| `rounded-1` | 4px | Tiny elements |
| `rounded-2` | 8px | Small buttons, inputs |
| `rounded-3` | 12px | Medium buttons |
| `rounded-4` | 16px | Cards, large buttons |
| `rounded-5` | 20px | Large cards |
| `rounded-6` | 24px | Modals |
| `rounded-full` | 9999px | Pills, avatars |

### Semantic Colors

| Token | HSL Value | Usage |
|-------|-----------|-------|
| `accent` | 207, 93%, 49% (blue) | Primary actions |
| `accent-secondary` | 44, 31%, 68% (yellow) | Secondary accents |
| `success` | 151, 55%, 42% (green) | Success states |
| `error` | 8, 73%, 54% (red) | Error states |
| `warning` | 33, 88%, 60% (orange) | Warning states |

## Component Registry Reference

**CRITICAL: Always use shadcn CLI to install components. NEVER manually write or copy component code.**

### Installation Methods

```bash
# Method 1: Direct URL (always works)
pnpm dlx shadcn@latest add https://dashboard.walletconnect.com/r/button.json

# Method 2: Registry alias (requires components.json config)
pnpm dlx shadcn@latest add @walletconnect/button

# Install multiple components at once
pnpm dlx shadcn@latest add @walletconnect/button @walletconnect/input @walletconnect/card
```

### Form Components

| Component | Direct URL | Key Props |
|-----------|------------|-----------|
| button | `https://dashboard.walletconnect.com/r/button.json` | variant, size, isLoading, leftIcon, rightIcon |
| input | `https://dashboard.walletconnect.com/r/input.json` | variant, size, leftIcon, rightIcon, isCopyable |
| checkbox | `https://dashboard.walletconnect.com/r/checkbox.json` | isSelected, isIndeterminate |
| radio | `https://dashboard.walletconnect.com/r/radio.json` | value, isDisabled |
| select | `https://dashboard.walletconnect.com/r/select.json` | selectedKey, items |
| switch | `https://dashboard.walletconnect.com/r/switch.json` | isSelected |
| slider | `https://dashboard.walletconnect.com/r/slider.json` | value, minValue, maxValue |
| text-area | `https://dashboard.walletconnect.com/r/text-area.json` | rows |
| tag-group | `https://dashboard.walletconnect.com/r/tag-group.json` | selectionMode |

### Button Variants

```tsx
// Available variants
<Button variant="accent">Primary Action</Button>
<Button variant="neutral">Neutral</Button>
<Button variant="neutral-secondary">Outlined</Button>
<Button variant="neutral-tertiary">Subtle</Button>
<Button variant="error">Destructive</Button>
<Button variant="link">Link Style</Button>
<Button variant="icon">Icon Only</Button>

// Available sizes
<Button size="sm">Small</Button>  // h-7
<Button size="md">Medium</Button> // h-9.5 (default)
<Button size="lg">Large</Button>  // h-12
```

### Icons Usage

```tsx
// Phosphor Icons (recommended)
import { House, Gear, User, CaretRight } from '@phosphor-icons/react'

<House size={24} weight="bold" />
<Gear size={20} weight="regular" />

// Custom WC icons (from registry)
import { WalletConnectLogo, WalletIcon } from '@/icons'

<WalletConnectLogo className="h-8 w-auto" />
```
