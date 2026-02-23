# Swift — WalletKit Integration

> **Recommended** if your wallet already uses ReownWalletKit.
> WalletConnectPay is automatically bundled as a WalletKit dependency.

## Requirements

- iOS 13.0+
- Swift 5.7+, Xcode 14.0+
- App ID from [dashboard.walletconnect.com](https://dashboard.walletconnect.com)

## Installation (Swift Package Manager)

`Package.swift`:
```swift
dependencies: [
    .package(url: "https://github.com/reown-com/reown-swift", from: "1.0.0")
]

.target(
    name: "YourWallet",
    dependencies: ["ReownWalletKit"]
)
// WalletConnectPay is automatically included
```

## Initialization

In `AppDelegate` or `App.init`:
```swift
import ReownWalletKit

WalletKit.configure(
    metadata: AppMetadata(
        name: "My Wallet",
        description: "My crypto wallet",
        url: "https://mywallet.com",
        icons: ["https://mywallet.com/icon.png"]
    ),
    crypto: DefaultCryptoProvider(),
    payLogging: true  // enable Pay debug logging
)
// Pay auto-configures using Networking.projectId
```

## Payment Link Detection

```swift
// Static — safe to call before configure()
if WalletKit.isPaymentLink(scannedString) {
    startPaymentFlow(paymentLink: scannedString)
}

// Deep link handling
func scene(_ scene: UIScene, openURLContexts contexts: Set<UIOpenURLContext>) {
    guard let url = contexts.first?.url else { return }
    if WalletKit.isPaymentLink(url.absoluteString) {
        startPaymentFlow(paymentLink: url.absoluteString)
    }
}
```

## Get Payment Options

```swift
let response = try await WalletKit.instance.Pay.getPaymentOptions(
    paymentLink: paymentLink,
    accounts: [
        "eip155:1:\(address)",
        "eip155:8453:\(address)",
        "eip155:10:\(address)",
        "eip155:137:\(address)",
        "eip155:42161:\(address)"
    ]
)

// response.paymentId   — use in all subsequent calls
// response.options     — [PaymentOption]
// response.info?       — merchant name, amount, expiresAt
```

## Get Required Actions

```swift
let actions = try await WalletKit.instance.Pay.getRequiredPaymentActions(
    paymentId: response.paymentId,
    optionId: selectedOption.id
)
// actions: [Action], each with action.walletRpc: { chainId, method, params }
```

## Signing (EIP-712)

```swift
// Sign all actions in order — signature[i] corresponds to actions[i]
var signatures: [String] = []
for action in actions {
    let rpc = action.walletRpc
    guard let paramsData = rpc.params.data(using: .utf8),
          let params = try? JSONSerialization.jsonObject(with: paramsData) as? [Any],
          params.count >= 2,
          let typedDataJson = params[1] as? String else {
        throw PaymentError.invalidParams
    }
    let sig = try await signer.signTypedData(data: typedDataJson, address: walletAddress)
    signatures.append(sig)
}
```

## Data Collection WebView

```swift
if let collectData = selectedOption.collectData, let urlString = collectData.url {
    let prefillData: [String: String] = [
        "fullName": "John Doe",
        "dob": "1990-01-15"
    ]
    let jsonData = try JSONSerialization.data(withJSONObject: prefillData)
    let prefillBase64 = jsonData.base64EncodedString()
    var components = URLComponents(string: urlString)!
    var queryItems = components.queryItems ?? []
    queryItems.append(URLQueryItem(name: "prefill", value: prefillBase64))
    components.queryItems = queryItems
    showWebView(url: URL(string: components.string!)!)
}
```

SwiftUI WebView (WKWebView):
```swift
import WebKit, SwiftUI

struct PayDataCollectionWebView: UIViewRepresentable {
    let url: URL
    let onComplete: () -> Void
    let onError: (String) -> Void

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.userContentController.add(context.coordinator, name: "payDataCollectionComplete")
        let wv = WKWebView(frame: .zero, configuration: config)
        wv.load(URLRequest(url: url))
        return wv
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}
    func makeCoordinator() -> Coordinator { Coordinator(onComplete: onComplete, onError: onError) }

    class Coordinator: NSObject, WKScriptMessageHandler {
        let onComplete: () -> Void
        let onError: (String) -> Void
        init(onComplete: @escaping () -> Void, onError: @escaping (String) -> Void) {
            self.onComplete = onComplete; self.onError = onError
        }
        func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
            guard let body = message.body as? String,
                  let data = body.data(using: .utf8),
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let type = json["type"] as? String else { return }
            DispatchQueue.main.async {
                if type == "IC_COMPLETE" { self.onComplete() }
                else if type == "IC_ERROR" { self.onError(json["error"] as? String ?? "Unknown") }
            }
        }
    }
}
```

## Confirm Payment

```swift
let result = try await WalletKit.instance.Pay.confirmPayment(
    paymentId: response.paymentId,
    optionId: selectedOption.id,
    signatures: signatures
)

switch result.status {
case .succeeded:  showSuccess()
case .processing: showProcessing()
case .failed:     showFailure()
case .expired:    showExpired()
case .requiresAction: handleAdditionalAction()
}

// Poll if not final
if !result.isFinal, let delay = result.pollInMs {
    try await Task.sleep(nanoseconds: UInt64(delay) * 1_000_000)
    // re-confirm
}
```

## Error Types

```swift
// GetPaymentOptionsError
case paymentNotFound, paymentExpired, invalidRequest,
     invalidAccount, complianceFailed, http, internalError

// GetRequiredPaymentActionsError (GetPaymentRequestError)
case optionNotFound, paymentNotFound, invalidAccount, http

// ConfirmPaymentError
case paymentNotFound, paymentExpired, invalidOption,
     invalidSignature, routeExpired, http
```
