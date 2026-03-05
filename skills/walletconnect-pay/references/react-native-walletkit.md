# React Native — WalletKit Integration

> **Recommended** if your wallet already uses `@reown/walletkit`.
> Pay functionality is included in the WalletKit package.

## Requirements

- Node.js 16+
- `@reown/walletkit`
- `@walletconnect/core`
- `react-native-webview@13.16.0` (for data collection)

## Installation

```bash
npm install @reown/walletkit @walletconnect/core react-native-webview@13.16.0
# or
pnpm add @reown/walletkit @walletconnect/core react-native-webview@13.16.0
```

## Initialization

```js
import { Core } from "@walletconnect/core";
import { WalletKit } from "@reown/walletkit";

const core = new Core({ projectId: process.env.PROJECT_ID });

const walletkit = await WalletKit.init({
  core,
  metadata: {
    name: "My Wallet",
    description: "My crypto wallet",
    url: "https://mywallet.com",
    icons: ["https://mywallet.com/icon.png"],
  },
});
// walletkit.pay is the Pay client
```

## Payment Link Detection

```js
import { isPaymentLink } from "@reown/walletkit";

async function handleUri(uri) {
  if (isPaymentLink(uri)) {
    await processPayment(uri);
  } else {
    await walletkit.pair({ uri });
  }
}
```

## Get Payment Options

```js
const options = await walletkit.pay.getPaymentOptions({
  paymentLink: uri,
  accounts: [
    "eip155:1:0xYourAddress",
    "eip155:8453:0xYourAddress",
    "eip155:10:0xYourAddress",
    "eip155:137:0xYourAddress",
    "eip155:42161:0xYourAddress",
  ],
  includePaymentInfo: true,
});

// options.paymentId  — use in all subsequent calls
// options.options[]  — available payment methods
// options.info?      — merchant details, expiresAt
// options.collectData? — global data collection (check per-option too)
```

## Get Required Actions

```js
const actions = await walletkit.pay.getRequiredPaymentActions({
  paymentId: options.paymentId,
  optionId: selectedOption.id,
});
// actions[i].walletRpc: { chainId, method, params }
```

## Signing (EIP-712)

```js
// Sign all actions in order — signature[i] must match actions[i]
const signatures = await Promise.all(
  actions.map(async (action) => {
    const { chainId, method, params } = action.walletRpc;
    const parsedParams = JSON.parse(params);
    // parsedParams[0] = address, parsedParams[1] = typed data
    return await wallet.signTypedData(chainId, parsedParams);
  })
);
```

## Data Collection WebView

```jsx
import { WebView } from "react-native-webview";

function DataCollectionScreen({ collectDataUrl, onComplete, onError }) {
  // Build prefill URL with known user data
  const prefillData = { fullName: "John Doe", dob: "1990-01-15" };
  const base64 = btoa(JSON.stringify(prefillData));
  const separator = collectDataUrl.includes("?") ? "&" : "?";
  const webViewUrl = `${collectDataUrl}${separator}prefill=${base64}`;

  function onMessage(event) {
    try {
      const msg = JSON.parse(event.nativeEvent.data);
      if (msg.type === "IC_COMPLETE") onComplete();
      else if (msg.type === "IC_ERROR") onError(msg.error);
    } catch (_) {}
  }

  return (
    <WebView
      source={{ uri: webViewUrl }}
      onMessage={onMessage}
      javaScriptEnabled
    />
  );
}

// Show only when needed:
if (selectedOption.collectData?.url) {
  showDataCollectionScreen(selectedOption.collectData.url);
}
```

## Confirm Payment

```js
const result = await walletkit.pay.confirmPayment({
  paymentId: options.paymentId,
  optionId: selectedOption.id,
  signatures,
});

// result.status: "processing" | "succeeded" | "failed" | "expired" | "requires_action"
// result.isFinal: boolean
// result.pollInMs?: number  → poll again after delay if not final

async function pollUntilFinal(paymentId, optionId, signatures) {
  let result = await walletkit.pay.confirmPayment({ paymentId, optionId, signatures });
  while (!result.isFinal && result.pollInMs) {
    await new Promise(r => setTimeout(r, result.pollInMs));
    result = await walletkit.pay.confirmPayment({ paymentId, optionId, signatures });
  }
  return result;
}
```

## Full Example

```js
async function handlePaymentLink(uri) {
  try {
    // 1. Get options
    const options = await walletkit.pay.getPaymentOptions({
      paymentLink: uri,
      accounts: getWalletAccounts(), // ["eip155:1:0x...", ...]
      includePaymentInfo: true,
    });

    if (!options.options.length) throw new Error("No payment options available");
    const selectedOption = options.options[0];

    // 2. Data collection (if required)
    if (selectedOption.collectData?.url) {
      await showDataCollectionWebView(selectedOption.collectData.url);
    }

    // 3. Get and sign actions
    const actions = await walletkit.pay.getRequiredPaymentActions({
      paymentId: options.paymentId,
      optionId: selectedOption.id,
    });
    const signatures = await Promise.all(
      actions.map(a => wallet.signTypedData(a.walletRpc.chainId, JSON.parse(a.walletRpc.params)))
    );

    // 4. Confirm
    const result = await pollUntilFinal(options.paymentId, selectedOption.id, signatures);
    if (result.status === "succeeded") showSuccess();
    else showError(result.status);

  } catch (err) {
    if (err.message?.includes("expired")) showError("Payment expired");
    else if (err.message?.includes("not found")) showError("Payment not found");
    else showError("Payment failed");
  }
}
```
