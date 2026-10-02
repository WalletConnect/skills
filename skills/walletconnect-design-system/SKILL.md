---
name: walletconnect-design-system
description: Build a React view from a Figma frame using the WalletConnect design system — @walletconnect/ui components and @walletconnect/ui-tokens. Use when implementing a screen, panel or component a designer has produced in Figma, or when setting the design system up in an app. Takes a Figma frame URL.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, mcp__claude_ai_Figma__get_metadata, mcp__claude_ai_Figma__get_variable_defs, mcp__claude_ai_Figma__get_screenshot
---

# Build from a Figma frame with the WalletConnect design system

You are implementing **one** frame as React, composed from `@walletconnect/ui`
components and `@walletconnect/ui-tokens` utilities.

Design owns every visual value. You own structure: layout, composition, which
published component fills each slot. **You never choose a colour, a size or a
radius.**

## This skill holds rules, not inventory

Which components exist, which tokens exist, which props each takes — none of that
is written here. All of it is read from the installed packages at the moment you
need it. A list in this file would be wrong the day design publishes something,
and nobody would notice until you told a developer a component does not exist.

## The report is the deliverable

The component set is small and deliberately follows what design has published.
On a real frame, **most rows in your coverage report will not resolve**, and that
is the useful output, not a failure. It tells the developer what the design
system covers, and it tells the design-system team what product work actually
needs — which is the one signal their roadmap does not otherwise get.

Say so when you hand it over. Do not apologise for it.

## 1. Check the install before anything else

Both failure modes here are silent, and an agent that skips this debugs the wrong
thing for an hour.

```bash
cat node_modules/@walletconnect/ui/package.json | grep '"version"'
cat node_modules/@walletconnect/ui-tokens/package.json | grep '"version"'
```

- **Both packages present, at the same version.** They are versioned as a pair.
- **If install fails with a bare `401`**, the `@walletconnect` scope is not
  pointed at GitHub Packages. See `references/setup.md`.
- **If the app runs Tailwind**, its CSS entry must declare the components as a
  source. Tailwind v4 does not scan `node_modules`, so without this every DS
  component renders **unstyled, with no error anywhere**:

  ```css
  @source "../node_modules/@walletconnect/ui/dist";
  ```

Report what is missing and stop. Do not work around it.

## 2. Parse the frame URL

```
https://www.figma.com/design/<fileKey>/<name>?node-id=301-26241
                             ^^^^^^^^^                  ^^^^^^^^^
```

`node-id` uses a hyphen in the URL and a colon in the API: `301-26241` →
`301:26241`.

## 3. Read the structure

```
get_metadata(fileKey, nodeId)
```

The frame tree, the nesting, and every `<instance>` with its name. Layout comes
from here — flex direction, ordering, what contains what.

`get_screenshot` is available if you need to see what you are building. Look at
it for layout and hierarchy only. **Never read a colour or a size off it.**

### Why `get_design_context` is not in `allowed-tools`

Figma's MCP server offers a third tool alongside the two above,
`get_design_context`, which looks purpose-built for this job: hand it a frame and
it returns ready-to-paste React and CSS. It is deliberately left out.

Asked to implement a frame, what it returns looks like this:

```
font-['Inter:Light']  text-[#2b2b2b]  text-[46px]  leading-[normal]
```

Every value hardcoded, every one an arbitrary value, and no indication which
library anything came from. It also instructs you to "preserve exact visual
design" — which, with no token to resolve against, means inventing one. That is
the drift this design system exists to prevent, arriving through the front door.

So the frame is read a different way: **structure from metadata, styling from
variable names.** Never from rendered values.

## 4. Read the styling as names

```
get_variable_defs(fileKey, nodeId)
```

Returns the variables bound on the frame **as names**:

```json
{ "fill/primary/default": "#0666ff", "radius/input": "8px" }
```

**Use the keys. Ignore the values entirely** — they are the resolved output, and
copying one is how a hex ends up in the source.

You get a name and a resolved value, and nothing else. Figma can carry a per
platform **Code Syntax** on a variable — the actual Tailwind class, written back
into the design file — which would be better than deriving one, because it comes
from the same export that produced the CSS. It is not reachable: the REST
endpoint that exposes it is Enterprise-only and refuses on this organisation's
plan, and `get_variable_defs` does not return it. So step 6 derives the class
from the name, and the type system catches a bad derivation.

