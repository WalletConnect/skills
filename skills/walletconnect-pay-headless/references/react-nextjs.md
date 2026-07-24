# React / Next.js Integration

The recommended path: render `<PayAppKitProvider>` once, drive a single `usePaymentSession` hook, and render per `snapshot.state`. Wallet connection is zero-config — the SDK owns the Reown AppKit / Wagmi / Solana setup; you never touch `@reown/*`, `wagmi`, or `viem`.

Do the server proxy first ([server-proxy.md](server-proxy.md)). The snapshot states and actions are in the main [SKILL.md](../SKILL.md).

> The snippets below show **how to call the SDK**. Where you mount the provider, how you route to the checkout, and how you style each state are your choices — this is one arrangement, not a required one. For a complete branded UI, read the [reference example](https://github.com/WalletConnect/walletconnect-pay-examples/tree/main/gateway/headless-checkout).

## 1. Provider

Mount `<PayAppKitProvider>` once, above wherever your checkout renders. It owns AppKit's client-only construction, the `WagmiProvider` + `QueryClientProvider` tree, and an SSR-safe context — in **headless mode** (no built-in modal; you render your own picker).

```tsx
'use client'
import { PayAppKitProvider } from '@walletconnect/pay-appkit/react'

export function PayProvider({ children }: { children: React.ReactNode }) {
  return (
    <PayAppKitProvider
      projectId={process.env.NEXT_PUBLIC_APPKIT_PROJECT_ID ?? ''}
      metadata={{ name: 'Acme Pay', description: 'Checkout', url: 'https://example.com', icons: [] }}
    >
      {children}
    </PayAppKitProvider>
  )
}
```

## 2. Assemble the seams and drive the session

The three seams: `transport` (→ your proxy), `clock` (`browserClock`), `signer` (`createAppKitSigner(wallet)`). `useAppKitWalletProvider` turns the AppKit instance into the `WalletProvider` seam **and** a ready-made picker (list, search, pagination, pairing QR `wcUri`).

```tsx
'use client'
import { createHttpTransport } from '@walletconnect/pay-core'
import { createAppKitSigner } from '@walletconnect/pay-appkit'
import { getPayAppKitInstance, useAppKitWalletProvider, usePayAppKit } from '@walletconnect/pay-appkit/react'
import { browserClock } from '@walletconnect/pay-state'
import { usePaymentSession } from '@walletconnect/pay-react'
import { useMemo } from 'react'

export function Checkout({ paymentId }: { paymentId: string }) {
  // The provider builds AppKit asynchronously — read the instance only once ready.
  const { isReady } = usePayAppKit()
  const appKit = isReady ? getPayAppKitInstance() : undefined

  const { wallet, wallets, wcUri /* + search / pagination helpers */ } =
    useAppKitWalletProvider(appKit, {
      wcPayUrl: typeof window !== 'undefined' ? window.location.href : undefined
    })

  // Memoize on [wallet] — rebuilding this object every render tears down the session.
  const seams = useMemo(
    () => ({
      transport: createHttpTransport({ baseUrl: '/api/wcp' }), // must match your proxy mount
      clock: browserClock,
      signer: createAppKitSigner(wallet)
    }),
    [wallet]
  )

  const {
    snapshot,
    connectWallet, disconnectWallet,
    selectOption, confirmSelection, submitInfoCapture
  } = usePaymentSession({ paymentId, seams, wallet })

  return <YourUI snapshot={snapshot} /* pass the actions + wallet picker data down */ />
}
```

That's the whole integration. Everything past this point is your UI reading `snapshot` and calling actions.

## 3. Render per `snapshot.state`

A `switch` on `snapshot.state` is the natural shape. This is abbreviated — the full state list and the action for each is the table in [SKILL.md](../SKILL.md):

```tsx
switch (snapshot.state) {
  case 'ReadyForWallet':
  case 'ConnectingWallet':
    // your wallet picker → connectWallet(item, item.namespaces[0])
    return <WalletPicker wallets={wallets} wcUri={wcUri} onConnect={connectWallet} />

  case 'OptionsReady':
    return <OptionList options={snapshot.options} onSelect={selectOption} />

  case 'InformationCapture':
    // build the form from the Engine's requirements — never hardcode fields
    return <KycForm fields={snapshot.collectData?.fields} onSubmit={submitInfoCapture} />

  case 'OptionSelected':
  case 'RequiresApproval':
    return (
      <button onClick={confirmSelection}>
        {snapshot.requiresApproval ? 'Approve & pay' : 'Confirm'}
      </button>
    )

  case 'Succeeded':
    return <Success payment={snapshot.payment} />

  // Initializing / LoadingOptions / AwaitingWalletApproval / WaitingForConfirmation → spinners
  // Failed / PaymentExpired / PaymentCancelled / InvalidPayment / SanctionedUser → failure screen
  //   group these five with isFailureState(snapshot.state)
  default:
    return <StatusView state={snapshot.state} error={snapshot.signingError} />
}
```

## Things worth knowing

- **Memoize `seams` on `[wallet]`.** This is the most common mistake — an un-memoized seams object recreates the session on every render.
- **Gate on `usePayAppKit().isReady`** before `getPayAppKitInstance()`; the provider builds AppKit asynchronously.
- **Build the KYC form from `snapshot.collectData.fields`** — the Engine decides what's required per option; don't hardcode.
- **`requiresApproval`** flips the confirm CTA between "Approve & pay" (two-phase, e.g. Permit2) and "Confirm". Both call `confirmSelection()`.
- **A plain user rejection** routes to `PaymentCancelled` and does *not* set `signingError`; only non-rejection signing failures do.
- **Multichain wallets** (more than one namespace) usually prompt a network choice first; pass the chosen `namespace` to `connectWallet(item, namespace)`.

## `usePaymentSession` options

```ts
usePaymentSession({
  paymentId,
  seams,             // { transport, clock, signer?, telemetry? }
  wallet,            // the WalletProvider seam
  initialPayment,    // optional — skip the first fetch if you already have the intent
  signingTimeoutMs,  // optional
  onMachineEvent     // optional — read-only analytics observer (event, snapshot)
})
```

Returns `{ snapshot }` plus the named actions. No `send`, no actor — the machine is driven only through the actions.
