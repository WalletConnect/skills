# Server Proxy — keep the Engine API key server-side

> The five-method contract below is stable; the example code is a durable *shape*, not a spec. For the complete, current walkthrough see the [implementation docs](https://docs.walletconnect.com/payments/psps/headless-sdk/implementation).

The WalletConnect Pay Engine is authenticated with a **secret API key that must never reach the browser**. So the one piece of backend every integration needs is a thin proxy: the browser calls *your* server, and your server calls the Engine with the key attached.

```
Browser (createHttpTransport, no key) → your proxy → createEngineClient (holds key) → WC Pay Engine
```

pay-core gives you both halves:

- **Server:** `@walletconnect/pay-core/server` → `createEngineClient({ apiUrl, apiKey })`. Pair it with `'server-only'` so it can never be bundled into client code.
- **Browser:** `@walletconnect/pay-core` → `createHttpTransport({ baseUrl })`. No key; it just calls your proxy.

## The contract: five Engine calls

`createEngineClient` and the browser `Transport` expose the **same five methods**. Your proxy's only job is to forward each one:

| Engine client method | Purpose |
| --- | --- |
| `getPayment(id)` | Load the payment intent |
| `getPaymentOptions(id, body)` | List payable options for the connected accounts |
| `fetchOptionActions(id, body)` | Build the wallet-RPC actions for a selected option |
| `confirmPayment(id, body)` | Submit signed results |
| `getPaymentStatus(id)` | Poll status until final |

**How you expose these is up to you** — Next.js Route Handlers, Express, Hono, Fastify, a Cloudflare Worker, an edge function, one catch-all route or five files. The only requirement: the browser transport must be able to reach them, and you point it there with `baseUrl`.

## How the default transport addresses your proxy

`createHttpTransport({ baseUrl })` issues requests to these paths, so the simplest proxy mirrors them one-to-one:

| Transport request | → Engine client call |
| --- | --- |
| `GET  {baseUrl}/payment/:id` | `getPayment(id)` |
| `POST {baseUrl}/payment/:id/options` | `getPaymentOptions(id, body)` |
| `POST {baseUrl}/payment/:id/fetch` | `fetchOptionActions(id, body)` |
| `POST {baseUrl}/payment/:id/confirm` | `confirmPayment(id, body)` |
| `GET  {baseUrl}/payment/:id/status` | `getPaymentStatus(id)` |

If your framework routes differently, you can supply a custom `fetch` to `createHttpTransport` and map paths yourself — but mirroring is the least work.

## Example — the shared Engine client

Construct the client once, server-side. `'server-only'` is what guarantees this module can't leak into the browser bundle.

```ts
// server/engine.ts
import 'server-only'
import { createEngineClient } from '@walletconnect/pay-core/server'

export const engine = createEngineClient({
  apiUrl: process.env.WCP_API_URL ?? 'https://staging.api.pay.walletconnect.org',
  apiKey: process.env.WCP_WALLET_API_KEY ?? '' // server env only — never a NEXT_PUBLIC_/VITE_ var
})
```

Each client method returns the Engine's `EngineResponse<T>` envelope (`{ status: 'success', data }` or `{ status: 'error', error }`) and never throws, so a handler can pass the result straight back as JSON.

## Example — Next.js Route Handlers

One thin handler per Engine method — each just calls the matching client method. No central dispatcher needed.

```ts
// app/api/wcp/payment/[id]/route.ts        → getPayment
import { engine } from '@/server/engine'
export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return Response.json(await engine.getPayment(id))
}
```

```ts
// app/api/wcp/payment/[id]/options/route.ts → getPaymentOptions
import { engine } from '@/server/engine'
export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return Response.json(await engine.getPaymentOptions(id, await req.json()))
}
```

`fetch` and `confirm` mirror `options` (POST + body → `fetchOptionActions` / `confirmPayment`); `status` mirrors the base route (GET → `getPaymentStatus`). Then point the browser at it:

```ts
import { createHttpTransport } from '@walletconnect/pay-core'
const transport = createHttpTransport({ baseUrl: '/api/wcp' })
```

## Example — any Node server (no framework)

The same idea without a framework — read `method` + path segments, call the matching method:

```js
import { createServer } from 'node:http'
import { engine } from './engine.mjs'

const handlers = {
  'GET payment/:id':          (id) => engine.getPayment(id),
  'GET payment/:id/status':   (id) => engine.getPaymentStatus(id),
  'POST payment/:id/options': (id, body) => engine.getPaymentOptions(id, body),
  'POST payment/:id/confirm': (id, body) => engine.confirmPayment(id, body),
  'POST payment/:id/fetch':   (id, body) => engine.fetchOptionActions(id, body)
}
// ...match req.method + path against the keys, call the handler, JSON-respond.
```

## Production notes

- These examples are a **starting point, not production-ready**. Add your own origin allowlist, rate limiting, and auth before shipping.
- Never leak stack traces to the client on error — return a generic `{ status: 'error' }`.

## Environment variables

```bash
# Reown AppKit project ID — PUBLIC (client-side). Required for wallet connection / QR pairing.
NEXT_PUBLIC_APPKIT_PROJECT_ID=      # Next.js       (or VITE_APPKIT_PROJECT_ID= for Vite)

# WalletConnect Pay Engine — SERVER-SIDE ONLY, never exposed to the browser.
WCP_API_URL=https://staging.api.pay.walletconnect.org
WCP_WALLET_API_KEY=
```

Only the AppKit project ID is public. `WCP_WALLET_API_KEY` staying server-side is the entire reason the proxy exists.
