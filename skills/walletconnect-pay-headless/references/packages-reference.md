# Packages Reference

> **Canonical source:** the public [packages reference](https://docs.walletconnect.com/payments/psps/headless-sdk/packages-reference) on the WalletConnect docs is kept current with each release. This file is a convenience snapshot for offline work — when it disagrees with the public page or your installed types, trust those. Always confirm signatures with go-to-definition against your installed version; this is a beta API (v0.1.x) and things move between minor releases.

The runtime is split into layered packages. Each is independently consumable; lower layers never depend on higher ones.

| Package | Role | Depends on |
| --- | --- | --- |
| `@walletconnect/pay-core` | Engine API client — contract types, CAIP utils, browser `Transport` seam, server `createEngineClient`. The foundation. | — |
| `@walletconnect/pay-state` | Headless runtime — state machine, seam contracts, `createPaymentController`, signing strategies, `PaymentSnapshot`. | pay-core |
| `@walletconnect/pay-react` | Thin React binding — `usePaymentSession`. | pay-state |
| `@walletconnect/pay-appkit` | Reown AppKit adapter — `WalletProvider` seam, zero-config `Signer`, headless wallet picker. `/react` subpath. | pay-state |

---

## `@walletconnect/pay-core`

Zero runtime dependencies. Two entry points: a browser-safe main entry and a server-only `/server` entry that holds the key.

### Browser entry

```ts
import { createHttpTransport, type Transport, type HttpTransportConfig } from '@walletconnect/pay-core'

interface HttpTransportConfig {
  baseUrl?: string     // default '/api/wcp'
  fetch?: typeof fetch
  timeoutMs?: number   // default 30_000
}

function createHttpTransport(config?: HttpTransportConfig): Transport
```

The `Transport` contract — five methods, each resolving to an `EngineResponse<T>` envelope (they never throw):

```ts
interface Transport {
  getPayment(paymentId): Promise<EngineResponse<GetPaymentResponse>>
  getPaymentOptions(paymentId, request): Promise<EngineResponse<GetPaymentOptionsResponseExtended>>
  fetchOptionActions(paymentId, request): Promise<EngineResponse<EngineBuildData>>
  confirmPayment(paymentId, request): Promise<EngineResponse<unknown>>
  getPaymentStatus(paymentId): Promise<EngineResponse<GetPaymentStatusResponse>>
}
```

Also exported: all Engine contract types (`GetPaymentResponse`, `PaymentOptionExtended`, `Amount`, `CollectData`, `PaymentStatus`, …), CAIP utilities (`parseCaip2`, `parseCaip10`, …), display helpers (`formatAmount`, `shortAddress`), and transport error helpers (`TRANSPORT_ERROR_CODES`, …).

### Server entry — `@walletconnect/pay-core/server`

Holds the secret key. Never import this into client code (pair it with `'server-only'`).

```ts
import { createEngineClient, type EngineClient, type EngineClientConfig } from '@walletconnect/pay-core/server'

interface EngineClientConfig {
  apiUrl: string
  apiKey: string
  fetch?: typeof fetch
  timeoutMs?: number   // default 30_000
}

function createEngineClient(config: EngineClientConfig): EngineClient
```

`EngineClient` exposes the same five methods as `Transport` — that symmetry is what makes the proxy a thin pass-through.

---

## `@walletconnect/pay-state`

The headless runtime.

### `createPaymentController`

The framework-agnostic binding (the React hook wraps this).

```ts
import { createPaymentController, type PaymentController, type PaymentControllerOptions } from '@walletconnect/pay-state'

interface PaymentControllerOptions {
  paymentId: string
  seams: PaymentSessionSeams        // { transport, clock, signer?, telemetry? }
  wallet: WalletProvider
  initialPayment?: GetPaymentResponse
  signingTimeoutMs?: number
  onMachineEvent?: MachineEventObserver  // read-only analytics observer
}

interface PaymentController {
  getSnapshot(): PaymentSnapshot
  subscribe(listener: () => void): () => void
  start(): void
  destroy(): void
  connectWallet(wallet, namespace?, options?): void
  disconnectWallet(namespace?): void
  selectOption(option, rank): void
  confirmSelection(): void
  unselectOption(): void
  submitInfoCapture(data): void
  navigateBack(): void
}
```

### Seams

```ts
interface PaymentSessionSeams {
  transport: Transport   // Engine calls (from pay-core)
  clock: Clock           // intervals + page visibility (status polling)
  signer?: Signer        // signing capability
  telemetry?: Telemetry  // analytics breadcrumbs (optional)
}
```

Browser defaults ship so you only inject `transport`, `wallet`, and `signer`:

```ts
import { browserClock, noopTelemetry, browserDefaults } from '@walletconnect/pay-state'
```

### `PaymentSnapshot` and `PaymentState`

```ts
type PaymentState =
  | 'Initializing' | 'InvalidPayment' | 'PaymentExpired' | 'PaymentCancelled'
  | 'Succeeded' | 'Failed' | 'SanctionedUser' | 'WaitingForConfirmation'
  | 'ReadyForWallet' | 'ConnectingWallet' | 'LoadingOptions' | 'OptionsReady'
  | 'OptionSelected' | 'RequiresApproval' | 'AwaitingWalletApproval'
  | 'NoOptions' | 'InformationCapture'   // 17 total

// The 5 terminal failure states, grouped:
const FAILURE_STATES = ['Failed', 'PaymentExpired', 'PaymentCancelled', 'InvalidPayment', 'SanctionedUser']
function isFailureState(state: PaymentState): boolean

interface PaymentSnapshot {
  state: PaymentState
  payment?: GetPaymentResponse
  options: PaymentOptionExtended[]
  selectedOption?: PaymentOptionExtended
  collectData?: CollectData | null       // Engine's KYC/contact requirements (.fields)
  infoCaptureData?: InfoCaptureData       // what the user submitted
  approvalResults?: SignPaymentResult[]   // approval-phase signatures (two-phase / Permit2)
  wallet: { isConnected: boolean; accounts: string[] }
  requiresApproval: boolean
  signingError?: { code: WalletErrorCode; message: string; details?: SignPaymentErrorDetails }
  isQuoteExpired?: boolean
  lastEngineErrorCode?: string            // diagnostic only
  profileId?: string
  profileNotFound?: boolean
}
```

`@walletconnect/pay-state` re-exports the public view-model types so you get everything from one import: `CollectData`, `GetPaymentResponse`, `PaymentOptionExtended`, `Namespace`, `WalletErrorCode`, `SignPaymentErrorDetails`, `InfoCaptureData`, `SignPaymentResult`.

### Signing strategies (custom wallet only)

AppKit hosts do **not** need these — `@walletconnect/pay-appkit` exports `createAppKitSigner(wallet)`. These are the low-level primitives for a non-AppKit wallet:

```ts
import { EvmSigningStrategy, SolanaSigningStrategy, signOptionActions } from '@walletconnect/pay-state'
```

See [custom-wallet.md](custom-wallet.md).

---

## `@walletconnect/pay-react`

A single hook — a `useSyncExternalStore`-based binding over the controller. SSR-safe, tear-free, zero XState leak.

```ts
import { usePaymentSession, type UsePaymentSessionOptions, type PaymentSessionApi } from '@walletconnect/pay-react'

function usePaymentSession(options: UsePaymentSessionOptions): PaymentSessionApi
```

`UsePaymentSessionOptions` matches `PaymentControllerOptions`. The return is `{ snapshot }` plus the named actions (`connectWallet`, `disconnectWallet`, `selectOption`, `confirmSelection`, `unselectOption`, `submitInfoCapture`, `navigateBack`).

Plus a **host-orchestration channel** for signals the runtime can't observe itself — `refreshOptions`, `notifyQuoteExpired`, `acknowledgeQuoteExpiry`, `markUserSanctioned`, `setProfileLookup`, `notifyPaymentExpired`, `failWalletConnection`. Most gateways won't need these to start.

---

## `@walletconnect/pay-appkit`

The Reown AppKit adapter — owns the entire AppKit setup so your host stays `@reown/*`-free. Main entry is framework-neutral; the React provider + hooks live on `/react`.

### Main entry

```ts
import {
  createPayAppKit,              // ({ projectId, metadata, themeVariables? }) => PayAppKit  (one-call setup)
  createAppKitSigner,           // (wallet) => Signer  (zero-config; bundles the Solana codec)
  createAppKitWalletList,       // (appKit, options?) => AppKitWalletList  (framework-neutral picker)
  createAppKitWalletProvider,   // (appKit, options?) => WalletProvider
  SUPPORTED_NETWORKS, EVM_NETWORKS, // the WC-owned network set (baked in, not host config)
  loadSolanaWeb3,               // lazy @solana/web3.js codec loader for Solana signing
  applyPlacements, resolvePlacements, // wallet-ordering helpers
  type AppKit                   // re-exported AppKit instance type
} from '@walletconnect/pay-appkit'
```

`AppKitWalletList` (from `createAppKitWalletList`) exposes: `wallet` (the `WalletProvider` seam the machine drives), `getState()`, `subscribe(cb)`, `fetchWallets()`, `getWcUri()`, search + pagination.

### React subpath — `@walletconnect/pay-appkit/react`

```ts
import {
  PayAppKitProvider,           // <PayAppKitProvider projectId metadata>…</> — render once near the root
  usePayAppKit,                // () => { isReady }  — gate before reading the instance
  getPayAppKitInstance,        // () => AppKit       — call only after isReady
  useAppKitWalletProvider,     // (appKit, options?) => { wallet, wallets, wcUri, getWcUri, search…, pagination… }
  type ConnectedWallet,
  type WalletListItem
} from '@walletconnect/pay-appkit/react'
```

`useAppKitWalletProvider(appKit, { wcPayUrl })` returns both the `wallet` seam and a ready-made picker controller (list, search, pagination, pairing QR `wcUri`).
