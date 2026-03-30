# Next.js Integration

> Use this when building a web dashboard or server-side application with Next.js App Router that creates payments and tracks their status.

## When to Choose Next.js

- Building a merchant dashboard with payment creation UI
- Need server-side API routes to keep API keys secure
- Want client-side polling with live status updates
- Integrating with messaging (WhatsApp, email) to send payment links

## Requirements

- Next.js 14+ with App Router
- Node.js 18+
- TypeScript recommended

## Installation

```bash
npm install qrcode @types/qrcode
```

No dedicated SDK is needed — the Merchant API is a standard REST API called from Next.js API routes.

---

## Environment Variables

```env
WALLETCONNECT_API_URL=<api-base-url>
WALLETCONNECT_MERCHANT_ID=<your-merchant-id>
WALLETCONNECT_CUSTOMER_API_KEY=<your-customer-api-key>
```

All keys are server-side only (no `NEXT_PUBLIC_` prefix) — they are never exposed to the browser.

---

## Server-Side Payment Client

Create a shared module for WalletConnect API calls:

```typescript
// src/lib/walletconnect.ts

const API_URL = process.env.WALLETCONNECT_API_URL!;
const MERCHANT_ID = process.env.WALLETCONNECT_MERCHANT_ID!;
const CUSTOMER_API_KEY = process.env.WALLETCONNECT_CUSTOMER_API_KEY!;

function paymentHeaders(): Record<string, string> {
  return {
    "Content-Type": "application/json",
    "Api-Key": CUSTOMER_API_KEY,
    "Merchant-Id": MERCHANT_ID,
  };
}

export async function createPayment(referenceId: string, amountCents: string) {
  const res = await fetch(`${API_URL}/merchant/payment`, {
    method: "POST",
    headers: paymentHeaders(),
    body: JSON.stringify({
      referenceId,
      amount: { value: amountCents, unit: "iso4217/USD" },
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || `Payment creation failed: ${res.status}`);
  }

  return res.json(); // { paymentId, gatewayUrl, expiresAt }
}

export async function getPaymentStatus(paymentId: string) {
  const res = await fetch(`${API_URL}/merchant/payment/${paymentId}/status`, {
    headers: paymentHeaders(),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || `Status check failed: ${res.status}`);
  }

  return res.json(); // { status, isFinal, pollInMs }
}

export async function getTransactions(params?: {
  status?: string;
  sortBy?: string;
  sortDir?: string;
  limit?: number;
  cursor?: string;
  startTs?: string;
  endTs?: string;
}) {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.sortBy) searchParams.set("sortBy", params.sortBy);
  if (params?.sortDir) searchParams.set("sortDir", params.sortDir);
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  if (params?.cursor) searchParams.set("cursor", params.cursor);
  if (params?.startTs) searchParams.set("startTs", params.startTs);
  if (params?.endTs) searchParams.set("endTs", params.endTs);

  const qs = searchParams.toString();
  const url = `${API_URL}/merchants/payments${qs ? `?${qs}` : ""}`;

  const res = await fetch(url, {
    headers: paymentHeaders(),
  });

  const text = await res.text();
  const data = text ? JSON.parse(text) : {};

  if (!res.ok) {
    throw new Error(data.message || `Transactions fetch failed: ${res.status}`);
  }

  return data; // { data: PaymentRecord[], nextCursor }
}
```

---

## API Route: Create Payment

```typescript
// src/app/api/payments/route.ts
import { NextRequest, NextResponse } from "next/server";
import { createPayment } from "@/lib/walletconnect";

export async function POST(req: NextRequest) {
  try {
    const { amountUsd, referenceId } = await req.json();

    if (!amountUsd) {
      return NextResponse.json({ error: "amountUsd is required" }, { status: 400 });
    }

    const cents = Math.round(parseFloat(amountUsd) * 100).toString();
    const refId = referenceId || `order-${Date.now()}`;
    const payment = await createPayment(refId, cents);

    return NextResponse.json(payment);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}
```

---

## API Route: Poll Status

```typescript
// src/app/api/payments/[paymentId]/status/route.ts
import { NextRequest, NextResponse } from "next/server";
import { getPaymentStatus } from "@/lib/walletconnect";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ paymentId: string }> }
) {
  try {
    const { paymentId } = await params;
    const status = await getPaymentStatus(paymentId);
    return NextResponse.json(status);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}
```

---

## Client-Side Polling Hook

```typescript
// src/hooks/usePaymentStatus.ts
"use client";
import { useEffect, useRef, useState } from "react";

export function usePaymentStatus(paymentId: string | null) {
  const [status, setStatus] = useState<string>("requires_action");
  const [isFinal, setIsFinal] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    if (!paymentId || isFinal) return;

    async function poll() {
      try {
        const res = await fetch(`/api/payments/${paymentId}/status`);
        const data = await res.json();
        setStatus(data.status);
        setIsFinal(data.isFinal);

        if (!data.isFinal) {
          timeoutRef.current = setTimeout(poll, data.pollInMs || 3000);
        }
      } catch {
        timeoutRef.current = setTimeout(poll, 5000);
      }
    }

    timeoutRef.current = setTimeout(poll, 2000);
    return () => { if (timeoutRef.current) clearTimeout(timeoutRef.current); };
  }, [paymentId, isFinal]);

  return { status, isFinal };
}
```

---

## QR Code Generation

Generate a QR code PNG from the `gatewayUrl`:

```typescript
// src/lib/qr.ts
import QRCode from "qrcode";

export async function generateQRBuffer(url: string): Promise<Buffer> {
  return QRCode.toBuffer(url, {
    type: "png",
    width: 512,
    margin: 2,
  });
}
```

For client-side rendering as a data URL:

```typescript
import QRCode from "qrcode";

const dataUrl = await QRCode.toDataURL(gatewayUrl, { width: 256 });
// Use in <img src={dataUrl} />
```

---

## Complete Example: Payment Page

```tsx
"use client";
import { useState } from "react";
import { usePaymentStatus } from "@/hooks/usePaymentStatus";

export default function PaymentPage() {
  const [amount, setAmount] = useState("");
  const [paymentId, setPaymentId] = useState<string | null>(null);
  const [gatewayUrl, setGatewayUrl] = useState("");
  const { status, isFinal } = usePaymentStatus(paymentId);

  async function createPayment() {
    const res = await fetch("/api/payments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amountUsd: amount }),
    });
    const data = await res.json();
    setPaymentId(data.paymentId);
    setGatewayUrl(data.gatewayUrl);
  }

  return (
    <div>
      {!paymentId ? (
        <form onSubmit={(e) => { e.preventDefault(); createPayment(); }}>
          <input value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="5.00" />
          <button type="submit">Create Payment</button>
        </form>
      ) : (
        <div>
          <p>Status: {status}</p>
          <a href={gatewayUrl} target="_blank">Open Payment Link</a>
          {!isFinal && <p>Waiting for payment...</p>}
          {status === "succeeded" && <p>Payment received!</p>}
        </div>
      )}
    </div>
  );
}
```

---

## Key Patterns

| Pattern | Implementation |
|---------|---------------|
| Keep API keys secure | All WalletConnect calls in API routes (no `NEXT_PUBLIC_` prefix) |
| Client-side status updates | Poll `/api/payments/[id]/status` from React with `useEffect` |
| Amount conversion | `Math.round(dollars * 100).toString()` — avoids floating-point issues |
| QR code delivery | Generate PNG server-side with `qrcode`, serve as buffer or data URL |
| Error handling | Wrap API calls in try/catch, return structured error responses |
