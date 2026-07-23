# Custom Wallet — bring your own `WalletProvider`

> This path touches the most version-sensitive surface (the `WalletProvider` / `Signer` seam signatures). Always confirm the exact shapes with go-to-definition against your installed `@walletconnect/pay-state`, and check the [packages reference](https://docs.walletconnect.com/payments/psps/headless-sdk/packages-reference) — trust those over the sketches here.

`@walletconnect/pay-appkit` is the ready-made wallet integration (Reown AppKit for EVM + Solana). Reach for a custom `WalletProvider` only when you are **not** using AppKit — you have your own connector, an in-house wallet, or an existing setup to reuse.

You supply one thing the SDK can't: the `WalletProvider` seam. The signer is **not** hand-built — `pay-state` ships `createSigner` to construct it from any `WalletProvider`.

## Implement the `WalletProvider` seam

The runtime drives the wallet only through this contract — connect, read accounts, hand over a provider to sign with, switch chains, and notify on changes. Implement it over your connector:

```ts
import type { WalletProvider } from '@walletconnect/pay-state'

const wallet: WalletProvider = {
  connect: async (item, namespace, options) => { /* open your connector; resolve with accounts */ },
  disconnect: async (namespace) => { /* drop one namespace, or all */ },
  getAccounts: (namespace) => { /* CAIP-10 accounts currently connected */ },
  getProvider: (namespace) => { /* the RPC provider the signer will use */ },
  switchNetwork: async (caip2) => { /* switch the active chain */ },
  subscribe: (listener) => { /* notify on connection/account changes; return unsubscribe */ }
}
```

Check the exact method signatures with go-to-definition on `WalletProvider` — this is a beta API and the shape can change between minor releases. The AppKit adapter (`createAppKitWalletProvider` in `@walletconnect/pay-appkit`) is the canonical reference implementation to copy from.

## Build the `Signer` with `createSigner`

`createSigner(wallet, { loadSolanaWeb3 })` (exported from `@walletconnect/pay-state`) builds the entire `Signer` seam from your `WalletProvider` — it picks the EVM or Solana signing strategy per namespace for you. This is the whole signer:

```ts
import { createSigner } from '@walletconnect/pay-state'
import { loadSolanaWeb3 } from '@walletconnect/pay-appkit' // lazy @solana/web3.js codec loader

const signer = createSigner(wallet, { loadSolanaWeb3 })
```

`loadSolanaWeb3` is only invoked when a Solana option is signed, so the codec stays out of your bundle until needed. If you don't depend on `@walletconnect/pay-appkit` at all, pass your own loader (`() => import('@solana/web3.js')`); EVM-only flows never call it.

The resulting seam exposes `signActions(option, range?)` — but you don't call that yourself; the runtime does.

## Assemble

Everything else is identical to the standard paths — only `wallet` and `signer` differ:

```ts
import { createHttpTransport } from '@walletconnect/pay-core'
import { browserClock, createPaymentController, createSigner } from '@walletconnect/pay-state'

const controller = createPaymentController({
  paymentId,
  wallet, // your custom WalletProvider
  seams: {
    transport: createHttpTransport({ baseUrl: '/api/wcp' }),
    clock: browserClock,
    signer: createSigner(wallet, { loadSolanaWeb3 })
  }
})
```

## Advanced: raw signing strategies

`createSigner` composes these for you; reach for them only if you need to override how a namespace signs. The strategies live in `@walletconnect/pay-state`:

```ts
import { EvmSigningStrategy, SolanaSigningStrategy } from '@walletconnect/pay-state'

// Each strategy takes the namespace provider plus an options bag, e.g.:
new SolanaSigningStrategy(solanaProvider, { loadWeb3: loadSolanaWeb3 })
// EvmSigningStrategy likewise needs its network-switch wiring in the options arg.
```

Verify the exact constructor options against the installed source before using these directly — `createSigner` is the supported path for almost every custom wallet.

## When NOT to do this

- **You use AppKit** → use `useAppKitWalletProvider` (React) / `createAppKitWalletList` (JS) + `createAppKitSigner`. Don't reimplement the seam.
- **You want a custom wallet *list* but AppKit connection** → `createAppKitWalletList` already gives you list/search/pagination/QR; render your own UI over it. You don't need a custom `WalletProvider` for that.

Reach for this reference only when the connection layer itself isn't AppKit.
