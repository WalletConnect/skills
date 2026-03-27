---
name: walletconnect-pay-merchant
description: Guides developers through creating USDC payment requests using the Reown/WalletConnect Pay Merchant API. Use when creating payments, generating payment links or QR codes, polling payment status, fetching transaction history, or integrating merchant payment acceptance into React Native, Next.js, web, or server-side applications.
---

# WalletConnect Pay — Merchant Integration

## Goal

Help developers create USDC payment requests using the Reown Payment API. The integration enables merchants to generate payment links (and QR codes), send them to customers, poll for payment status, and retrieve transaction history. Customers pay from any WalletConnect-compatible wallet.

## When to use

- Creating USDC payment requests from a server, web app, or React Native app
- Building a mobile POS terminal or payment kiosk with React Native
- Generating payment links or QR codes for customers
- Polling payment status (pending → processing → succeeded)
- Fetching merchant transaction history
- Integrating payment acceptance into a backend, dashboard, bot, or mobile app
- Troubleshooting merchant API authentication or payment creation errors

## When not to use

- Building a wallet that accepts/processes payments (use the [Wallet Pay SDK](../walletconnect-pay/) instead)
- General WalletConnect pairing/session management unrelated to payments

## Supported Assets & Networks

**Assets:** USDC (currently)
**Networks:** Ethereum (`eip155:1`), Base (`eip155:8453`), Optimism (`eip155:10`), Polygon (`eip155:137`), Arbitrum (`eip155:42161`)
**Currency input:** Fiat amount in cents using ISO 4217 (e.g., `iso4217/USD`)

## Choose Your Integration Path

| Path | When to use | Complexity |
|------|-------------|------------|
| **React Native (POS / Mobile)** | Mobile app that creates payments and displays QR codes | Medium |
| **Next.js / Web app** | Dashboard or web UI creates payments via API routes | Low |
| **Server-side API** | Backend creates payments, sends links to customers | Low |
| **WhatsApp / Chat bot** | Bot sends payment links via messaging API | Medium |

Jump to the right reference:
- [React Native Integration](references/react-native-integration.md)
- [Next.js Integration](references/nextjs-integration.md)
- [API Reference (all platforms)](references/api-reference.md)

## Prerequisites

1. **Reown Merchant Account** — obtain credentials from the Reown dashboard
2. **Merchant ID** — identifies your merchant account
3. **Customer API Key** — authenticates payment creation and status requests
4. **Merchant Portal API Key** — authenticates transaction history requests
5. **Node.js 18+** (for server-side or Next.js integrations)

## Universal Payment Flow

Every merchant integration follows these steps:

```
Merchant App
     ↓
1. POST /merchant/payment        → create payment, get gatewayUrl
     ↓
2. Send gatewayUrl to customer   → WhatsApp, email, QR code, link
     ↓
3. Customer opens gatewayUrl     → connects wallet, pays USDC
     ↓
4. GET /merchant/payment/{id}/status  → poll until isFinal === true
     ↓
5. Handle final status           → succeeded / failed / expired
```

### Step 1 — Create a payment

Send a POST request with the amount in cents and a unique reference ID.

```typescript
const response = await fetch(`${API_URL}/merchant/payment`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Api-Key": CUSTOMER_API_KEY,
    "Merchant-Id": MERCHANT_ID,
    "WCP-Version": "2026-02-19.preview",
  },
  body: JSON.stringify({
    referenceId: "order-12345",
    amount: {
      value: "500",        // $5.00 in cents
      unit: "iso4217/USD",
    },
  }),
});

const { paymentId, gatewayUrl, expiresAt } = await response.json();
```

**Request fields:**

| Field | Type | Description |
|-------|------|-------------|
| `referenceId` | string | Your unique identifier for this payment (e.g., order ID) |
| `amount.value` | string | Amount in **cents** (e.g., `"500"` = $5.00) |
| `amount.unit` | string | Currency unit in ISO 4217 format: `"iso4217/USD"` |

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `paymentId` | string | Unique payment identifier for status polling |
| `gatewayUrl` | string | URL the customer opens to pay (also encodes as QR code) |
| `expiresAt` | number \| null | Unix timestamp when the payment expires |

### Step 2 — Send payment link to customer

The `gatewayUrl` is a web link the customer opens to connect their wallet and pay. You can:

- Send it as a clickable link (WhatsApp, email, SMS)
- Generate a QR code image from it
- Display it directly in your UI

