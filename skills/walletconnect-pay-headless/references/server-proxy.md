# Server Proxy — keep the Engine API key server-side

The WalletConnect Pay Engine is authenticated with a **secret API key that must never reach the browser**. The Headless SDK enforces this with two entry points in `@walletconnect/pay-core`:

- **Browser:** `@walletconnect/pay-core` → `createHttpTransport()` (no key; calls *your* origin).
- **Server:** `@walletconnect/pay-core/server` → `createEngineClient({ apiUrl, apiKey })` (holds the key).

The data path is:

```
Browser → createHttpTransport (Transport seam) → your /api/wcp/* routes → createEngineClient → WC Pay Engine
                                                   (secret API key attached here, server-side)
```

Your proxy has exactly one job: forward five calls to the Engine with the key attached. The browser transport issues requests to `${baseUrl}/payment/:id/...`, so your routes must mount at those paths.

> These proxy routes are a **starting point, not production-ready**. Add your own origin allowlist, rate limiting, and auth before shipping. Their only job here is to keep the Engine key off the browser.

## The five routes

| Route (browser sees) | Method | Engine client method | Engine path |
| --- | --- | --- | --- |
| `/api/wcp/payment/[id]` | `GET` | `getPayment(id)` | `/v1/gateway/payment/:id` |
| `/api/wcp/payment/[id]/options` | `POST` | `getPaymentOptions(id, body)` | `/v1/gateway/payment/:id/options` |
| `/api/wcp/payment/[id]/fetch` | `POST` | `fetchOptionActions(id, body)` | `/v1/gateway/payment/:id/fetch` |
| `/api/wcp/payment/[id]/confirm` | `POST` | `confirmPayment(id, body)` | `/v1/gateway/payment/:id/confirm` |
| `/api/wcp/payment/[id]/status` | `GET` | `getPaymentStatus(id)` | `/v1/gateway/payment/:id/status` |

## Next.js — server Engine helper

`lib/server/engine.ts` — the `'server-only'` import is what guarantees this module can never be bundled into client code.

```ts
import 'server-only'
import { createEngineClient } from '@walletconnect/pay-core/server'

// The gateway API key lives here (server env) and NEVER reaches the browser.
const client = createEngineClient({
  apiUrl: process.env.WCP_API_URL ?? 'https://staging.api.pay.walletconnect.org',
  apiKey: process.env.WCP_WALLET_API_KEY ?? ''
})

/** Forward a call to the Engine and return an EngineResponse-shaped Response. */
export async function callEngine(
  path: string,
  init: { method: 'GET' | 'POST'; body?: unknown }
): Promise<Response> {
  const paymentId = path.split('/')[4] // /v1/gateway/payment/:id[/action]
  let result

  if (path.endsWith('/options')) {
    result = await client.getPaymentOptions(paymentId!, init.body as any)
  } else if (path.endsWith('/status')) {
    result = await client.getPaymentStatus(paymentId!)
  } else if (path.endsWith('/confirm')) {
    result = await client.confirmPayment(paymentId!, init.body as any)
  } else if (path.endsWith('/fetch')) {
    result = await client.fetchOptionActions(paymentId!, init.body as any)
  } else if (path.startsWith('/v1/gateway/payment/')) {
    result = await client.getPayment(paymentId!)
  } else {
    return Response.json({
      status: 'error',
      error: { code: 'INVALID_PATH', message: `Unknown path: ${path}` }
    })
  }

  return Response.json(result)
}
```

The Engine client methods return the `EngineResponse<T>` envelope (`{ status: 'success', data }` or `{ status: 'error', error }`) — they never throw — so you can pass the result straight back as JSON.

## Next.js — the five route handlers (App Router)

Each handler is a thin wrapper. Note `params` is a `Promise` in the App Router.

`app/api/wcp/payment/[id]/route.ts`
```ts
import { callEngine } from '@/lib/server/engine'

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return callEngine(`/v1/gateway/payment/${id}`, { method: 'GET' })
}
```

`app/api/wcp/payment/[id]/options/route.ts`
```ts
import { callEngine } from '@/lib/server/engine'

export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const body = await req.json()
  return callEngine(`/v1/gateway/payment/${id}/options`, { method: 'POST', body })
}
```

`app/api/wcp/payment/[id]/fetch/route.ts` and `.../confirm/route.ts` are identical to `options` (POST + `body`), with `/fetch` and `/confirm` in the path. `app/api/wcp/payment/[id]/status/route.ts` mirrors the base route (GET, no body) with `/status` in the path.

## Framework-neutral — any Node server

The proxy is just a request router. A dependency-free Node `http` server:

```js
import { createServer } from 'node:http'
import { createEngineClient } from '@walletconnect/pay-core/server'

const client = createEngineClient({
  apiUrl: process.env.WCP_API_URL ?? 'https://staging.api.pay.walletconnect.org',
  apiKey: process.env.WCP_WALLET_API_KEY ?? ''
})

// Map an incoming proxy request → the matching Engine client call.
async function dispatch(method, segments, body) {
  const [resource, id, action] = segments // e.g. ['payment', 'pay_123', 'options']
  if (resource !== 'payment' || !id) return null
  if (method === 'GET'  && !action)              return client.getPayment(id)
  if (method === 'GET'  && action === 'status')  return client.getPaymentStatus(id)
  if (method === 'POST' && action === 'options') return client.getPaymentOptions(id, body)
  if (method === 'POST' && action === 'confirm') return client.confirmPayment(id, body)
  if (method === 'POST' && action === 'fetch')   return client.fetchOptionActions(id, body)
  return null
}

createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://localhost')
    const segments = url.pathname.replace(/^\/api\/wcp\//, '').split('/').filter(Boolean)
    const body = req.method === 'POST' ? await readJson(req) : undefined
    const result = await dispatch(req.method, segments, body)
    res.setHeader('content-type', 'application/json')
    if (!result) { res.statusCode = 404; res.end(JSON.stringify({ status: 'error' })); return }
    res.end(JSON.stringify(result))
  } catch {
    // Never leak the stack.
    res.statusCode = 500
    res.end(JSON.stringify({ status: 'error', error: { code: 'PROXY_ERROR', message: 'Proxy error' } }))
  }
}).listen(Number(process.env.PORT ?? 8787))
```

Any framework works — Express, Hono, Fastify, a Cloudflare Worker, an edge function — as long as it exposes the five paths and forwards to `createEngineClient`.

## Environment variables

```bash
# Reown AppKit project ID — required for wallet connection / QR pairing (PUBLIC / client-side)
NEXT_PUBLIC_APPKIT_PROJECT_ID=      # Next.js
# VITE_APPKIT_PROJECT_ID=           # Vite

# WalletConnect Pay Engine — SERVER-SIDE ONLY, never exposed to the browser
WCP_API_URL=https://staging.api.pay.walletconnect.org
WCP_WALLET_API_KEY=
```

Only the AppKit project ID is public. `WCP_WALLET_API_KEY` must stay server-side — that is the entire reason the proxy exists.
