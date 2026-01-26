# WalletConnect Layout Patterns

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

## Auth Layout

Centered layout for sign-in/sign-up pages:

```tsx
// src/app/(auth)/layout.tsx
import { Logo } from '@/components/logo'

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen flex-col gap-3 py-6 px-1.5">
      <header className="flex justify-center">
        <Logo />
      </header>
      <main className="flex flex-1 items-center justify-center">
        {children}
      </main>
      <footer className="text-center text-sm text-gray-500">
        &copy; {new Date().getFullYear()} Your Company
      </footer>
    </div>
  )
}
```

### Auth Page Template

```tsx
// src/app/(auth)/sign-in/page.tsx
import { SignInForm } from './_components/sign-in-form'

export default function SignInPage() {
  return (
    <div className="w-full max-w-[28rem] px-5">
      <div className="flex flex-col gap-6 text-center">
        <div>
          <h4>Welcome back</h4>
          <p className="text-gray-500">Sign in to your account</p>
        </div>
        <SignInForm />
      </div>
    </div>
  )
}
```

## Dashboard Layout

Multi-level nested layout with navbar and navigation:

```tsx
// src/app/(dashboard)/layout.tsx
import { Suspense } from 'react'
import { Navbar, NavbarSkeleton } from './_components/navbar'
import { Footer } from './_components/footer'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen flex-col py-6">
      <Suspense fallback={<NavbarSkeleton />}>
        <Navbar />
      </Suspense>
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  )
}
```

### Navbar Component

```tsx
// src/app/(dashboard)/_components/navbar.tsx
import { Logo } from '@/components/logo'
import { Button } from '@/components/ui/button'
import { Link } from '@/components/ui/link'
import { Skeleton } from '@/components/ui/skeleton'

export function Navbar() {
  return (
    <header className="container-base container-xl">
      <nav className="flex w-full items-center justify-between">
        <div className="flex items-center gap-4">
          <Logo />
          {/* Add project/team selectors here */}
        </div>
        <div className="flex items-center gap-2">
          <Link href="/settings" variant="ghost">Settings</Link>
          <Button variant="secondary">Help</Button>
        </div>
      </nav>
    </header>
  )
}

export function NavbarSkeleton() {
  return (
    <header className="container-base container-xl">
      <nav className="flex w-full items-center justify-between">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-8 w-24" />
      </nav>
    </header>
  )
}
```

### Navigation Tabs

```tsx
// src/app/(dashboard)/[projectId]/_components/navigation.tsx
'use client'

import { Link } from '@/components/ui/link'
import { useSelectedLayoutSegment } from 'next/navigation'
import { cn } from '@/lib/tw-utils'
import { Skeleton } from '@/components/ui/skeleton'

interface Route {
  label: string
  href: string
  segment: string | null
}

interface NavigationProps {
  routes: Route[]
  baseUrl: string
}

export function Navigation({ routes, baseUrl }: NavigationProps) {
  const segment = useSelectedLayoutSegment()

  return (
    <nav className="sticky top-0 z-50 bg-background py-5">
      <div className="container-base container-xl">
        <div className="flex max-w-fit gap-2 overflow-x-auto no-scrollbar">
          {routes.map((route) => {
            const isActive = segment === route.segment
            return (
              <Link
                key={route.href}
                href={`${baseUrl}${route.href}`}
                variant="ghost"
                className={cn(
                  'whitespace-nowrap',
                  isActive && 'bg-gray-100 dark:bg-gray-800'
                )}
                aria-current={isActive ? 'page' : undefined}
              >
                {route.label}
              </Link>
            )
          })}
        </div>
      </div>
    </nav>
  )
}

export function NavigationSkeleton() {
  return (
    <nav className="sticky top-0 z-50 bg-background py-5">
      <div className="container-base container-xl">
        <div className="flex gap-2">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-9 w-24" />
          ))}
        </div>
      </div>
    </nav>
  )
}
```

### Project Layout with Navigation

```tsx
// src/app/(dashboard)/[projectId]/layout.tsx
import { Suspense } from 'react'
import { Navigation, NavigationSkeleton } from './_components/navigation'

const routes = [
  { label: 'Overview', href: '', segment: null },
  { label: 'Analytics', href: '/analytics', segment: 'analytics' },
  { label: 'Settings', href: '/settings', segment: 'settings' },
]

export default function ProjectLayout({
  children,
  params,
}: {
  children: React.ReactNode
  params: { projectId: string }
}) {
  const baseUrl = `/${params.projectId}`

  return (
    <>
      <Suspense fallback={<NavigationSkeleton />}>
        <Navigation routes={routes} baseUrl={baseUrl} />
      </Suspense>
      {children}
    </>
  )
}
```