```typescript
// Generate QR code (Node.js)
import QRCode from "qrcode";
const qrBuffer = await QRCode.toBuffer(gatewayUrl, { type: "png", width: 512 });
```

### Step 3 — Poll payment status

Poll until `isFinal` is `true`. Use the `pollInMs` hint from the response.

```typescript
async function pollStatus(paymentId: string): Promise<string> {
  while (true) {
    const res = await fetch(`${API_URL}/merchant/payment/${paymentId}/status`, {
      headers: {
        "Api-Key": CUSTOMER_API_KEY,
        "Merchant-Id": MERCHANT_ID,
        "WCP-Version": "2026-02-19.preview",
      },
    });
    const { status, isFinal, pollInMs } = await res.json();
    if (isFinal) return status;
    await new Promise((r) => setTimeout(r, pollInMs || 3000));
  }
}
```

**Status values:**

| Status | Description | isFinal |
|--------|-------------|---------|
| `requires_action` | Payment created, waiting for customer | `false` |
| `processing` | Customer submitted payment, blockchain confirming | `false` |
| `succeeded` | Payment confirmed and settled | `true` |
| `failed` | Payment failed | `true` |
| `expired` | Payment timed out | `true` |
| `cancelled` | Payment was cancelled | `true` |

### Step 4 — Fetch transaction history

Use a separate API key (`Merchant-Portal-Api-Key`) to list past transactions.

```typescript
const res = await fetch(
  `${API_URL}/merchants/${MERCHANT_ID}/payments?limit=50&sort_by=date&sort_dir=desc`,
  {
    headers: {
      "Content-Type": "application/json",
      "x-api-key": MERCHANT_PORTAL_API_KEY,
    },
  }
);
const { data, next_cursor } = await res.json();
```

**Query parameters:**

| Param | Description |
|-------|-------------|
| `status` | Filter by status (can repeat for multiple) |
| `sort_by` | `"date"` or `"amount"` |
| `sort_dir` | `"asc"` or `"desc"` |
| `limit` | Max results per page |
| `cursor` | Pagination cursor from `next_cursor` |

**Transaction record fields:**

| Field | Type | Description |
|-------|------|-------------|
| `payment_id` | string | Payment identifier |
| `reference_id` | string | Your reference ID |
| `status` | string | Payment status |
| `fiat_amount` | number | Amount in cents |
| `fiat_currency` | string | `"iso4217/USD"` |
| `token_amount` | string | Raw token amount (e.g., `"100000"` for 0.10 USDC) |
| `token_caip19` | string | Token identifier in CAIP-19 format |
| `chain_id` | string | Blockchain chain ID |
| `tx_hash` | string | Blockchain transaction hash |
| `wallet_name` | string | Wallet used for payment |
| `buyer_caip10` | string | Buyer's address in CAIP-10 format |
| `created_at` | string | ISO 8601 timestamp |

## Authentication

All payment creation and status requests require these headers:

```
Api-Key: <CUSTOMER_API_KEY>
Merchant-Id: <MERCHANT_ID>
WCP-Version: 2026-02-19.preview
Content-Type: application/json
```

Transaction history uses a different auth:

```
x-api-key: <MERCHANT_PORTAL_API_KEY>
Content-Type: application/json
```

Optional SDK headers (for tracking):

```
Sdk-Name: <your-app-name>
Sdk-Version: <your-version>
Sdk-Platform: web
```

## Validation checklist

- [ ] Amount is in **cents** as a string (e.g., `"500"` for $5.00, not `"5.00"`)
- [ ] `referenceId` is unique per payment (UUID or prefixed timestamp)
- [ ] `WCP-Version` header is set to `2026-02-19.preview`
- [ ] `Api-Key` and `Merchant-Id` headers are set on every payment request
- [ ] Status polling uses `pollInMs` from the response (not hardcoded)
- [ ] All 6 payment statuses are handled in UI
- [ ] `expiresAt` is checked — warn user if payment is about to expire
- [ ] Transaction history uses `x-api-key` (not `Api-Key`)
- [ ] API keys are server-side only — never exposed to browser clients
- [ ] QR codes are generated from `gatewayUrl` (not `paymentId`)

## Common errors

