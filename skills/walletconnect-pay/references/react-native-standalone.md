# React Native — Standalone Pay SDK

> Use this when your wallet does **not** use WalletConnect WalletKit.
> The Standalone SDK provides all Pay features without the WalletKit dependency.

## Requirements

- React Native 0.70+
- `@walletconnect/react-native-compat` installed and linked

## Installation

```bash
npm install @walletconnect/pay
# or
yarn add @walletconnect/pay
```

Install the required React Native native module:
```bash
npm install @walletconnect/react-native-compat
```

### Architecture

The SDK uses a provider abstraction:
- **NativeProvider**: Uses React Native uniffi module (current)
- **WasmProvider**: Uses WebAssembly module (coming soon for web browsers)

The SDK auto-detects the best available provider.

## Configuration

```js
import { WalletConnectPay } from "@walletconnect/pay";

const client = new WalletConnectPay({
  appId: "your-app-id",
  // OR use apiKey instead:
  // apiKey: "your-api-key",
});
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `appId` | `string` | No* | App ID for authentication |
| `apiKey` | `string` | No* | API key for authentication |
| `clientId` | `string` | No | Client ID for tracking |
| `baseUrl` | `string` | No | Custom API base URL |
| `logger` | `Logger` | No | Custom logger instance |

*At least one of `apiKey` or `appId` must be provided.

## Provider Utilities

```js
import {
  isProviderAvailable,
  detectProviderType,
  isNativeProviderAvailable,
  setNativeModule,
} from "@walletconnect/pay";

// Check if any provider is available
if (isProviderAvailable()) {
  // SDK can be used
}

// Detect which provider type is available
const providerType = detectProviderType(); // 'native' | 'wasm' | null

// Check specifically for native provider
if (isNativeProviderAvailable()) {
  // React Native native module is available
}

// Manually inject native module (if auto-discovery fails)
import { NativeModules } from "react-native";
setNativeModule(NativeModules.RNWalletConnectPay);
```

## Payment Link Detection

The standalone SDK does not include `isPaymentLink()`. Detect payment links by checking:
- Domain is `pay.walletconnect.com` or a subdomain
- URI contains `pay_` prefix in the path, `pay=` query parameter, or `pay.` hostname

```js
function isPaymentLink(uri) {
  try {
    const url = new URL(uri);
    return url.hostname === "pay.walletconnect.com" ||
           url.hostname.endsWith(".pay.walletconnect.com");
  } catch {
    return false;
  }
}
```

## Get Payment Options

```js
const options = await client.getPaymentOptions({
  paymentLink: "https://pay.walletconnect.com/?pid=pay_abc123...",
  accounts: [
    `eip155:1:${walletAddress}`,      // Ethereum Mainnet
    `eip155:137:${walletAddress}`,    // Polygon
    `eip155:8453:${walletAddress}`,   // Base
    `eip155:42161:${walletAddress}`,  // Arbitrum
  ],
  includePaymentInfo: true,
});

// Display merchant info
if (options.info) {
  console.log(`Merchant: ${options.info.merchant.name}`);
  console.log(`Amount: ${options.info.amount.display.assetSymbol} ${options.info.amount.value}`);
}

// Show available options
for (const option of options.options) {
  console.log(`Pay with ${option.amount.display.assetSymbol}`);
  if (option.collectData) {
    console.log(`Option ${option.id} requires info capture`);
  }
}
```

## Get Required Actions

```js
const actions = await client.getRequiredPaymentActions({
  paymentId: options.paymentId,
  optionId: options.options[0].id,
});

for (const action of actions) {
  console.log("Chain:", action.walletRpc.chainId);
  console.log("Method:", action.walletRpc.method);
  console.log("Params:", action.walletRpc.params);
}
```

## Signing

```js
const signatures = await Promise.all(
  actions.map((action) =>
    wallet.signTypedData(
      action.walletRpc.chainId,
      JSON.parse(action.walletRpc.params)
    )
  )
);
// Critical: preserve order — signatures[i] must correspond to actions[i]
```

## Data Collection WebView

```js
// Check per-option
if (selectedOption.collectData?.url) {
  // Optional: prefill known user data
  const prefillData = { fullName: "John Doe", dob: "1990-01-15" };
  const base64 = btoa(JSON.stringify(prefillData));
  const separator = selectedOption.collectData.url.includes("?") ? "&" : "?";
  const url = `${selectedOption.collectData.url}${separator}prefill=${base64}`;

  // Show WebView — listen for IC_COMPLETE / IC_ERROR
}
```

### WebView Implementation

Install the dependency:
```bash
npm install react-native-webview@13.16.0
```

```tsx
import React, { useCallback } from "react";
import { WebView, WebViewMessageEvent } from "react-native-webview";
import { Linking, View, ActivityIndicator } from "react-native";

