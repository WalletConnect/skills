# Merchant Payment API Reference

> Complete REST API reference for creating payments, polling status, and fetching transaction history.

## Authentication

Two authentication modes:

| Endpoint group | Headers |
|---------------|---------|
| Payment creation & status | `Api-Key`, `Merchant-Id`, `WCP-Version` |
| Transaction history | `x-api-key` |

---

## Endpoint 1 — Create Payment

**`POST /merchant/payment`**

Creates a new payment and returns a gateway URL for the customer.

### Request headers

```
Content-Type: application/json
Api-Key: <CUSTOMER_API_KEY>
Merchant-Id: <MERCHANT_ID>
WCP-Version: 2026-02-19.preview
Sdk-Name: <optional-app-name>
Sdk-Version: <optional-version>
Sdk-Platform: <optional-platform>
```

### Request body

```json
{
  "referenceId": "order-12345",
  "amount": {
    "value": "500",
    "unit": "iso4217/USD"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `referenceId` | string | Yes | Your unique identifier for this payment |
| `amount.value` | string | Yes | Amount in **cents** (e.g., `"500"` = $5.00) |
| `amount.unit` | string | Yes | `"iso4217/USD"` (ISO 4217 currency code) |

### Response

```json
{
  "paymentId": "pay_abc123def456",
  "gatewayUrl": "https://pay.walletconnect.com/?pid=pay_abc123def456",
  "expiresAt": 1711234567
}
```

| Field | Type | Description |
|-------|------|-------------|
| `paymentId` | string | Use for status polling and confirmation |
| `gatewayUrl` | string | Customer opens this to pay; also use for QR code generation |
| `expiresAt` | number \| null | Unix timestamp (seconds) when payment expires |

---

## Endpoint 2 — Get Payment Status

**`GET /merchant/payment/{paymentId}/status`**

Poll this endpoint to track payment progress.

### Request headers

Same as Create Payment (`Api-Key`, `Merchant-Id`, `WCP-Version`).

### Response

```json
{
  "status": "processing",
  "isFinal": false,
  "pollInMs": 3000
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Current payment status (see table below) |
| `isFinal` | boolean | `true` when payment reached terminal state |
| `pollInMs` | number | Suggested delay before next poll (milliseconds) |

### Payment statuses

| Status | Meaning | isFinal |
|--------|---------|---------|
| `requires_action` | Created, waiting for customer to open link and pay | `false` |
| `processing` | Customer submitted payment, awaiting blockchain confirmation | `false` |
| `succeeded` | Payment confirmed and settled | `true` |
| `failed` | Payment failed (insufficient funds, rejected, etc.) | `true` |
| `expired` | Payment timed out before customer completed | `true` |
| `cancelled` | Payment was explicitly cancelled | `true` |

### Polling pattern

```typescript
async function waitForPayment(paymentId: string): Promise<string> {
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

---

## Endpoint 3 — Cancel Payment

**`POST /payments/{paymentId}/cancel`**

Cancel a payment that is in `requires_action` state. Returns `400` if payment is in any other state.

### Request headers

Same as Create Payment.

### Request body

Empty object `{}`.

### Response

`200 OK` on success.

---

## Endpoint 4 — List Transactions

**`GET /merchants/{merchantId}/payments`**

Fetch historical payment records. Uses a different API key.

### Request headers

```
Content-Type: application/json
x-api-key: <MERCHANT_PORTAL_API_KEY>
```

### Query parameters

| Param | Type | Description |
|-------|------|-------------|
| `status` | string | Filter by status (repeat for multiple values) |
| `sort_by` | string | `"date"` or `"amount"` |
| `sort_dir` | string | `"asc"` or `"desc"` |
| `limit` | number | Max results per page |
| `cursor` | string | Pagination cursor from previous response |

### Response

```json
{
  "data": [
    {
      "payment_id": "pay_abc123",
      "reference_id": "order-12345",
      "status": "succeeded",
      "merchant_id": "merchant_xyz",
      "is_terminal": true,
      "wallet_name": "MetaMask",
      "tx_hash": "0xabc...",
      "fiat_amount": 500,
      "fiat_currency": "iso4217/USD",
      "token_amount": "500000",
      "token_caip19": "eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
      "chain_id": "eip155:8453",
      "buyer_caip10": "eip155:8453:0xBuyerAddress",
      "created_at": "2026-03-25T10:30:00Z",
      "confirmed_at": "2026-03-25T10:30:15Z"
    }
  ],
  "next_cursor": "cursor_abc123"
}
```

### Transaction record fields

| Field | Type | Description |
|-------|------|-------------|
| `payment_id` | string | Payment identifier |
| `reference_id` | string | Your reference ID from creation |
| `status` | string | Final payment status |
| `merchant_id` | string | Your merchant ID |
| `is_terminal` | boolean | Whether status is final |
| `wallet_name` | string | Name of wallet used |
| `tx_hash` | string | Blockchain transaction hash |
| `fiat_amount` | number | Amount in cents |
| `fiat_currency` | string | ISO 4217 currency (`"iso4217/USD"`) |
| `token_amount` | string | Raw token amount (USDC has 6 decimals: `"500000"` = 0.50 USDC) |
| `token_caip19` | string | Token in CAIP-19 format: `eip155:{chainId}/erc20:{address}` |
| `chain_id` | string | Blockchain identifier |
| `buyer_caip10` | string | Buyer address in CAIP-10 format |
| `created_at` | string | ISO 8601 creation timestamp |
| `confirmed_at` | string | ISO 8601 confirmation timestamp |

---

## Error Responses

All errors return JSON with a `message` field:

```json
{
  "message": "Merchant ID is not configured",
  "code": "INVALID_MERCHANT",
  "status": 400
}
```

| HTTP Status | Common cause | Fix |
|-------------|-------------|-----|
| 400 | Invalid request body (bad amount, missing fields) | Check `amount.value` is cents string |
| 401 | Missing or invalid API key | Verify `Api-Key` header |
| 403 | Wrong API key for endpoint | Use `x-api-key` for transaction history |
| 404 | Payment not found | Check `paymentId` is correct |
| 408 | Request timeout | Retry with exponential backoff |

---

## Amount Formatting

Amounts are always in **cents** as a **string**:

| Dollar amount | `amount.value` |
|--------------|----------------|
| $1.00 | `"100"` |
| $5.00 | `"500"` |
| $10.50 | `"1050"` |
| $0.01 | `"1"` |

Convert from dollars: `Math.round(dollars * 100).toString()`

---

## CAIP Format Reference

**CAIP-10** (account): `eip155:{chainId}:{address}`
**CAIP-19** (token): `eip155:{chainId}/erc20:{contractAddress}`

### USDC contract addresses

| Network | Chain ID | USDC Address |
|---------|----------|-------------|
| Ethereum | 1 | `0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48` |
| Base | 8453 | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Optimism | 10 | `0x0b2c639c533813f4aa9d7837caf62653d097ff85` |
| Polygon | 137 | `0x3c499c542cef5e3811e1192ce70d8cc03d5c3359` |
| Arbitrum | 42161 | `0xaf88d065e77c8cc2239327c5edb3a432268e5831` |
