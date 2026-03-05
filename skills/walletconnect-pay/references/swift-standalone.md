# Swift — Standalone Pay SDK

> Use this when your wallet does **not** use WalletConnect WalletKit.
> The Standalone SDK provides all Pay features without the WalletKit dependency.

## Requirements

- iOS 13.0+
- Swift 5.7+
- Xcode 14.0+
- App ID or API Key from [dashboard.walletconnect.com](https://dashboard.walletconnect.com)

## Installation

### Swift Package Manager

`Package.swift`:
```swift
dependencies: [
    .package(url: "https://github.com/reown-com/reown-swift", from: "1.0.0")
]
```

Add `WalletConnectPay` to your target dependencies:
```swift
.target(
    name: "YourApp",
    dependencies: ["WalletConnectPay"]
)
```

Check [GitHub releases](https://github.com/reown-com/reown-swift/releases) for the latest version.

## Configuration

In your `AppDelegate` or `SceneDelegate`:
```swift
import WalletConnectPay

func application(_ application: UIApplication, didFinishLaunchingWithOptions...) {
    // Option 1: With appId (recommended for wallets)
    WalletConnectPay.configure(
        appId: "your-walletconnect-project-id",
        logging: true
    )

    // Option 2: With API key
    WalletConnectPay.configure(
        apiKey: "your-pay-api-key"
    )
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `apiKey` | `String?` | No* | WalletConnect Pay API key |
| `appId` | `String?` | No* | WalletConnect project ID |
| `baseUrl` | `String?` | No | Custom API base URL |
| `logging` | `Bool` | No | Enable debug logging |

*At least one of `apiKey` or `appId` must be provided.

## Payment Link Detection

The standalone SDK includes `isPaymentLink()` which checks for `pay.` hosts and `pay=` parameter in WalletConnect URIs.

```swift
func handleScannedQR(_ content: String) {
    if isPaymentLink(content) {
        startPaymentFlow(paymentLink: content)
    }
}
```

### Deep Link Handling

```swift
// In SceneDelegate or AppDelegate
func scene(_ scene: UIScene, openURLContexts URLContexts: Set<UIOpenURLContext>) {
    guard let url = URLContexts.first?.url else { return }

    if isPaymentLink(url.absoluteString) {
        startPaymentFlow(paymentLink: url.absoluteString)
    }
}
```

## Get Payment Options

```swift
let paymentLink = "https://pay.walletconnect.com/?pid=pay_abc123..."

let accounts = [
    "eip155:1:\(walletAddress)",      // Ethereum Mainnet
    "eip155:137:\(walletAddress)",    // Polygon
    "eip155:8453:\(walletAddress)",   // Base
    "eip155:42161:\(walletAddress)"   // Arbitrum
]

do {
    let response = try await WalletConnectPay.instance.getPaymentOptions(
        paymentLink: paymentLink,
        accounts: accounts
    )

    if let info = response.info {
        print("Merchant: \(info.merchant.name)")
        print("Amount: \(info.amount.display.assetSymbol) \(info.amount.value)")
    }

    for option in response.options {
        print("Pay with \(option.amount.display.assetSymbol) on \(option.amount.display.networkName ?? "Unknown")")
        if option.collectData != nil {
            print("Option \(option.id) requires info capture")
        }
    }
} catch {
    print("Failed to get payment options: \(error)")
}
```

## Get Required Actions

```swift
let actions = try await WalletConnectPay.instance.getRequiredPaymentActions(
    paymentId: response.paymentId,
    optionId: selectedOption.id
)
```

## Signing

Each action contains a `walletRpc` with EIP-712 typed data (`eth_signTypedData_v4`).

```swift
var signatures: [String] = []

for action in actions {
    let rpc = action.walletRpc
    // rpc.chainId - "eip155:8453"
    // rpc.method  - "eth_signTypedData_v4"
    // rpc.params  - JSON string: ["address", "{...typed data...}"]

    let paramsData = rpc.params.data(using: .utf8)!
    let params = try JSONSerialization.jsonObject(with: paramsData) as! [Any]
    let typedDataJson = params[1] as! String

    let signature = try await yourWallet.signTypedData(
        typedData: typedDataJson,
        address: walletAddress,
        chainId: rpc.chainId
    )

    signatures.append(signature)
}
// Critical: preserve order — signatures[i] must correspond to actions[i]
```

## Data Collection WebView

```swift
// Check per-option
if let collectData = selectedOption.collectData, let url = collectData.url {
    // Optional: prefill known user data
    let prefillData = ["fullName": "John Doe", "dob": "1990-01-15"]
    let jsonData = try JSONSerialization.data(withJSONObject: prefillData)
    let base64 = jsonData.base64EncodedString()

    var components = URLComponents(string: url)!
    components.queryItems = (components.queryItems ?? []) + [
        URLQueryItem(name: "prefill", value: base64)
    ]

    // Show WKWebView with payDataCollectionComplete JS bridge
    // Listen for IC_COMPLETE -> proceed to confirmPayment
    //         IC_ERROR     -> show error
}
```

### WKWebView Implementation

```swift
import WebKit
import SwiftUI

struct PayDataCollectionWebView: UIViewRepresentable {
    let url: URL
    let onComplete: () -> Void
    let onError: (String) -> Void

    func makeCoordinator() -> Coordinator {
        Coordinator(onComplete: onComplete, onError: onError)
    }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.userContentController.add(
            context.coordinator,
            name: "payDataCollectionComplete"
        )

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}

    class Coordinator: NSObject, WKScriptMessageHandler, WKNavigationDelegate {
        let onComplete: () -> Void
        let onError: (String) -> Void

        init(onComplete: @escaping () -> Void, onError: @escaping (String) -> Void) {
            self.onComplete = onComplete
            self.onError = onError
        }

        func userContentController(
            _ controller: WKUserContentController,
            didReceive message: WKScriptMessage
        ) {
            guard let body = message.body as? [String: Any],
                  let type = body["type"] as? String else { return }

            switch type {
            case "IC_COMPLETE": onComplete()
            case "IC_ERROR": onError(body["error"] as? String ?? "Unknown error")
            default: break
            }
        }
    }
}
```

## Confirm Payment

```swift
let result = try await WalletConnectPay.instance.confirmPayment(
    paymentId: paymentId,
    optionId: selectedOption.id,
    signatures: signatures
    // Do NOT pass collectedData — WebView handles this
)

switch result.status {
case .succeeded:      print("Payment successful!")
case .processing:     print("Payment is being processed...")
case .failed:         print("Payment failed")
case .expired:        print("Payment expired")
case .requiresAction: print("Additional action required")
}

// If not final, poll after suggested interval
if !result.isFinal, let pollMs = result.pollInMs {
    try await Task.sleep(nanoseconds: UInt64(pollMs) * 1_000_000)
    // Re-call confirmPayment
}
```

## Error Handling

```swift
do {
    let options = try await WalletConnectPay.instance.getPaymentOptions(...)
} catch let error as GetPaymentOptionsError {
    switch error {
    case .invalidPaymentLink: showError("Invalid payment link")
    case .paymentNotFound:    showError("Payment not found")
    case .paymentExpired:     showError("Payment expired")
    case .invalidOption:      showError("Invalid option")
    case .invalidSignature:   showError("Signature verification failed")
    case .routeExpired:       showError("Payment route expired")
    case .http:               showError("Network error")
    }
}
```

## Complete Example

```swift
import WalletConnectPay

class PaymentManager {

    func processPayment(
        paymentLink: String,
        walletAddress: String,
        signer: YourSignerProtocol
    ) async throws {

        // 1. Get payment options
        let accounts = [
            "eip155:1:\(walletAddress)",
            "eip155:137:\(walletAddress)",
            "eip155:8453:\(walletAddress)"
        ]

        let optionsResponse = try await WalletConnectPay.instance.getPaymentOptions(
            paymentLink: paymentLink,
            accounts: accounts
        )

        guard !optionsResponse.options.isEmpty else {
            throw PaymentError.noOptionsAvailable
        }

        // 2. Select option (simplified — use first)
        let selectedOption = optionsResponse.options[0]

        // 3. Get required actions
        let actions = try await WalletConnectPay.instance.getRequiredPaymentActions(
            paymentId: optionsResponse.paymentId,
            optionId: selectedOption.id
        )

        // 4. Sign all actions
        var signatures: [String] = []
        for action in actions {
            let rpc = action.walletRpc
            let paramsData = rpc.params.data(using: .utf8)!
            let params = try JSONSerialization.jsonObject(with: paramsData) as! [Any]
            guard let typedDataJson = params[1] as? String else {
                throw PaymentError.invalidParams
            }
            let sig = try await signer.signTypedData(
                data: typedDataJson,
                address: walletAddress
            )
            signatures.append(sig)
        }

        // 5. Collect data via WebView if required
        if let collectData = selectedOption.collectData, let url = collectData.url {
            try await showDataCollectionWebView(url: url)
        }

        // 6. Confirm payment
        let result = try await WalletConnectPay.instance.confirmPayment(
            paymentId: optionsResponse.paymentId,
            optionId: selectedOption.id,
            signatures: signatures
        )

        guard result.status == .succeeded else {
            throw PaymentError.paymentFailed(result.status)
        }
    }
}
```

## Key Differences from WalletKit Integration

| Aspect | WalletKit | Standalone |
|--------|-----------|------------|
| Package | `reown-swift` WalletKit | `reown-swift` WalletConnectPay |
| Client | `WalletKit.Pay` | `WalletConnectPay.instance` |
| Init | Auto with WalletKit | Manual `WalletConnectPay.configure()` |
| `isPaymentLink()` | Built-in via WalletKit | Standalone utility function |
| Auth | Project ID | API Key or App ID |
