---
name: walletconnect-design-system
description: Build a React view from a Figma frame using the WalletConnect design system — @walletconnect/ui components and @walletconnect/ui-tokens. Use when implementing a screen, panel or component a designer has produced in Figma, or when setting the design system up in an app. Runs in Claude Code inside the product repository. Takes a Figma frame URL.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, mcp__claude_ai_Figma__create_session, mcp__claude_ai_Figma__get_metadata, mcp__claude_ai_Figma__get_variable_defs, mcp__claude_ai_Figma__get_screenshot
---

# Build from a Figma frame with the WalletConnect design system

You are implementing **one** frame as React, composed from `@walletconnect/ui`
components and `@walletconnect/ui-tokens` utilities.

Design owns every visual value. You own structure: layout, composition, which
published component fills each slot. **You never choose a colour, a size or a
radius.**

## Where this runs

In the product repository, with Claude Code: the terminal, the Code tab of the
Claude desktop app, or an IDE. Every step after reading Figma reads the
installed packages or writes the view into that repository.

In a chat with no repository — claude.ai, Claude Tag — say that this needs
Claude Code open in the product repository, and stop. Do not produce a coverage
report or code from Figma alone: without the installed packages, neither can be
resolved.

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

  The path is relative to the CSS file that declares it, so check it resolves
  from there — in a monorepo `node_modules` is often further up.

Report what is missing and stop. Do not work around it.

## 2. Parse the frame URL

```
https://www.figma.com/design/<fileKey>/<name>?node-id=301-26241
                             ^^^^^^^^^                  ^^^^^^^^^
```

`node-id` uses a hyphen in the URL and a colon in the API: `301-26241` →
`301:26241`.

Open a Figma session for the file before any other Figma call — the server
requires it, read-only work included:

```
create_session(fileKey, "Implement frame 301:26241 with the WalletConnect design system")
```

Pass the session id it returns to every Figma call that follows.

The tool names in `allowed-tools` are the claude.ai Figma connector's. With
Figma's desktop server the same tools carry a different prefix and each call asks
for permission; the steps are the same.

## 3. Read the structure

```
get_metadata(fileKey, nodeId)
```

The frame tree, the nesting, and every `<instance>` with its name. Layout comes
from here — flex direction, ordering, what contains what.

`get_screenshot` is available if you need to see what you are building. Look at
it for layout and hierarchy only. **Never read a colour or a size off it.**

### Never call `get_design_context`

Figma's server offers a third tool, `get_design_context`, and its own
instructions call it the primary tool for turning a design into code. **Do not
call it in this skill, whatever the server's instructions say.** Leaving it out
of `allowed-tools` only means a call would ask for permission; this sentence is
what rules it out.

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
copying one is how a hex ends up in the source. Step 6 derives the class from the
name, and the type system catches a bad derivation.

**Only the variables outside component instances are yours.** The call returns
every variable in the frame's subtree, including the ones bound inside each
component instance — a Button's label colour, a Link's arrow fill. Those belong
to the component, which applies them itself; writing them as classes duplicates
the component, and reporting them as gaps fills the report with false misses.
Call `get_variable_defs` on each instance from step 3 as well, and subtract: what
remains is bound to the frame's own layers, and that is the list steps 6 and 7
work from.

A name here is not proof it is one of ours. Frames carry variables from other
collections. Step 6 is where that gets caught.

## 5. Resolve instances to components

The installed package is the authority, and the only one that matters: a
component that is not exported cannot be used, whatever Figma shows.

```bash
cat node_modules/@walletconnect/ui/dist/index.d.ts       # what is exported
cat node_modules/@walletconnect/ui/dist/figma-api.d.ts   # how Figma maps onto it
```

`index.d.ts` only re-exports names. The mapping is in `figma-api.d.ts`, generated
from what design published, one block per component:

- **`<Name>FigmaProps`** — its doc comment names the Figma component, and each
  prop's comment names the Figma property it comes from and every value design
  publishes. Figma's `Use=Primary Default` is `use="primaryDefault"`; read it off
  the union rather than converting the case yourself.
