# Vanilla JavaScript Integration

The framework-neutral path: `createPaymentController` from `@walletconnect/pay-state` + a manual `subscribe` + imperative render. Same runtime, same seams, same `snapshot.state` contract as React — no `@walletconnect/pay-react`.

Prerequisites, install, env vars, and the server proxy are in [server-proxy.md](server-proxy.md). Do that first. For vanilla, expose the project ID under your toolchain's client env (e.g. `VITE_APPKIT_PROJECT_ID`).

## Step 1 — AppKit (zero-config)

`appkit.ts` — one factory call. `createPayAppKit` constructs the AppKit instance, the Wagmi/Solana adapters, and the WC-owned network set for you, in headless mode.

```ts
import { createPayAppKit } from '@walletconnect/pay-appkit'

export const payAppKit = createPayAppKit({
  projectId: import.meta.env.VITE_APPKIT_PROJECT_ID ?? '',
  metadata: {
    name: 'Acme Pay (vanilla)',
    description: 'Headless checkout — vanilla JS',
    url: window.location.origin,
    icons: []
  }
})
```

> **Escape hatch:** if you need direct control over AppKit, you can construct Reown's `createAppKit({ adapters, networks, projectId, features: { headless: true }, metadata })` yourself and hand the instance to `createAppKitWalletList` / `createAppKitWalletProvider`. `createPayAppKit` is the zero-config wrapper over exactly that.

## Step 2 — Controller + wallet list + render loop

`main.ts`

```ts
import { createHttpTransport } from '@walletconnect/pay-core'
import { createAppKitSigner, createAppKitWalletList } from '@walletconnect/pay-appkit'
import { browserClock, createPaymentController } from '@walletconnect/pay-state'

import { payAppKit } from './appkit'
import { createCheckout } from './render' // your imperative renderer

function resolvePaymentId(): string {
  const fromPath = window.location.pathname.replace(/^\/+/, '').split('/')[0]
  if (fromPath) return decodeURIComponent(fromPath)
  return new URLSearchParams(window.location.search).get('paymentId') ?? 'pay_demo_123'
}

const paymentId = resolvePaymentId()

// Framework-neutral wallet-list controller: fetches the wallet list, search + pagination,
// pairing QR URI, and exposes `walletList.wallet` — the WalletProvider seam the machine drives.
const walletList = createAppKitWalletList(payAppKit, {
  isMobile: window.matchMedia('(max-width: 768px)').matches,
  wcPayUrl: window.location.href
})
const wallet = walletList.wallet

const controller = createPaymentController({
  paymentId,
  wallet,
  seams: {
    transport: createHttpTransport({ baseUrl: '/api/wcp' }),
    clock: browserClock,
    signer: createAppKitSigner(wallet)
  }
})

const mount = document.getElementById('checkout')!
const checkout = createCheckout({ mount, controller, walletList, paymentId })

// Re-render on every machine transition …
controller.subscribe(() => checkout.render(controller.getSnapshot()))
// … and on wallet-list changes (search results, pagination, QR URI arriving).
walletList.subscribe(() => checkout.render(controller.getSnapshot()))

controller.start()               // begin the machine (loads the payment)
void walletList.fetchWallets()   // populate the picker
checkout.render(controller.getSnapshot())
```

## The controller surface

```ts
interface PaymentController {
  getSnapshot(): PaymentSnapshot
  subscribe(listener: () => void): () => void   // returns an unsubscribe fn
  start(): void
  destroy(): void
  // domain actions — same set as the React hook:
  connectWallet(wallet, namespace?, options?): void
  disconnectWallet(namespace?): void
  selectOption(option, rank): void
  confirmSelection(): void
  unselectOption(): void
  submitInfoCapture(data): void
  navigateBack(): void
}
```

`createPaymentController` options match the React hook: `{ paymentId, seams, wallet, initialPayment?, signingTimeoutMs?, onMachineEvent? }`.

## Imperative render, keyed off `snapshot.state`

Your `render(snapshot)` branches on the same 17 states as the React switch (see the main SKILL table). The load-bearing branches:

```ts
import { isFailureState, type PaymentSnapshot } from '@walletconnect/pay-state'
import { formatAmount } from '@walletconnect/pay-core'

function render(s: PaymentSnapshot) {
  const state = s.state

  if (isFailureState(state)) return renderFailure(state, s.signingError)
  if (state === 'Succeeded') return renderSuccess(`Paid ${formatAmount(s.payment?.amount)}`)

  if (state === 'ReadyForWallet' || state === 'ConnectingWallet') return renderWalletPicker(s)
  if (state === 'LoadingOptions') return renderSpinner('Finding payment options…')
  if (state === 'NoOptions')      return renderEmpty('No payment options for this wallet.')
  if (state === 'OptionsReady')   return renderOptions(s.options) // → controller.selectOption(opt, rank)

  if (state === 'InformationCapture')
    return renderKycForm(s.collectData?.fields) // → controller.submitInfoCapture(data)

  if (state === 'AwaitingWalletApproval') return renderSpinner('Approve in your wallet…')
  if (state === 'WaitingForConfirmation') return renderSpinner('Submitting payment…')

  // OptionSelected | RequiresApproval → the Confirm CTA
  const building = (s.selectedOption?.actions ?? []).some(a => a.type === 'build')
  const label = building ? 'Preparing payment…' : s.requiresApproval ? 'Approve & pay' : 'Confirm'
  return renderConfirm(label, () => controller.confirmSelection())
}
```

## Key rules

- **Subscribe to both** the controller *and* the wallet-list controller; the picker updates (search, pagination, QR URI) come from the latter.
- **Call `controller.start()`** to boot the machine, and `walletList.fetchWallets()` to fill the picker.
- **`createHttpTransport({ baseUrl: '/api/wcp' })`, `browserClock`, `createAppKitSigner(wallet)`** — the seams are identical to React.
- **`controller.destroy()`** when tearing down (SPA route change) to stop polling and release listeners.
- If you rebuild the DOM on every transition, preserve the search input's value/caret/scroll yourself.