interface PayDataCollectionWebViewProps {
  url: string;
  onComplete: () => void;
  onError: (error: string) => void;
}

function PayDataCollectionWebView({
  url,
  onComplete,
  onError,
}: PayDataCollectionWebViewProps) {
  const handleMessage = useCallback(
    (event: WebViewMessageEvent) => {
      try {
        const data = JSON.parse(event.nativeEvent.data);
        switch (data.type) {
          case "IC_COMPLETE":
            onComplete();
            break;
          case "IC_ERROR":
            onError(data.error || "Unknown error");
            break;
        }
      } catch {
        // Ignore non-JSON messages
      }
    },
    [onComplete, onError]
  );

  const handleNavigationRequest = useCallback(
    (request: { url: string }) => {
      // Open external links (T&C, Privacy Policy) in system browser
      if (!request.url.includes("pay.walletconnect.com")) {
        Linking.openURL(request.url);
        return false;
      }
      return true;
    },
    []
  );

  return (
    <WebView
      source={{ uri: url }}
      onMessage={handleMessage}
      onShouldStartLoadWithRequest={handleNavigationRequest}
      javaScriptEnabled
      domStorageEnabled
      startInLoadingState
      renderLoading={() => (
        <View style={{ flex: 1, justifyContent: "center", alignItems: "center" }}>
          <ActivityIndicator size="large" />
        </View>
      )}
    />
  );
}
```

## Confirm Payment

```js
const result = await client.confirmPayment({
  paymentId: options.paymentId,
  optionId: selectedOption.id,
  signatures,
  // Do NOT pass collectedData — WebView handles this
});

if (result.status === "succeeded") {
  console.log("Payment successful!");
} else if (result.status === "processing") {
  console.log("Payment is processing...");
} else if (result.status === "failed") {
  console.log("Payment failed");
}

// If not final, poll after suggested interval
if (!result.isFinal && result.pollInMs) {
  await new Promise(r => setTimeout(r, result.pollInMs));
  // Re-call confirmPayment
}
```

## Error Handling

```js
import { PayError } from "@walletconnect/pay";

try {
  const options = await client.getPaymentOptions({...});
} catch (error) {
  if (error instanceof PayError) {
    console.error(`Pay error [${error.code}]: ${error.message}`);
  }
}
```

## Complete Example

```js
import { WalletConnectPay } from "@walletconnect/pay";

class PaymentManager {
  private client: WalletConnectPay;

  constructor() {
    this.client = new WalletConnectPay({ appId: "your-app-id" });
  }

  async processPayment(paymentLink: string, walletAddress: string) {
    // 1. Get payment options
    const accounts = [1, 8453, 10, 137, 42161].map(
      (chain) => `eip155:${chain}:${walletAddress}`
    );

    const options = await this.client.getPaymentOptions({
      paymentLink,
      accounts,
      includePaymentInfo: true,
    });

    if (!options.options.length) throw new Error("No options available");

    // 2. Select option (simplified — use first)
    const selectedOption = options.options[0];

    // 3. Get required actions
    const actions = await this.client.getRequiredPaymentActions({
      paymentId: options.paymentId,
      optionId: selectedOption.id,
    });

    // 4. Sign all actions
    const signatures = await Promise.all(
      actions.map((action) =>
        wallet.signTypedData(
          action.walletRpc.chainId,
          JSON.parse(action.walletRpc.params)
        )
      )
    );

    // 5. Collect data via WebView if required
    if (selectedOption.collectData?.url) {
      await this.showDataCollectionWebView(selectedOption.collectData.url);
    }

    // 6. Confirm payment
    const result = await this.client.confirmPayment({
      paymentId: options.paymentId,
      optionId: selectedOption.id,
      signatures,
    });

    return result;
  }

  private async signAction(action, walletAddress: string): Promise<string> {
    const { chainId, method, params } = action.walletRpc;
    return await wallet.signTypedData(chainId, JSON.parse(params));
  }
}
```

## Key Differences from WalletKit Integration

| Aspect | WalletKit | Standalone |
|--------|-----------|------------|
| Package | `@reown/walletkit` | `@walletconnect/pay` |
| Client | `walletkit.pay` | `new WalletConnectPay()` |
| Init | Auto with WalletKit | Manual constructor |
| `isPaymentLink()` | Built-in import | Implement manually |
| Auth | Project ID | API Key or App ID |
| Provider check | Not needed | `isProviderAvailable()` recommended |
