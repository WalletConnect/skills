# React / Next.js Integration

The recommended path. You render `<PayAppKitProvider>` once near the root, then drive a single `usePaymentSession` hook and render per `snapshot.state`. Wallet connection is **zero-config** — the SDK owns the entire Reown AppKit / Wagmi / Solana setup; you never touch `@reown/*`, `wagmi`, or `viem`.

Prerequisites, install, env vars, and the server proxy are in [server-proxy.md](server-proxy.md). Do that first.

## Step 1 — Provider (once, near the root)

`components/providers.tsx`

```tsx
'use client'

import { PayAppKitProvider } from '@walletconnect/pay-appkit/react'

const projectId = process.env.NEXT_PUBLIC_APPKIT_PROJECT_ID ?? ''

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <PayAppKitProvider
      projectId={projectId}
      metadata={{
        name: 'Acme Pay',
        description: 'Headless checkout',
        url: typeof window !== 'undefined' ? window.location.origin : 'https://example.com',
        icons: []
      }}
    >
      {children}
    </PayAppKitProvider>
  )
}
```

`<PayAppKitProvider>` owns AppKit's client-only construction, the `WagmiProvider` + `QueryClientProvider` tree, and an SSR-safe context. It builds AppKit in **headless mode** — no built-in modal; you render your own wallet picker.

## Step 2 — Checkout (seams + session)

`components/checkout.tsx`

```tsx
'use client'

import { createHttpTransport } from '@walletconnect/pay-core'
import { createAppKitSigner } from '@walletconnect/pay-appkit'
import {
  getPayAppKitInstance,
  useAppKitWalletProvider,
  usePayAppKit,
  type WalletListItem
} from '@walletconnect/pay-appkit/react'
import { browserClock, isFailureState, type PaymentOptionExtended } from '@walletconnect/pay-state'
import { usePaymentSession } from '@walletconnect/pay-react'
import { useMemo } from 'react'

export function Checkout({ paymentId }: { paymentId: string }) {
  // The provider constructs AppKit asynchronously; read the instance once it's ready.
  const { isReady } = usePayAppKit()
  const appKit = isReady ? getPayAppKitInstance() : undefined

  // The WalletProvider seam + a ready-made picker (list, search, pagination, QR URI).
  const {
    wallet, wallets, wcUri, getWcUri,
    searchQuery, setSearchQuery, hasMore, loadMore, isFetchingWallets
  } = useAppKitWalletProvider(appKit, {
    wcPayUrl: typeof window !== 'undefined' ? window.location.href : undefined
  })

  // Assemble the runtime seams. The signer is one built-in call.
  const seams = useMemo(
    () => ({
      transport: createHttpTransport({ baseUrl: '/api/wcp' }),
      clock: browserClock,
      signer: createAppKitSigner(wallet)
    }),
    [wallet]
  )

  const {
    snapshot,
    connectWallet,
    disconnectWallet,
    selectOption,
    confirmSelection,
    submitInfoCapture
  } = usePaymentSession({ paymentId, seams, wallet })

  return <div>{renderState()}</div>

  function renderState() {
    switch (snapshot.state) {
      case 'Initializing':
        return <Spinner label="Loading payment…" />

      case 'ReadyForWallet':
      case 'ConnectingWallet':
        return (
          <WalletPicker
            wallets={wallets}
            wcUri={wcUri}
            searchQuery={searchQuery}
            onSearch={setSearchQuery}
            hasMore={hasMore}
            onLoadMore={loadMore}
            isFetching={isFetchingWallets}
            connecting={snapshot.state === 'ConnectingWallet'}
            onConnect={(w: WalletListItem) =>
              // Multichain wallets (>1 namespace) usually prompt a network choice first.
              w.namespaces.length > 1 ? openNamespaceModal(w) : connectWallet(w, w.namespaces[0])
            }
          />
        )

      case 'LoadingOptions':
        return <Spinner label="Finding payment options…" />

      case 'OptionsReady':
        return (
          <OptionList
            options={snapshot.options}
            onSelect={(opt: PaymentOptionExtended, rank: number) => selectOption(opt, rank)}
          />
        )

      case 'NoOptions':
        return <Empty label="No payment options for this wallet." onSwitch={() => disconnectWallet()} />

      case 'InformationCapture':
        // Build the form from the Engine's requirements — never hardcode fields.
        return <KycForm fields={snapshot.collectData?.fields} onSubmit={submitInfoCapture} />

      case 'OptionSelected':
      case 'RequiresApproval':
        return (
          <>
            {snapshot.signingError && (
              <p>Signing failed ({snapshot.signingError.code}): {snapshot.signingError.message}</p>
            )}
            <button onClick={() => confirmSelection()}>
              {snapshot.requiresApproval ? 'Approve & pay' : 'Confirm'}
            </button>
          </>
        )

      case 'AwaitingWalletApproval':
        return <Spinner label="Approve in your wallet…" />

      case 'WaitingForConfirmation':
        return <Spinner label="Submitting payment…" />

      case 'Succeeded':
        return <Success payment={snapshot.payment} />

      default:
        // Failed | PaymentExpired | PaymentCancelled | InvalidPayment | SanctionedUser
        return <Failure state={snapshot.state} error={snapshot.signingError} />
    }
  }
}
```

That is a full gateway: connect → options → (optional KYC) → confirm → sign → settle, all driven by the runtime. You only render and call actions.

## Wiring it up

```tsx
// app/layout.tsx
import { Providers } from '@/components/providers'
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html><body><Providers>{children}</Providers></body></html>
}

// app/pay/[id]/page.tsx
import { Checkout } from '@/components/checkout'
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <Checkout paymentId={id} />
}
```

## Key rules

- **`useMemo` the seams** on `[wallet]`. Rebuilding the seams object every render tears down and recreates the session.
- **Gate on `isReady`** before calling `getPayAppKitInstance()` — the provider builds AppKit asynchronously.
- **Build the KYC form from `snapshot.collectData.fields`.** The Engine decides what's required per option.
- **`requiresApproval`** flips the CTA between "Approve & pay" (two-phase, e.g. Permit2) and "Confirm". Both call `confirmSelection()`.
- **A plain user rejection** routes to `PaymentCancelled` and does *not* set `signingError`; only non-rejection signing failures do.
- **Once connected**, `disconnectWallet(namespace?)` drops one namespace or all of them.

## `usePaymentSession` options

```ts
usePaymentSession({
  paymentId,
  seams,               // { transport, clock, signer?, telemetry? }
  wallet,              // the WalletProvider seam
  initialPayment,      // optional: skip the first fetch if you already have the intent
  signingTimeoutMs,    // optional
  onMachineEvent       // optional: read-only analytics observer (event, snapshot)
})
```

The return is `{ snapshot }` plus the named actions from the main SKILL table. There is no `send` or actor on the surface.
