# Custom Wallet — bring your own `WalletProvider`

`@walletconnect/pay-appkit` is the ready-made wallet integration (Reown AppKit for EVM + Solana). Reach for a custom `WalletProvider` only when you are **not** using AppKit — you have your own wallet connector, an in-house wallet, or an existing wagmi/ethers setup you must reuse.

You implement two things: the `WalletProvider` seam (connection + accounts) and a `Signer` built from the raw signing strategies in `@walletconnect/pay-state`. Everything else (transport, clock, the machine) is unchanged.

## The `WalletProvider` seam

The runtime drives the wallet only through this contract — connect, read accounts, get a provider to sign with, and switch chains. Implement it over your connector:

```ts
import { createPaymentController } from '@walletconnect/pay-state'

const wallet: WalletProvider = {
  // Connection lifecycle (shape per the pay-state WalletProvider contract):
  connect: async (item, namespace, options) => { /* open your connector, return accounts */ },
  disconnect: async (namespace) => { /* drop one namespace, or all */ },
  getAccounts: (namespace) => { /* CAIP-10 accounts currently connected */ },
  getProvider: (namespace) => { /* the RPC provider the signer will use */ },
  switchNetwork: async (caip2) => { /* switch active chain */ },
  subscribe: (listener) => { /* notify on connection/account changes; return unsubscribe */ }
}
```

Check the exact method signatures against your installed version:

```ts
import type { WalletProvider } from '@walletconnect/pay-state'
```

Read them from your editor's go-to-definition on `WalletProvider` — this is a beta API and the shape can change between minor releases. The AppKit adapter (`createAppKitWalletProvider`) is the canonical reference implementation.

## Building a `Signer` from the raw strategies

AppKit hosts get `createAppKitSigner(wallet)` for free. Without AppKit, compose the low-level strategies yourself. They turn a selected option's wallet-RPC actions into signed results:

```ts
import {
  EvmSigningStrategy,
  SolanaSigningStrategy,
  signOptionActions,
  type Signer
} from '@walletconnect/pay-state'

const signer: Signer = {
  // Dispatch each of a selected option's actions to the right strategy per namespace.
  signOptionActions: (option, ctx) =>
    signOptionActions(option, ctx, {
      eip155: new EvmSigningStrategy(/* evm provider from wallet.getProvider('eip155') */),
      solana: new SolanaSigningStrategy(/* solana provider + web3 codec */)
    })
}
```

**Solana note:** the EVM path is dependency-free, but Solana signing needs the `@solana/web3.js` codec. `createAppKitSigner` bundles it via the lazy loader `loadSolanaWeb3` from `@walletconnect/pay-appkit`. For a custom Solana signer, load the codec yourself:

```ts
import { loadSolanaWeb3 } from '@walletconnect/pay-appkit'
const web3 = await loadSolanaWeb3()
```

If you only support EVM, you can omit the Solana strategy.

## Assemble

The rest is identical to the standard paths — only `wallet` and `signer` change:

```ts
const controller = createPaymentController({
  paymentId,
  wallet, // your custom WalletProvider
  seams: {
    transport: createHttpTransport({ baseUrl: '/api/wcp' }),
    clock: browserClock,
    signer  // your custom Signer
  }
})
```

## When NOT to do this

- **You use AppKit** → use `useAppKitWalletProvider` (React) or `createAppKitWalletList` (JS) + `createAppKitSigner`. Do not reinvent the seam.
- **You want a custom wallet *list* but AppKit connection** → `createAppKitWalletList` already exposes list/search/pagination/QR; render your own UI over it. You don't need a custom `WalletProvider` for that.

Reach for this reference only when the connection layer itself is not AppKit.
