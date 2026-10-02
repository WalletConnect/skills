# Installing the WalletConnect design system

Both packages are on **GitHub Packages**, not npmjs, and they are versioned as a
pair — always install them at the same version.

## 1. Point the scope at GitHub Packages

In the project's `.npmrc`:

```
@walletconnect:registry=https://npm.pkg.github.com
//npm.pkg.github.com/:_authToken=${GITHUB_TOKEN}
```

`GITHUB_TOKEN` is a personal access token with `read:packages`, **per developer
and per CI runner**. Without it, install fails with a bare `401` that never
mentions authentication — which is why this is the first thing to check.

```bash
pnpm add @walletconnect/ui @walletconnect/ui-tokens
```

## 2. Choose a stylesheet

Three ways, depending on what the app is.

### The app runs Tailwind v4 and writes its own layout

The common case.

```css
@import "tailwindcss";
@import "@walletconnect/ui-tokens/tokens.css";
@import "@walletconnect/ui-tokens/variants.css";
@source "../node_modules/@walletconnect/ui/dist";
```

**The last line is not optional.** Tailwind v4 does not scan `node_modules`, so
without it the components' own classes are never generated and every DS component
renders unstyled — with no error anywhere. It is the single most common setup
failure and the hardest to diagnose, because nothing is broken except the output.

### Components only, no layout of your own

```css
@import "@walletconnect/ui/styles.css";
```

Carries the utilities *those components* use and the typography classes — not the
full vocabulary. Most of what a real screen writes is absent, `flex-wrap` among
them.

### No Tailwind, no build step

```css
@import "@walletconnect/ui-tokens/sheet.css";
```

Every utility design's vocabulary can produce, precompiled. Around 862 KB raw,
42 KB brotli for the base sheet. Interactive states are absent deliberately —
they belong to the components, which are precompiled and own them.

## 3. Peer dependencies

`react` and `react-dom` 18+, `@walletconnect/ui-tokens` at the matching version,
and `@phosphor-icons/react` for any component that renders a glyph.

## Theming

Themes are a **runtime** switch, not a build variant. A theme class re-points the
semantic variables for its subtree, and nests:

```html
<div class="theme-dark">
  <div class="bg-surface-raised">dark</div>
</div>
```

One class per Figma mode beyond the base, named after the mode with `-mode`
stripped: `Dark Mode` becomes `.theme-dark`.

A theme block overrides **semantics**. Overriding a primitive instead silently
does nothing — custom properties are computed where they are declared and
inherited as computed values, so a semantic declared at `:root` never sees the
change.
