# API-First Integration

> Use this when you prefer direct Gateway API calls without an SDK dependency.
> Requires an API key — contact the WalletConnect team to obtain access.

## When to Choose API-First

- Your wallet is on a platform without an official SDK
- You need full control over request/response handling
- You're integrating into a custom backend that brokers signing for mobile clients

## Authentication

All requests require:
```
Api-Key: <your-api-key>
Content-Type: application/json
```

Contact WalletConnect to obtain your API key after completing the access request form.

## Base URL

```
https://pay.walletconnect.com
```

## Payment Link Validation

Before calling APIs, validate that the URI is a genuine WC Pay link:
- Domain must be `pay.walletconnect.com` or a subdomain
- Path contains `pay_` prefix OR query contains `pay=` OR hostname starts with `pay.`

Extract the payment `id` from the link (e.g., `pay_abc123` → id is `pay_abc123`).

---

## Endpoint 1 — Get Payment Options

**`POST /v1/gateway/payment/{id}/options`**

Request:
```json
{
  "accounts": [
    "eip155:1:0xYourAddress",
    "eip155:8453:0xYourAddress",
    "eip155:10:0xYourAddress",
    "eip155:137:0xYourAddress",
    "eip155:42161:0xYourAddress"
  ],
  "includePaymentInfo": true
}
```

Response:
```json
{
  "paymentId": "pay_abc123",
  "options": [
    {
      "id": "option_xyz",
      "amount": {
        "value": "1000000",
        "unit": "iso4217/USD",
        "display": {
          "amount": "10.00",
          "assetSymbol": "USDC",
          "networkName": "Base"
        }
      },
      "account": "eip155:8453:0xYourAddress",
      "etaS": 5,
      "actions": [
        {
          "type": "walletRpc",
          "data": {
            "chainId": "eip155:8453",
            "method": "eth_signTypedData_v4",
            "params": "[\"0xYourAddress\", \"{...typed data...}\"]"
          }
        }
      ],
      "collectData": null
    }
  ],
  "info": {
    "merchant": { "name": "Coffee Shop" },
    "amount": { "value": "1000000", "unit": "iso4217/USD" },
    "expiresAt": "2025-01-01T12:05:00Z"
  }
}
```

**Note on `actions` types:**
- `walletRpc` → ready to sign immediately
- `build` → must call the Fetch endpoint first to get the signable action

---

## Endpoint 2 — Fetch an Action (Build → WalletRpc)

**`POST /v1/gateway/payment/{id}/fetch`**

Only needed when an option's action type is `"build"`.

Request:
```json
{
  "optionId": "option_xyz"
}
```

Response: returns `walletRpc` action ready for signing (same shape as above).

---

## Endpoint 3 — Confirm Payment

**`POST /v1/gateway/payment/{id}/confirm`**

Request:
```json
{
  "optionId": "option_xyz",
  "results": [
    {
      "type": "walletRpc",
      "data": ["0x<signature_hex>"]
    }
  ],
  "collectedData": null
}
```

- `results` order must match `actions` order exactly
- `collectedData` is `null` when WebView handled data collection

Response:
```json
{
  "status": "processing",
  "isFinal": false,
  "pollInMs": 2000
}
```

**Status values:** `requires_action` | `processing` | `succeeded` | `failed` | `expired`

---

## Polling Pattern

If `isFinal` is `false`, poll by re-calling confirm after `pollInMs` milliseconds.
For server-side long-polling, add `?maxPollMs=30000` to the confirm URL.

```
POST /v1/gateway/payment/{id}/confirm?maxPollMs=30000
```

The server will hold the connection up to 30 seconds and return when status changes.

---

## Signing

Actions use `eth_signTypedData_v4`:
- `params[0]` = wallet address
- `params[1]` = EIP-712 typed data JSON string

Wrap the signature in the result format:
```json
{ "type": "walletRpc", "data": ["0x<signature>"] }
```

---

## Data Collection WebView

The API response includes `collectData.url` when compliance data is required.
Open this URL in an in-app WebView. Listen for postMessage events:

```
{ "type": "IC_COMPLETE" }  → user completed data entry, proceed to confirm
{ "type": "IC_ERROR", "error": "..." }  → show error
```

Prefill known user data by appending `?prefill=<base64(JSON)>` to the URL.

---

## Full Integration Flow

```
1. Validate payment link, extract payment ID
2. POST /options  → get paymentId, options[], actions[]
3. If action.type === "build":
     POST /fetch → get walletRpc action
4. Sign walletRpc actions (preserve order)
5. If collectData.url exists:
     Show WebView → await IC_COMPLETE
6. POST /confirm { optionId, results, collectedData }
7. Poll /confirm until isFinal === true
8. Handle final status (succeeded/failed/expired)
```

---

## Error Codes

| Code | Meaning |
|------|---------|
| `payment_not_found` | Payment ID doesn't exist or was deleted |
| `payment_expired` | Payment timed out (inform merchant to retry) |
| `invalid_account` | Account not in CAIP-10 format |
| `compliance_failed` | KYC/KYT blocked the payment — do not retry |
| `invalid_signature` | Signature mismatch or wrong order |
| `option_not_found` | Option ID is invalid for this payment |
| `route_expired` | Liquidity route expired — get fresh options |

---

## CAIP-10 Reference

All accounts must use: `eip155:{chainId}:{checksumAddress}`

| Network | chainId |
|---------|---------|
| Ethereum | 1 |
| Base | 8453 |
| Optimism | 10 |
| Polygon | 137 |
| Arbitrum | 42161 |