A name here is not proof it is one of ours. Frames carry variables from other
collections. Step 6 is where that gets caught.

## 5. Resolve instances to components

The installed package is the authority, and the only one that matters: a
component that is not exported cannot be used, whatever Figma shows.

```bash
cat node_modules/@walletconnect/ui/dist/index.d.ts
```

Design's variant values map to props by case — Figma's `Use=Primary Default`
becomes `use="primaryDefault"`. **Confirm each against the prop type's union
rather than guessing it**; the union is the list of what design has published.

An instance whose name matches nothing exported is reported as outside the design
system. Do not search other libraries to disambiguate — there is nothing to build
from either way, so it only manufactures doubt.

## 6. Resolve variables to classes

The namespace shape, which is stable even as individual names change:

| Figma variable | Utility |
|---|---|
| `fill/primary/default` | `bg-fill-primary-default` |
| `surface/raised` | `bg-surface-raised` |
| `content/default` | `text-content-default` |
| `icon/default` | `text-icon-default` |
| `border/default` | `border-default` |
| `border/width/default` | `border-width-default` |
| `radius/input` | `rounded-input` |
| `space/400` | `p-space-400`, `gap-space-400`, `m-space-400` |
| `icon-size/md` | `size-icon-size-md` |
| text style `typography/component/button-lg` | `typography-component-button-lg` |

**`border/*` is a colour and `border/width/*` is a width.** They share one
Tailwind prefix and are different namespaces — the trap that catches everyone.

**Take a type style as one class.** `typography-component-button-lg`, never
`text-350 leading-200 font-semibold`: design authored family, size, weight,
line-height and tracking together, and splitting them drops the typeface.

**A name that does not resolve stays unresolved.** Not the nearest colour, not
the closest spacing step. A plausible substitution passes every check while
silently changing the design, which makes it worse than a gap — the gap is
visible and the substitution is not.

You do not need to enumerate the vocabulary to check a name. Write the class
through `cx` and let TypeScript refuse it; that is what the type is for.

## 7. Report coverage, then stop

```
Frame: Checkout panel (301:26241)

  instance  Button              → DsButton                       ✓
  variable  surface/raised      → bg-surface-raised              ✓
  variable  radius/container    → rounded-container              ✓
  variable  Live/Primary        → no design-system token         ✗
  instance  Input               → not published in the DS        ✗

  3 of 4 variables resolved · 1 of 2 instances resolved
```

Hand the unresolved rows over as a list worth filing with the design-system team.
That is what tells them what to build next.

## 8. Write it

Every `className` goes through `cx`, so an off-system class is a compile error
in the editor rather than a silent miss:

```tsx
import { cx } from '@walletconnect/ui-tokens/cx';

<div className={cx('flex', 'items-center', 'p-space-400', 'bg-surface-raised')} />
```

- **Layout utilities are fine** — `flex`, `items-center`, `grid-cols-3`. Nobody
  tokenises layout.
- **Tailwind's scales are not.** `p-4`, `text-sm`, `bg-slate-700` and `p-[13px]`
  all compile and are all rejected by name.
- **For an unresolved slot, leave the element out** with a comment naming the
  missing token or component. Never a placeholder value.
- **Themes are a runtime class**, not a build variant: `<div class="theme-dark">`
  re-points the semantic variables for that subtree, and nests.

## 9. Prove it

```bash
npx tsc --noEmit     # cx rejects off-system classes here
<the app's own build>
```

A type error on a `cx` argument means the class is not design's. Fix it by
reading the code syntax again or by reporting the gap — **never by picking a
published token that looks close, and never by writing a raw value**.

## Finish with a summary

- the view, and which component or token filled each slot
- every unresolved piece, and what design or the design-system team needs to do
- the result of the checks

## Hard limits

- One view. Do not touch unrelated files.
- No new dependencies.
- No arbitrary values, ever.
- A view that needs a component change is a design-system job. Report it, do not
  work around it by hand-building the component locally.