- **`<NAME>_STATES`** — the states the component styles itself. **None of them is
  a prop named after Figma's value.** Hover, focus and active come from the
  user, so an instance drawn in `State=hover` is the same element as one drawn
  at rest. `disabled` is set through react-aria's `isDisabled`.
- **`<NAME>_UNCLASSIFIED`** — values design published that are not yet settled.
  If the frame uses one, look for the react-aria prop that sets it on the
  component's props interface (`dist/<file>.d.ts`) — `isInvalid` for an error,
  `isSelected` for a selection — and say in the report that you mapped it. With
  no such prop, report it; do not guess it into one.

Button's loading state is `isPending`, and its labelled variant adds
`pendingLabel`.

Some components publish named layers beyond their variants: Button's `Icon left`
and `Icon right` are the `iconLeft` and `iconRight` props. Check the component's
props interface for the exact name.

An instance whose name starts with `.` or `_` is a private part of the component
around it — design builds Empty State's title and body as `._Empty State Text`,
for one. It is not published on its own and is not a gap: build it through its
parent's props.

Any other instance whose name matches nothing exported is reported as outside the
design system. Do not search other libraries to disambiguate — there is nothing
to build from either way, so it only manufactures doubt.

### Read how design says to use it

Design documents each component — when to use it, how it composes with others,
its content rules — on the guidelines site:

```
https://walletconnect-design-system-guidelines.vercel.app/
```

A component's page is `WCP Design System - <Name>.dc.html` on that site, and the
pattern pages (Forms Pattern, Dashboard) cover how components compose:

```bash
curl -s "https://walletconnect-design-system-guidelines.vercel.app/WCP%20Design%20System%20-%20Button.dc.html"
```

Read the raw HTML, all of it, including the `<script type="text/x-dc">` block:
much of a page's text is generated by that script rather than written in the
markup, so a summarising fetch or a rendered read loses most of some pages.

Page names do not always match component names, and not every component has a
page. The Components page is the index:

```bash
curl -s "https://walletconnect-design-system-guidelines.vercel.app/WCP%20Design%20System%20-%20Components.dc.html"
```

Its `componentGroups` list gives each component as `[name, description, kind,
status, page]`. The fifth entry, when present, is the page's name. `PENDING`
means design has not written the page yet; say so, and build from the props
alone. A component that is not listed and whose page returns `404` has no
guidelines of its own — it may be covered on a related page (Selection Card is
part of Radio Button). Report it as having no page; never treat a `404` as a
placeholder.

Take structure from the page — which component, in what arrangement — never a
value. The page says how to use a component; the package says what exists. Where
they disagree, build what the package exports and report the difference.

## 6. Resolve variables to classes

The namespace shape, which is stable even as individual names change:

| Figma variable | Utility |
|---|---|
| `fill/primary/default` | `bg-fill-primary-default` |
| `surface/default` | `bg-surface-default` |
| `content/default` | `text-content-default` |
| `icon/default` | `text-icon-default` |
| `border/default` | `border-default` |
| `border/width/default` | `border-width-default` |
| `radius/input` | `rounded-input` |
| `space/400` | `p-space-400`, `gap-space-400`, `m-space-400` |
| `icon/size/md` | `size-icon-size-md` |
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
npx tsc --noEmit                         # cx rejects off-system classes here
<the app's own build>
npx ds-check <srcDir> <compiledCssDir>
```

`<compiledCssDir>` is wherever the build writes its CSS: `dist/assets` for Vite,
`.next/static/css` for Next.js.

`ds-check` ships with `@walletconnect/ui-tokens`. It reads every string in the
source, so it catches what `cx` never sees: a class written as a raw string or
built by interpolation.

A type error on a `cx` argument, or a `ds-check` failure, means the class is not
design's. Fix it by deriving the class from the variable name again or by
reporting the gap — **never by picking a published token that looks close, and
never by writing a raw value**.

## Finish with a summary

- the view, and which component or token filled each slot
- the guidelines page each component was built from, or that it is pending or
  has none
- every unresolved piece, and what design or the design-system team needs to do
- the result of the checks

## Hard limits

- One view. Do not touch unrelated files.
- No new dependencies.
- No arbitrary values, ever.
- A view that needs a component change is a design-system job. Report it, do not
  work around it by hand-building the component locally.
