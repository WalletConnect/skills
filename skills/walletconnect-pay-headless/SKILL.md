---
name: walletconnect-pay-headless
description: Guides developers building a fully branded, self-hosted crypto checkout on the WalletConnect Pay Headless SDK (the @walletconnect/pay-* packages). Use when implementing a headless payment flow in React/Next.js or vanilla JavaScript, wiring the server proxy that keeps the Engine API key server-side, setting up wallet connection through AppKit, rendering the payment state machine, or troubleshooting the pay-core / pay-state / pay-react / pay-appkit packages.
---

# WalletConnect Pay — Headless SDK Integration

## Goal

Help developers build a **fully branded, fully owned crypto checkout** inside their own product using the WalletConnect Pay Headless SDK. The SDK is the exact runtime that powers the hosted Buyer Experience, extracted into framework-agnostic `@walletconnect/pay-*` packages. You get the payment state machine, a typed Engine API client, and wallet orchestration; you bring the UI, branding, routing, and infrastructure.

The mental model is **headless runtime + host**: the payment flow lives entirely in the SDK, your app is the host that consumes it, and the runtime reaches the outside world only through five injectable **seams**.

## When to use

- Building a self-hosted, branded checkout for a PSP, acquirer, platform, or marketplace
- Embedding pay-with-crypto directly into an existing checkout flow (no redirect to a hosted page)
- Wiring the server proxy that keeps the Engine API key off the browser
- Setting up wallet connection (EVM + Solana) via the AppKit adapter, or bringing your own wallet
- Rendering the payment lifecycle (load → connect → quote → sign → confirm → settle) from a snapshot
- Troubleshooting `@walletconnect/pay-core`, `-state`, `-react`, or `-appkit`

## When not to use

- You just want to accept payments with the least effort → use the **hosted gateway** (`pay.walletconnect.com`) or the **Ecommerce** integration instead
- You are creating payment requests as a merchant (payment links / QR / status polling) → use the **`walletconnect-pay-merchant`** skill
- You are building a wallet that *accepts* WC Pay payments → use the **`walletconnect-pay`** (wallet) skill

## Supported networks & tokens

**Tokens:** USDC, USDT, EURC, PYUSD, and more (full WC Pay coverage).
**Networks:** Ethereum, Polygon, Base, Optimism, Arbitrum, and Solana (rolling out).