| Error | Cause | Fix |
|-------|-------|-----|
| `401 Unauthorized` | Missing or invalid `Api-Key` | Verify `CUSTOMER_API_KEY` is correct |
| `400 Bad Request` | Invalid amount format | Ensure `amount.value` is a string of cents |
| `Merchant ID not configured` | Empty `Merchant-Id` header | Set `REOWN_MERCHANT_ID` env var |
| Payment stuck in `requires_action` | Customer hasn't opened the link | Resend the `gatewayUrl` or generate a new payment |
| `expired` status | Customer took too long | Create a new payment and resend |
| Transaction history returns `403` | Wrong API key | Use `MERCHANT_PORTAL_API_KEY` for `/merchants/` endpoints |

## Examples

### Example 1 — Create payment and generate QR (Node.js)

```typescript
import QRCode from "qrcode";
import { randomUUID } from "crypto";

async function createPaymentWithQR(amountUsd: number) {
  const cents = Math.round(amountUsd * 100).toString();

  const res = await fetch(`${process.env.REOWN_API_URL}/merchant/payment`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Api-Key": process.env.REOWN_CUSTOMER_API_KEY!,
      "Merchant-Id": process.env.REOWN_MERCHANT_ID!,
      "WCP-Version": "2026-02-19.preview",
    },
    body: JSON.stringify({
      referenceId: randomUUID(),
      amount: { value: cents, unit: "iso4217/USD" },
    }),
  });

  const { paymentId, gatewayUrl } = await res.json();
  const qrPng = await QRCode.toBuffer(gatewayUrl, { type: "png", width: 512 });

  return { paymentId, gatewayUrl, qrPng };
}
```

### Example 2 — Next.js API route (create + poll)

```typescript
// app/api/payments/route.ts
import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const { amount } = await req.json();
  const cents = Math.round(parseFloat(amount) * 100).toString();

  const res = await fetch(`${process.env.REOWN_API_URL}/merchant/payment`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Api-Key": process.env.REOWN_CUSTOMER_API_KEY!,
      "Merchant-Id": process.env.REOWN_MERCHANT_ID!,
      "WCP-Version": "2026-02-19.preview",
    },
    body: JSON.stringify({
      referenceId: `order-${Date.now()}`,
      amount: { value: cents, unit: "iso4217/USD" },
    }),
  });

  return NextResponse.json(await res.json());
}
```

### Example 3 — Send payment via WhatsApp (Kapso SDK)

```typescript
import { WhatsAppClient } from "@kapso/whatsapp-cloud-api";
import QRCode from "qrcode";

async function sendPaymentViaWhatsApp(phoneNumber: string, amountUsd: number) {
  // 1. Create payment
  const cents = Math.round(amountUsd * 100).toString();
  const paymentRes = await fetch(`${API_URL}/merchant/payment`, {
    method: "POST",
    headers: { "Api-Key": API_KEY, "Merchant-Id": MERCHANT_ID, "WCP-Version": "2026-02-19.preview", "Content-Type": "application/json" },
    body: JSON.stringify({ referenceId: `wa-${Date.now()}`, amount: { value: cents, unit: "iso4217/USD" } }),
  });
  const { paymentId, gatewayUrl } = await paymentRes.json();

  // 2. Generate QR and upload to WhatsApp
  const qrBuffer = await QRCode.toBuffer(gatewayUrl, { type: "png", width: 512 });
  // ... upload via media API, then send as image message with caption

  // 3. Poll status
  let status = "requires_action";
  while (status === "requires_action" || status === "processing") {
    await new Promise((r) => setTimeout(r, 3000));
    const statusRes = await fetch(`${API_URL}/merchant/payment/${paymentId}/status`, {
      headers: { "Api-Key": API_KEY, "Merchant-Id": MERCHANT_ID, "WCP-Version": "2026-02-19.preview" },
    });
    const data = await statusRes.json();
    status = data.status;
    if (data.isFinal) break;
  }

  return { paymentId, status };
}
```

## Evaluations

1. **Activation** — "I want to create a USDC payment link from my Node.js backend and send it to a customer."
2. **Activation** — "How do I check the status of a WalletConnect Pay payment?"
3. **Activation** — "I need to generate a QR code for a payment request and send it via WhatsApp."
4. **Non-activation** — "How do I accept a WC Pay payment in my wallet app?" (use Wallet Pay SDK)
5. **Edge case** — "What format should the amount be in?" (Answer: string of cents, e.g., `"500"` for $5.00)
6. **Edge case** — "Why does my transaction history return 403?" (Answer: use `MERCHANT_PORTAL_API_KEY` with `x-api-key` header, not `Api-Key`)
7. **Troubleshooting** — "My payment is stuck in requires_action." (Answer: customer hasn't opened the link yet; resend or create a new payment)