## Pages Layout

Simple layout for static/content pages:

```tsx
// src/app/(pages)/layout.tsx
import { Header } from './_components/header'

export default function PagesLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen flex-col gap-1.5 py-6">
      <Header />
      <main className="flex-1">{children}</main>
    </div>
  )
}
```

## Page Content Pattern

Standard page structure with Suspense:

```tsx
// src/app/(dashboard)/[projectId]/analytics/page.tsx
import { Suspense } from 'react'
import { AnalyticsContent, AnalyticsSkeleton } from './_components/analytics'

export default function AnalyticsPage() {
  return (
    <div className="container-base container-lg">
      <Suspense fallback={<AnalyticsSkeleton />}>
        <AnalyticsContent />
      </Suspense>
    </div>
  )
}
```

### Content Component with Async Data

```tsx
// src/app/(dashboard)/[projectId]/analytics/_components/analytics.tsx
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

async function getAnalyticsData() {
  // Fetch data
  return { views: 1000, users: 500 }
}

export async function AnalyticsContent() {
  const data = await getAnalyticsData()

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h4>Analytics</h4>
        <p className="text-gray-500">View your project metrics</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <Card.Header>
            <Card.Title>Page Views</Card.Title>
          </Card.Header>
          <Card.Content>
            <p className="text-h2">{data.views.toLocaleString()}</p>
          </Card.Content>
        </Card>
        <Card>
          <Card.Header>
            <Card.Title>Users</Card.Title>
          </Card.Header>
          <Card.Content>
            <p className="text-h2">{data.users.toLocaleString()}</p>
          </Card.Content>
        </Card>
      </div>
    </div>
  )
}

export function AnalyticsSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <Skeleton className="h-8 w-32" />
        <Skeleton className="mt-2 h-5 w-48" />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {[1, 2].map((i) => (
          <Card key={i}>
            <Card.Header>
              <Skeleton className="h-5 w-24" />
            </Card.Header>
            <Card.Content>
              <Skeleton className="h-10 w-20" />
            </Card.Content>
          </Card>
        ))}
      </div>
    </div>
  )
}
```

## Mobile Navigation with Sheet

```tsx
// src/app/(dashboard)/_components/mobile-nav.tsx
'use client'

import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Link } from '@/components/ui/link'
import { List } from '@phosphor-icons/react'

const routes = [
  { label: 'Dashboard', href: '/dashboard' },
  { label: 'Projects', href: '/projects' },
  { label: 'Settings', href: '/settings' },
]

export function MobileNav() {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="xl:hidden">
          <List size={24} />
          <span className="sr-only">Toggle menu</span>
        </Button>
      </SheetTrigger>
      <SheetContent side="left">
        <nav className="flex flex-col gap-2 pt-8">
          {routes.map((route) => (
            <Link
              key={route.href}
              href={route.href}
              variant="ghost"
              className="justify-start"
            >
              {route.label}
            </Link>
          ))}
        </nav>
      </SheetContent>
    </Sheet>
  )
}
```

## Folder Structure Convention

```
src/
├── app/
│   ├── (auth)/
│   │   ├── layout.tsx
│   │   ├── sign-in/
│   │   │   ├── page.tsx
│   │   │   └── _components/
│   │   │       └── sign-in-form.tsx
│   │   └── sign-up/
│   │       └── page.tsx
│   ├── (dashboard)/
│   │   ├── layout.tsx
│   │   ├── _components/
│   │   │   ├── navbar.tsx
│   │   │   ├── footer.tsx
│   │   │   └── mobile-nav.tsx
│   │   └── [projectId]/
│   │       ├── layout.tsx
│   │       ├── page.tsx
│   │       ├── _components/
│   │       │   └── navigation.tsx
│   │       └── settings/
│   │           └── page.tsx
│   ├── (pages)/
│   │   ├── layout.tsx
│   │   └── about/
│   │       └── page.tsx
│   └── layout.tsx
├── components/
│   ├── providers/
│   │   └── index.tsx
│   ├── ui/
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   └── ...
│   └── logo.tsx
├── lib/
│   └── tw-utils.ts
├── hooks/
│   └── use-prefetch.ts
└── styles/
    └── globals.css
```