The Engine returns the concrete, live set of payable options for the connected wallet — you never hardcode token/network lists. See [Token & chain coverage](https://docs.walletconnect.com/payments/token-and-chain-coverage) for the current list.

## Beta

The Headless SDK is beta (v0.1.x). Public APIs may change between minor releases until 1.0. [Talk to the team](https://share.hsforms.com/1XsMCkUxFT2Cte8SCeAh89wnxw6s) before going to production.

## The four packages

The runtime is layered; lower packages never import higher ones, so you take only what you need.

| Package | Role | Depends on | React? |
| --- | --- | --- | --- |
| `@walletconnect/pay-core` | Engine API client — contract types, CAIP utils, the browser `Transport` seam (`createHttpTransport`), and the server-only `createEngineClient` (`/server` subpath) that holds your API key. | — | no |
| `@walletconnect/pay-state` | The headless runtime — the payment state machine, seam contracts, `createPaymentController`, signing strategies, and the public `PaymentSnapshot`. No React, no HTTP client, no wallet SDK. | pay-core | no |
| `@walletconnect/pay-react` | Thin React binding — `usePaymentSession` returns the snapshot + named actions. Zero state-machine leak. | pay-state | yes |
| `@walletconnect/pay-appkit` | Reown AppKit adapter — owns the entire AppKit setup, implements the `WalletProvider` seam, provides a zero-config `Signer`, and ships a headless wallet-picker. `/react` subpath ships the provider + hooks. | pay-state | `/react` only |

## The five seams

The runtime is driven entirely through these injectable contracts. In practice you wire only the first three; the SDK ships the rest.

| Seam | Abstracts | You provide it with |
| --- | --- | --- |
| `Transport` | Engine HTTP calls | `createHttpTransport({ baseUrl: '/api/wcp' })` from pay-core → your server proxy |
| `WalletProvider` | connect / accounts / provider / switch | `pay-appkit` (`useAppKitWalletProvider` in React, `createAppKitWalletList` in JS), or your own |
| `Signer` | signs a payment option's wallet-RPC actions | `createAppKitSigner(wallet)` from pay-appkit — one call |
| `Clock` | intervals + page visibility (status polling) | `browserClock` from pay-state (default) |
| `Telemetry` | analytics breadcrumbs | your pipeline, or `noopTelemetry` (optional) |

## Choose your integration path

| Path | When to use | Reference |
| --- | --- | --- |
| **React / Next.js** (recommended) | You use React. `usePaymentSession` + `<PayAppKitProvider>`. | [react-nextjs.md](references/react-nextjs.md) |
| **Vanilla JavaScript** | Framework-neutral. `createPaymentController` + subscribe + imperative render. | [vanilla-js.md](references/vanilla-js.md) |
| **Custom wallet** | You are not using AppKit; you implement the `WalletProvider` seam and use the raw signing strategies. | [custom-wallet.md](references/custom-wallet.md) |

Supporting references, useful for every path:

- [server-proxy.md](references/server-proxy.md) — the five route handlers + the server Engine client + why the key stays server-side
- [packages-reference.md](references/packages-reference.md) — the full public API surface of all four packages

## Prerequisites

1. **Node 18+**. React examples use **Next.js** (App Router); the JS example is framework-neutral.
2. A **Reown Project ID** — create one at [dashboard.reown.com](https://dashboard.reown.com) and enable the **headless** feature on the project.
3. A **WalletConnect Pay Gateway API key** for the Engine (server-side only). [Talk to us](https://share.hsforms.com/1XsMCkUxFT2Cte8SCeAh89wnxw6s) to get onboarded.

## Install

Install only the Headless SDK. Wallet connectivity (`@reown/appkit`, `wagmi`, `viem`, `@solana/web3.js`, `@tanstack/react-query`) comes transitively through `@walletconnect/pay-appkit` — you never add or configure it directly.

```bash
npm install @walletconnect/pay-core @walletconnect/pay-state \
            @walletconnect/pay-appkit @walletconnect/pay-react
```

Omit `@walletconnect/pay-react` if you are not using React.

## The payment lifecycle

Whatever UI you build, the runtime moves a payment through the same stages. Your job is to render each stage and call the matching action.

```
Load payment → Connect wallet → Fetch options → Select & build → Sign → Confirm & settle
```

1. **Load** — the buyer arrives with a payment ID. The runtime fetches the intent (amount, merchant, accepted tokens).
2. **Connect** — the buyer connects a wallet through the `WalletProvider` seam. The runtime reads accounts across supported networks.
3. **Fetch options** — given the accounts, the Engine returns the concrete ways to pay (token, network, amount, fees, and whether compliance data is required).
4. **Select & build** — the buyer picks an option; the runtime builds the transaction(s) and the exact wallet-RPC actions to sign.
5. **Sign** — the `Signer` drives the wallet through the required signatures (e.g. a permit + the payment).
6. **Confirm & settle** — signed results are submitted; the runtime polls status until success, failure, or expiry.

## The three things you build

Everything else comes from the SDK. You build exactly:

1. **A server proxy** — routes that forward to the Engine with your secret key. → [server-proxy.md](references/server-proxy.md)
2. **A browser transport** — `createHttpTransport({ baseUrl: '/api/wcp' })`, pointed at those routes.
3. **The AppKit provider** — one component (`<PayAppKitProvider>` in React) or one factory call (`createPayAppKit` in JavaScript).

Then `usePaymentSession` (React) or `createPaymentController` (JavaScript) ties it together and gives you a snapshot to render.

## The snapshot is the whole UI contract

`snapshot.state` is one of **17** values. Render per state and call the matching action. This table is the heart of the integration — the exact `PaymentState` union from `@walletconnect/pay-state`:

| `snapshot.state` | Meaning | What to render / do |
| --- | --- | --- |
| `Initializing` | Loading the payment intent | Spinner |
| `ReadyForWallet` | Waiting for wallet connection | Wallet picker → `connectWallet(item, namespace?)` |
| `ConnectingWallet` | Connection in progress | Spinner / QR (`wcUri`) |
| `LoadingOptions` | Fetching payable options | Spinner |
| `OptionsReady` | Options available | List `snapshot.options` → `selectOption(option, rank)` |
| `NoOptions` | No payable options for this wallet | Empty state; let them switch wallet |
| `InformationCapture` | Engine requires KYC/contact data | Form from `snapshot.collectData.fields` → `submitInfoCapture(data)` |
| `OptionSelected` | Option chosen, ready to confirm | Confirm button → `confirmSelection()` |
| `RequiresApproval` | Needs a separate approval (e.g. Permit2) | Button labelled "Approve & pay" → `confirmSelection()` |
| `AwaitingWalletApproval` | Waiting on wallet signature | Spinner "Approve in your wallet…" (no button) |
| `WaitingForConfirmation` | Submitting / settling | Spinner "Submitting payment…" |
| `Succeeded` | Paid | Success screen (`snapshot.payment`) |
| `Failed` | Terminal failure | Failure screen (`snapshot.signingError`) |
| `PaymentExpired` | Payment timed out | Failure screen |
| `PaymentCancelled` | Cancelled (incl. user rejection) | Failure screen |
| `InvalidPayment` | Bad/unknown payment ID | Failure screen |
| `SanctionedUser` | Compliance block | Failure screen |

The five terminal **failure** states — `Failed`, `PaymentExpired`, `PaymentCancelled`, `InvalidPayment`, `SanctionedUser` — are grouped by the exported helper `isFailureState(state)`. `Succeeded` is terminal but **not** a failure.

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
  signingError?: { code; message; details? } // set only on non-rejection signing failure
  isQuoteExpired?: boolean
  lastEngineErrorCode?: string           // DIAGNOSTIC ONLY — never "why it failed"
  profileId?: string
  profileNotFound?: boolean
}
```

## Named actions

Both `usePaymentSession` (React) and `createPaymentController` (JS) expose the same domain actions:

| Action | Drives |
| --- | --- |
| `connectWallet(wallet, namespace?, options?)` | Begin connecting a wallet |
| `disconnectWallet(namespace?)` | Disconnect one namespace, or all |
| `selectOption(option, rank)` | Pick a payment option |
| `confirmSelection()` | Confirm and move toward signing |
| `unselectOption()` | Return to the option list |
| `submitInfoCapture(data)` | Submit collected KYC/contact data |
| `navigateBack()` | Step back |

There is **no** raw `send`/actor on the surface — you drive the machine only through these actions (and, rarely, the host-orchestration channel: `refreshOptions`, `notifyQuoteExpired`, `markUserSanctioned`, … — most gateways don't need these to start).

## Validation checklist

- [ ] The Engine API key is read from **server env only** and never appears in client code or `NEXT_PUBLIC_*` / `VITE_*` vars
- [ ] The browser transport `baseUrl` matches the proxy mount (`/api/wcp`) exactly
- [ ] All **five** proxy routes exist: `GET :id`, `POST :id/options`, `POST :id/fetch`, `POST :id/confirm`, `GET :id/status`
- [ ] Proxy routes have origin allowlist / rate limiting / auth before production (the examples are a starting point, not production-ready)
- [ ] `<PayAppKitProvider>` is rendered once near the root (React); the AppKit instance is read only after `usePayAppKit().isReady`
- [ ] The seams are memoized on `wallet` (React `useMemo`) so the session isn't rebuilt every render
- [ ] All **17** `snapshot.state` values are handled (group the 5 failure states via `isFailureState`)
- [ ] `snapshot.requiresApproval` toggles the CTA label ("Approve & pay" vs "Confirm")
- [ ] The KYC form is built from `snapshot.collectData.fields`, not hardcoded
- [ ] The Reown project has the **headless** feature enabled
- [ ] `signingError` is shown for diagnostics, but `lastEngineErrorCode` is NOT presented as the failure reason

## Common errors

| Symptom | Cause | Fix |
| --- | --- | --- |
| API key visible in browser bundle | Key imported into a client component / public env var | Move it behind the server proxy; import `createEngineClient` only from `@walletconnect/pay-core/server` with `'server-only'` |
| Transport 404s | `baseUrl` ≠ route mount, or a route is missing | Ensure all five routes under `/api/wcp/payment/[id]/...` and matching `baseUrl` |
| Wallet never connects / no QR | Reown headless feature off, or missing/blocked project ID | Enable headless on the Reown project; set the public project-ID env var |
| `getPayAppKitInstance()` throws | Read before `usePayAppKit().isReady` | Gate on `isReady` first |
| Session resets every render | Seams object rebuilt each render | Wrap `seams` in `useMemo([wallet])` |
| CSP blocks WC pairing | Missing `frame-src` for `verify.walletconnect.com`/`.org` | Add them (plus `'self'`) to your CSP `frame-src` |
| Stuck on `AwaitingWalletApproval` | User dismissed the wallet prompt | It routes to `PaymentCancelled`; offer a retry from the option list |

## Examples / prompts this skill activates on

1. "Add a WalletConnect Pay headless checkout to my Next.js app."
2. "Wire the server proxy so my Engine API key stays server-side."
3. "Render the payment options and confirm step from the snapshot."
4. "How do I handle the Permit2 approve-and-pay step?" (→ `RequiresApproval` + `confirmSelection()`)
5. "Build a framework-neutral checkout with `createPaymentController`."
6. "Bring my own wallet instead of AppKit." (→ implement `WalletProvider`, use `EvmSigningStrategy`/`SolanaSigningStrategy`)
7. "Why is my API key showing up in the browser bundle?" (→ server proxy + `/server` subpath)

## Evaluations

1. **Activation** — "Build a branded crypto checkout in my Next.js app with WalletConnect Pay." → React path.
2. **Activation** — "Set up the WC Pay Engine proxy routes in Next.js." → server-proxy reference.
3. **Activation** — "Render the WC Pay payment state machine in vanilla JS." → vanilla path.
4. **Non-activation** — "Create a USDC payment link and poll its status." → use `walletconnect-pay-merchant`.
5. **Non-activation** — "Add WC Pay acceptance to my mobile wallet." → use `walletconnect-pay` (wallet).
6. **Edge case** — "Where does the Engine API key live?" → server env only, behind the proxy, via `@walletconnect/pay-core/server`.
7. **Edge case** — "How many payment states are there?" → 17 `PaymentState` values; 5 are terminal failures (`isFailureState`).
8. **Troubleshooting** — "My transport calls 404." → `baseUrl` mismatch or a missing route among the five.
