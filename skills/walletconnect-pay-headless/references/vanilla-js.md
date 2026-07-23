# Vanilla JavaScript Integration

The framework-neutral path: `createPaymentController` from `@walletconnect/pay-state` + a manual `subscribe` + your own render. Same runtime, same seams, same `snapshot.state` contract as React — no `@walletconnect/pay-react`.

Do the server proxy first ([server-proxy.md](server-proxy.md)). The snapshot states and actions are in the main [SKILL.md](../SKILL.md).

> The snippets show **how to drive the controller**. How you render and route is yours — see the [reference example](https://github.com/WalletConnect/walletconnect-pay-examples/tree/main/gateway/headless-checkout) for a full framework-neutral UI.

## 1. AppKit (zero-config)

```ts
import { createPayAppKit } from '@walletconnect/pay-appkit'

export const payAppKit = createPayAppKit({
  projectId: import.meta.env.VITE_APPKIT_PROJECT_ID ?? '',
  metadata: { name: 'Acme Pay', description: 'Checkout', url: window.location.origin, icons: [] }
})
```

`createPayAppKit` constructs the AppKit instance, the Wagmi/Solana adapters, and the WC-owned network set for you, in headless mode. (If you need direct control, you can build Reown's own `createAppKit({ …, features: { headless: true } })` and hand the instance to `createAppKitWalletList` instead — `createPayAppKit` is the zero-config wrapper over exactly that.)

## 2. Controller + wallet list + render loop

The seams are identical to React: `createHttpTransport({ baseUrl })`, `browserClock`, `createAppKitSigner(wallet)`. `createAppKitWalletList` gives you the picker (list/search/pagination/QR) and exposes `walletList.wallet` — the `WalletProvider` seam the machine drives.

```ts
import { createHttpTransport } from '@walletconnect/pay-core'
import { createAppKitSigner, createAppKitWalletList } from '@walletconnect/pay-appkit'
import { browserClock, createPaymentController } from '@walletconnect/pay-state'
import { payAppKit } from './appkit'

const walletList = createAppKitWalletList(payAppKit, { wcPayUrl: window.location.href })
const wallet = walletList.wallet

const controller = createPaymentController({
  paymentId,
  wallet,
  seams: {
    transport: createHttpTransport({ baseUrl: '/api/wcp' }), // must match your proxy mount
    clock: browserClock,
    signer: createAppKitSigner(wallet)
  }
})

// Re-render on every machine transition AND on wallet-list changes (search, pagination, QR).
controller.subscribe(() => render(controller.getSnapshot()))
walletList.subscribe(() => render(controller.getSnapshot()))

controller.start()             // boot the machine (loads the payment)
void walletList.fetchWallets() // populate the picker
render(controller.getSnapshot())
```

## 3. Render per `snapshot.state`

Your `render(snapshot)` branches on the same 17 states as React (see the [SKILL.md](../SKILL.md) table) and calls controller actions. The shape:

```ts
import { isFailureState } from '@walletconnect/pay-state'

function render(s) {
  if (isFailureState(s.state)) return renderFailure(s.state, s.signingError)
  switch (s.state) {
    case 'ReadyForWallet':
    case 'ConnectingWallet': return renderWalletPicker(walletList) // → controller.connectWallet(item, ns)
    case 'OptionsReady':     return renderOptions(s.options)       // → controller.selectOption(opt, rank)
    case 'InformationCapture': return renderKyc(s.collectData?.fields) // → controller.submitInfoCapture(data)
    case 'OptionSelected':
    case 'RequiresApproval':
      return renderConfirm(s.requiresApproval ? 'Approve & pay' : 'Confirm', () => controller.confirmSelection())
    case 'Succeeded':        return renderSuccess(s.payment)
    default:                 return renderSpinner(s.state) // Initializing / LoadingOptions / Awaiting… / Waiting…
  }
}
```

## Controller surface

```ts
interface PaymentController {
  getSnapshot(): PaymentSnapshot
  subscribe(listener: () => void): () => void  // returns an unsubscribe fn
  start(): void
  destroy(): void                              // call on teardown to stop polling
  // same named actions as the React hook:
  connectWallet, disconnectWallet, selectOption, confirmSelection, unselectOption, submitInfoCapture, navigateBack
}
```

Options match the React hook: `{ paymentId, seams, wallet, initialPayment?, signingTimeoutMs?, onMachineEvent? }`.

## Things worth knowing

- **Subscribe to both** the controller and the wallet-list controller — picker updates come from the latter.
- **`controller.start()`** boots the machine; **`walletList.fetchWallets()`** fills the picker.
- **`controller.destroy()`** on teardown (SPA route change) to stop status polling and release listeners.
- If you rebuild the DOM on every transition, preserve the search input's value/caret/scroll yourself.
