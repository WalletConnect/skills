---
name: walletconnect-pay-headless
description: Guides developers building a fully branded, self-hosted crypto checkout on the WalletConnect Pay Headless SDK (the @walletconnect/pay-* packages). Use when implementing a headless payment flow in React/Next.js or vanilla JavaScript, wiring the server proxy that keeps the Engine API key server-side, setting up wallet connection through AppKit, rendering the payment state machine, or troubleshooting the pay-core / pay-state / pay-react / pay-appkit packages.
---

# WalletConnect Pay — Headless SDK Integration

## What this is

**WalletConnect Pay** lets an app accept stablecoin payments from any WalletConnect-compatible wallet. The **Headless SDK** is the set of framework-agnostic npm packages (`@walletconnect/pay-*`) that run the payment flow — loading the payment, connecting a wallet, quoting, signing, and settling — **without imposing any UI**. You render the screens; the SDK runs the machine.

It is the same runtime that powers WalletConnect's own hosted checkout ("Buyer Experience"), extracted so you can build a fully branded checkout on the same engine.

> **This skill teaches the SDK contract, not a prescribed app structure.** The code here shows how to call the SDK correctly. How you route requests, lay out files, and structure your UI is yours — treat the example scaffolding as *one* illustration, not a required shape. For a complete, opinionated build, see the [reference example](https://github.com/WalletConnect/walletconnect-pay-examples/tree/main/gateway/headless-checkout) and the [official docs](https://docs.walletconnect.com/payments/psps/headless-sdk/overview).

## When to use

- Building a self-hosted, branded stablecoin checkout inside your own product and domain
- Embedding pay-with-crypto into an existing checkout flow instead of redirecting to a WalletConnect-hosted page
- Wiring the server proxy that keeps the Engine API key off the browser
- Rendering the payment lifecycle (load → connect → quote → sign → confirm → settle) from a snapshot
- Troubleshooting the four SDK packages (see [The four packages](#the-four-packages) below)

**Not this skill:** if you only want to *create* a payment request (a link/QR) or poll its status as a merchant, or you're adding WC Pay *acceptance* to a wallet app, this is the wrong integration — those are separate products. If you just want the fastest path with no UI to build, use WalletConnect's [hosted gateway](https://docs.walletconnect.com/payments/overview) instead.

## The mental model: headless runtime + host

The payment flow lives entirely in the SDK. Your app is the **host** that consumes it. The runtime only touches the outside world through five injectable **seams** — swappable adapters — so you can supply your own transport, wallet, timing, and analytics and reuse the exact same payment machine.

| Seam | Abstracts | You provide it with |
| --- | --- | --- |
| `Transport` | Engine HTTP calls | `createHttpTransport({ baseUrl })` from pay-core → your server proxy |
| `WalletProvider` | connect / accounts / provider / switch | `pay-appkit` (ready-made), or your own wallet integration |
| `Signer` | signs a payment option's wallet-RPC actions | `pay-appkit`'s `createAppKitSigner(wallet)`, or `createSigner(wallet, …)` from pay-state |
| `Clock` | intervals + page visibility (status polling) | `browserClock` from pay-state (default) |
| `Telemetry` | analytics breadcrumbs (optional) | your pipeline, or `noopTelemetry` |

In practice you wire only the first three; `browserClock` and `noopTelemetry` are the shipped defaults.

**AppKit** = [Reown AppKit](https://reown.com/appkit), the wallet-connection library. `@walletconnect/pay-appkit` wraps it so you get EVM + Solana wallet connection, a wallet picker, and a signer without touching `@reown/*`, `wagmi`, or `viem` yourself. If you already have your own wallet connector, you can skip AppKit and implement the `WalletProvider` seam directly ([custom-wallet.md](references/custom-wallet.md)).

## The four packages

Layered; lower packages never import higher ones, so you take only what you need. Full API surface and current signatures live in the [packages reference](https://docs.walletconnect.com/payments/psps/headless-sdk/packages-reference) — treat that public page as the source of truth (this is a beta API, v0.1.x, and signatures can change between minor releases).

| Package | Role |
| --- | --- |
| `@walletconnect/pay-core` | Engine API client — contract types, the browser `Transport` seam (`createHttpTransport`), and the server-only `createEngineClient` (`/server` subpath) that holds your API key. |
| `@walletconnect/pay-state` | The headless runtime — the payment state machine, seam contracts, `createPaymentController`, and the public `PaymentSnapshot`. No React, no HTTP, no wallet SDK. |
| `@walletconnect/pay-react` | Thin React binding — `usePaymentSession` returns the snapshot + named actions. |
| `@walletconnect/pay-appkit` | The Reown AppKit adapter — the `WalletProvider` seam, a zero-config `Signer`, and a wallet picker. `/react` subpath ships the provider + hooks. |

## Choose your path

| Path | When | Reference |
| --- | --- | --- |
| **React / Next.js** | You use React → `usePaymentSession` + `<PayAppKitProvider>` | [react-nextjs.md](references/react-nextjs.md) |
| **Vanilla JavaScript** | Framework-neutral → `createPaymentController` + subscribe + render | [vanilla-js.md](references/vanilla-js.md) |
| **Custom wallet** | Not using AppKit → implement `WalletProvider`, build the signer with `createSigner` | [custom-wallet.md](references/custom-wallet.md) |

Every path needs the server proxy → [server-proxy.md](references/server-proxy.md).

## Prerequisites

1. **Node 18+**.
2. A **Reown Project ID** — from [dashboard.reown.com](https://dashboard.reown.com), with the **headless** feature enabled. Used for wallet connection / QR pairing. Public (client-side).
3. A **WalletConnect Pay Gateway API key** — server-side only. [Talk to WalletConnect](https://share.hsforms.com/1XsMCkUxFT2Cte8SCeAh89wnxw6s) to get onboarded.

## Install

```bash
npm install @walletconnect/pay-core @walletconnect/pay-state \
            @walletconnect/pay-appkit @walletconnect/pay-react
```

Wallet connectivity (`@reown/appkit`, `wagmi`, `viem`, `@solana/web3.js`) comes transitively through `@walletconnect/pay-appkit` — you don't add it directly. Omit `@walletconnect/pay-react` if you're not using React.

## The payment lifecycle

Whatever UI you build, the runtime moves a payment through the same stages. You render each stage and call the matching action:

```
Load payment → Connect wallet → Fetch options → Select & build → Sign → Confirm & settle
```

The SDK drives all transitions. You never advance it manually — you read `snapshot.state` and call one of the named actions in response to user input.

## The snapshot is the whole UI contract

`snapshot.state` is one of **17** values (the exact `PaymentState` union from `@walletconnect/pay-state`). Render per state, call the matching action:

| `snapshot.state` | Meaning | Typical action |
| --- | --- | --- |
| `Initializing` | Loading the payment intent | — (spinner) |
| `ReadyForWallet` | Waiting for wallet connection | `connectWallet(item, namespace?)` |
| `ConnectingWallet` | Connection in progress | — (spinner / QR) |
| `LoadingOptions` | Fetching payable options | — (spinner) |
| `OptionsReady` | Options available | `selectOption(option, rank)` |
| `NoOptions` | No payable options for this wallet | let the user switch wallet |
| `InformationCapture` | Engine requires KYC/contact data | `submitInfoCapture(data)` |
| `OptionSelected` | Option chosen, ready to confirm | `confirmSelection()` |
| `RequiresApproval` | Needs a separate approval (e.g. Permit2) | `confirmSelection()` (label "Approve & pay") |
| `AwaitingWalletApproval` | Waiting on the wallet signature | — (spinner) |
| `WaitingForConfirmation` | Submitting / settling | — (spinner) |
| `Succeeded` | Paid | success screen (`snapshot.payment`) |
| `Failed` | Terminal failure | failure screen (`snapshot.signingError`) |
| `PaymentExpired` | Timed out | failure screen |
| `PaymentCancelled` | Cancelled (incl. user rejection) | failure screen |
| `InvalidPayment` | Bad/unknown payment ID | failure screen |
| `SanctionedUser` | Compliance block | failure screen |

Group the five terminal failures — `Failed`, `PaymentExpired`, `PaymentCancelled`, `InvalidPayment`, `SanctionedUser` — with the exported helper `isFailureState(state)`. `Succeeded` is terminal but **not** a failure.

### Snapshot fields you'll read

```ts
interface PaymentSnapshot {
  state: PaymentState                    // one of the 17 above (always present)
  payment?: GetPaymentResponse           // intent: amount, merchant, tokens (once loaded)
  options: PaymentOptionExtended[]       // payable options (always present; empty when none)
  selectedOption?: PaymentOptionExtended // the picked option (has .actions)
  collectData?: CollectData | null       // Engine's KYC/contact REQUIREMENTS (.fields)
  infoCaptureData?: InfoCaptureData      // what the user SUBMITTED
  wallet: { isConnected: boolean; accounts: string[] } // flat across all namespaces
  requiresApproval: boolean              // true iff state === 'RequiresApproval'
  signingError?: { code; message; details? } // set only on a non-rejection signing failure
  isQuoteExpired?: boolean
  lastEngineErrorCode?: string           // DIAGNOSTIC ONLY — never present as "why it failed"
  profileId?: string
  profileNotFound?: boolean
}
```

## Named actions

Both `usePaymentSession` (React) and `createPaymentController` (JS) expose the same domain actions. There is no raw `send`/actor on the surface — you drive the machine only through these:

| Action | Drives |
| --- | --- |
| `connectWallet(wallet, namespace?, options?)` | Begin connecting a wallet |
| `disconnectWallet(namespace?)` | Disconnect one namespace, or all |
| `selectOption(option, rank)` | Pick a payment option |
| `confirmSelection()` | Confirm and move toward signing |
| `unselectOption()` | Return to the option list |
| `submitInfoCapture(data)` | Submit collected KYC/contact data |
| `navigateBack()` | Step back |

(There's also a rarely-needed host-orchestration channel — `refreshOptions`, `notifyQuoteExpired`, `markUserSanctioned`, … — for signals the runtime can't observe itself. Most integrations don't need it to start.)

## The one hard rule: the API key stays server-side

The WalletConnect Pay Engine is authenticated with a **secret API key that must never reach the browser**. pay-core enforces this with two entry points: a browser-safe main entry (`createHttpTransport`, no key) and a server-only `@walletconnect/pay-core/server` entry (`createEngineClient`, holds the key). The browser talks to *your* server; your server talks to the Engine. That server proxy is the one piece of backend you must build — see [server-proxy.md](references/server-proxy.md).

## Validation checklist

- [ ] The Engine API key is read from **server env only** — never in client code or a `NEXT_PUBLIC_*` / `VITE_*` var
- [ ] The browser transport `baseUrl` matches wherever your proxy is mounted
- [ ] Your proxy exposes all five Engine calls (`getPayment`, `getPaymentOptions`, `fetchOptionActions`, `confirmPayment`, `getPaymentStatus`)
- [ ] The proxy has origin allowlist / rate limiting / auth before production
- [ ] All 17 `snapshot.state` values are handled (group the 5 failures via `isFailureState`)
- [ ] `snapshot.requiresApproval` toggles the confirm CTA ("Approve & pay" vs "Confirm")
- [ ] The KYC form is built from `snapshot.collectData.fields`, not hardcoded
- [ ] The Reown project has the **headless** feature enabled

## Common errors

| Symptom | Cause | Fix |
| --- | --- | --- |
| API key visible in the browser bundle | Key imported into client code / a public env var | Move it behind the server proxy; import `createEngineClient` only from `@walletconnect/pay-core/server` |
| Transport calls 404 | `baseUrl` ≠ where your proxy is mounted, or a route is missing | Align `baseUrl` with your routes; expose all five Engine calls |
| Wallet never connects / no QR | Reown headless feature off, or missing project ID | Enable headless on the Reown project; set the public project-ID env var |
| Session resets every render (React) | Seams object rebuilt each render | Memoize `seams` on `[wallet]` |
| CSP blocks WC pairing | Missing `frame-src` for `verify.walletconnect.com` / `.org` | Add them (plus `'self'`) to your CSP `frame-src` |
| Stuck on `AwaitingWalletApproval` | User dismissed the wallet prompt | It routes to `PaymentCancelled`; offer a retry from the option list |
