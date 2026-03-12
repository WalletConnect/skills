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
https://api.pay.walletconnect.org
```

## Payment Link Validation

QR codes encode a URL with the payment ID in the `pid` query parameter:
```
https://pay.walletconnect.com/?pid=pay_abc123
```

Extract the payment ID:
```typescript
const url = new URL(scannedData);
const paymentId = url.searchParams.get("pid"); // "pay_abc123"
```

Also accept:
- Domain must be `pay.walletconnect.com` or a subdomain
- Path contains `pay_` prefix OR query contains `pid=` OR hostname starts with `pay.`

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
      "id": "c8f17780-267f-4ea6-bec1-8d143ca68a4c",
      "account": "eip155:8453:0xYourAddress",
      "amount": {
        "value": "100000",
        "unit": "caip19/eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "display": {
          "assetSymbol": "USDC",
          "assetName": "USD Coin",
          "decimals": 6,
          "networkName": "Base",
          "iconUrl": "https://api.walletconnect.com/assets/v1/image/token/USDC/md",
          "networkIconUrl": "https://api.walletconnect.com/assets/v1/image/network/eip155:8453/md"
        }
      },
      "etaS": 5,
      "expiresAt": null,
      "actions": [
        {
          "type": "build",
          "data": {
            "data": "7b22636861696e5f6964223a226569703135353a38343533222c..."
          }
        }
      ],
      "collectData": {
        "fields": [
          { "type": "text", "id": "fullName", "name": "Full name", "required": true },
          { "type": "date", "id": "dob", "name": "Date of birth", "required": true }
        ],
        "schema": { "...JSON Schema..." },
        "url": "https://pay.walletconnect.com/collect/?pid=pay_abc123&accounts=..."
      }
    }
  ],
  "info": null,
  "collectData": { "...same structure as per-option..." }
}
```

**Notes:**
- `info` can be `null` even with `includePaymentInfo: true`
- `amount.unit` uses CAIP-19 format, not ISO 4217
- `amount.display` includes `assetName`, `decimals`, `iconUrl`, `networkIconUrl` in addition to `assetSymbol` and `networkName`
- `expiresAt` is present on each option (can be `null`)
- `collectData` appears both at top-level and per-option

**Action types:**
- `walletRpc` → ready to sign immediately
- `build` → contains hex-encoded walletRpc data (see below)

### Decoding `build` actions

A `build` action contains a `data.data` field that is a **hex-encoded JSON string**. Decode it to get the walletRpc action:

```typescript
const hex = action.data.data;
const json = Buffer.from(hex, "hex").toString("utf8");
const walletRpc = JSON.parse(json);
// {
//   "chain_id": "eip155:8453",
//   "method": "eth_signTypedData_v4",
//   "params": ["0xAddress", "{...EIP-712 typed data...}"]
// }
```

Note: the decoded action uses `chain_id` (snake_case), not `chainId`.

---

## Endpoint 2 — Fetch an Action (Build → WalletRpc)

**`POST /v1/gateway/payment/{id}/fetch`**

Only needed when an option's action type is `"build"` and you prefer server-side resolution instead of decoding the hex client-side.

Request:
```json
{
  "optionId": "c8f17780-267f-4ea6-bec1-8d143ca68a4c",
  "data": "7b22636861696e5f6964223a226569703135353a38343533222c..."
}
```

**Important:** The `data` field is **required** and must be the hex string from `action.data.data`. It must be a string, not an object.

Response: returns `walletRpc` action ready for signing.

---

## Endpoint 3 — Confirm Payment

**`POST /v1/gateway/payment/{id}/confirm`**

Request:
```json
{
  "optionId": "c8f17780-267f-4ea6-bec1-8d143ca68a4c",
  "results": [
    {
      "type": "walletRpc",
      "data": ["0x<signature_hex>"]
    }
  ],
  "collectedData": {
    "fullName": "John Doe",
    "dob": "1990-01-15",
    "tosConfirmed": true,
    "porCountry": "US",
    "porAddress": "123 Main St, New York, NY"
  }
}
```

- `results` order must match `actions` order exactly
- `collectedData` is `null` when no compliance data is required, or when WebView handled data collection

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

## Data Collection (Compliance)

When `collectData` is present on an option, compliance data must be collected before confirming.

### Option A: Native form using fields and schema

The response includes structured `fields` and a JSON Schema:

```json
{
  "fields": [
    { "type": "text", "id": "fullName", "name": "Full name", "required": true },
    { "type": "date", "id": "dob", "name": "Date of birth", "required": true }
  ],
  "schema": {
    "required": ["fullName", "dob", "tosConfirmed"],
    "properties": {
      "fullName": { "type": "string", "minLength": 1 },
      "dob": { "type": "string", "format": "date" },
      "tosConfirmed": { "const": true, "type": "boolean" },
      "porCountry": { "type": "string", "pattern": "^[A-Z]{2}$" },
      "porAddress": { "type": "string", "maxLength": 200 },
      "pobCountry": { "type": "string", "pattern": "^[A-Z]{2}$" },
      "pobAddress": { "type": "string", "maxLength": 200 }
    },
    "anyOf": [
      { "required": ["pobCountry", "pobAddress"] },
      { "required": ["porCountry", "porAddress"] }
    ]
  }
}
```

Build a native form, collect the data, and pass it as `collectedData` in the confirm request. Always include `"tosConfirmed": true`.

### Option B: WebView

Open `collectData.url` in an in-app WebView. Listen for postMessage events:

```
{ "type": "IC_COMPLETE" }  → user completed data entry, proceed to confirm
{ "type": "IC_ERROR", "error": "..." }  → show error
```

Prefill known user data by appending `?prefill=<base64(JSON)>` to the URL.

When using the WebView, pass `"collectedData": null` in the confirm request.

---

## Full Integration Flow

```
1. Scan QR code, extract `pid` query parameter
2. POST /v1/gateway/payment/{pid}/options
   Body: { accounts: [CAIP-10 addresses], includePaymentInfo: true }
3. Pick an option (e.g. first with sufficient balance)
4. For each action in option.actions:
   - If type === "build": decode action.data.data from hex to JSON
     (contains { chain_id, method, params })
   - If type === "walletRpc": use action.data directly
5. If option.collectData exists:
   - Build native form from collectData.fields/schema, OR
   - Open collectData.url in WebView → await IC_COMPLETE
6. Sign params[1] (EIP-712 typed data) with wallet private key
7. POST /v1/gateway/payment/{pid}/confirm
   Body: { optionId, results: [{ type: "walletRpc", data: ["0xsig"] }], collectedData }
8. Poll confirm until isFinal === true
9. Handle final status (succeeded/failed/expired)
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
| `params_validation` | Request body validation failed (check field types) |

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
