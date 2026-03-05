# Flutter — Standalone Pay SDK

> Use this when your wallet does **not** use WalletConnect WalletKit.
> The Standalone SDK provides all Pay features without the WalletKit dependency.

## Requirements

- Flutter 3.0+
- Dart 3.0+
- App ID or API Key from [dashboard.walletconnect.com](https://dashboard.walletconnect.com)

## Installation

```bash
flutter pub add walletconnect_pay
```

Or add to `pubspec.yaml`:
```yaml
dependencies:
  walletconnect_pay: ^1.0.0  # check pub.dev for latest
```

## Configuration

```dart
import 'package:walletconnect_pay/walletconnect_pay.dart';

final payClient = WalletConnectPay(
  apiKey: 'YOUR_API_KEY',    // Optional
  appId: 'YOUR_APP_ID',     // Optional
  clientId: 'OPTIONAL_CLIENT_ID',
  baseUrl: 'https://api.pay.walletconnect.com', // Optional
);

// Initialize the SDK
try {
  await payClient.init();
} on PayInitializeError catch (e) {
  print('Initialization failed: ${e.code} - ${e.message}');
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `apiKey` | `String?` | No* | WalletConnect Pay API key |
| `appId` | `String?` | No* | WalletConnect app ID |
| `clientId` | `String?` | No | Client identifier |
| `baseUrl` | `String?` | No | Base URL for the API |

*At least one of `apiKey` or `appId` must be provided.

## Payment Link Detection

The standalone SDK does not include `isPaymentLink()`. Detect payment links by checking:
- Domain is `pay.walletconnect.com` or a subdomain
- URI contains `pay_` prefix in the path, `pay=` query parameter, or `pay.` hostname

```dart
bool isPaymentLink(String uri) {
  final url = Uri.tryParse(uri);
  if (url == null) return false;
  return url.host == 'pay.walletconnect.com' ||
         url.host.endsWith('.pay.walletconnect.com');
}
```

## Get Payment Options

```dart
final request = GetPaymentOptionsRequest(
  paymentLink: 'https://pay.walletconnect.com/pay_123',
  accounts: [
    'eip155:1:$walletAddress',      // Ethereum Mainnet
    'eip155:137:$walletAddress',    // Polygon
    'eip155:8453:$walletAddress',   // Base
    'eip155:42161:$walletAddress',  // Arbitrum
  ],
  includePaymentInfo: true,
);

final response = await payClient.getPaymentOptions(request: request);

print('Payment ID: ${response.paymentId}');
print('Options available: ${response.options.length}');

if (response.info != null) {
  print('Amount: ${response.info!.amount.formatAmount()}');
  print('Merchant: ${response.info!.merchant.name}');
}

for (final option in response.options) {
  if (option.collectData != null) {
    print('Option ${option.id} requires info capture');
  }
}
```

## Get Required Payment Actions

```dart
final actionsRequest = GetRequiredPaymentActionsRequest(
  optionId: selectedOption.id,
  paymentId: response.paymentId,
);

final actions = await payClient.getRequiredPaymentActions(
  request: actionsRequest,
);

for (final action in actions) {
  final walletRpc = action.walletRpc;
  print('Chain ID: ${walletRpc.chainId}');
  print('Method: ${walletRpc.method}');
  print('Params: ${walletRpc.params}');
}
```

## Signing

```dart
final signatures = <String>[];

for (final action in actions) {
  final rpc = action.walletRpc;
  // rpc.chainId - "eip155:8453"
  // rpc.method  - "eth_signTypedData_v4"
  // rpc.params  - JSON string: ["address", "{...typed data...}"]

  final signature = await yourWallet.signTypedData(
    chainId: rpc.chainId,
    params: rpc.params,
  );
  signatures.add(signature);
}
// Critical: preserve order — signatures[i] must correspond to actions[i]
```

## Data Collection WebView

```dart
// Check per-option
if (selectedOption.collectData?.url != null) {
  final baseUrl = selectedOption.collectData!.url;

  // Optional: prefill known user data
  final prefillData = {'fullName': 'John Doe', 'dob': '1990-01-15'};
  final base64 = base64Encode(utf8.encode(jsonEncode(prefillData)));
  final separator = baseUrl.contains('?') ? '&' : '?';
  final url = '$baseUrl${separator}prefill=$base64';

  // Show WebView with ReactNativeWebView JS bridge (injected via JS)
  // Listen for IC_COMPLETE -> proceed to confirmPayment
  //         IC_ERROR     -> show error
}
```

### WebView Implementation

Add to `pubspec.yaml`:
```yaml
dependencies:
  webview_flutter: ^4.10.0
  url_launcher: ^6.1.0
```

```dart
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:url_launcher/url_launcher.dart';

class PayDataCollectionWebView extends StatefulWidget {
  final String url;
  final VoidCallback onComplete;
  final ValueChanged<String> onError;

  const PayDataCollectionWebView({
    super.key,
    required this.url,
    required this.onComplete,
    required this.onError,
  });

  @override
  State<PayDataCollectionWebView> createState() => _PayDataCollectionWebViewState();
}

class _PayDataCollectionWebViewState extends State<PayDataCollectionWebView> {
  late final WebViewController _controller;

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..addJavaScriptChannel(
        'ReactNativeWebView',
        onMessageReceived: (message) {
          try {
            final data = jsonDecode(message.message);
            switch (data['type']) {
              case 'IC_COMPLETE':
                widget.onComplete();
                break;
              case 'IC_ERROR':
                widget.onError(data['error'] ?? 'Unknown error');
                break;
            }
          } catch (_) {
            // Ignore non-JSON messages
          }
        },
      )
      ..setNavigationDelegate(
        NavigationDelegate(
          onNavigationRequest: (request) {
            if (!request.url.contains('pay.walletconnect.com')) {
              launchUrl(Uri.parse(request.url));
              return NavigationDecision.prevent;
            }
            return NavigationDecision.navigate;
          },
        ),
      )
      ..loadRequest(Uri.parse(widget.url));
  }

  @override
  Widget build(BuildContext context) {
    return WebViewWidget(controller: _controller);
  }
}
```

## Confirm Payment

```dart
final confirmRequest = ConfirmPaymentRequest(
  paymentId: response.paymentId,
  optionId: selectedOption.id,
  signatures: signatures,
  // Do NOT pass collectedData — WebView handles this
  maxPollMs: 60000,
);

final confirmResponse = await payClient.confirmPayment(request: confirmRequest);

print('Status: ${confirmResponse.status}');
print('Is Final: ${confirmResponse.isFinal}');

// If not final, poll after suggested interval
if (!confirmResponse.isFinal && confirmResponse.pollInMs != null) {
  await Future.delayed(Duration(milliseconds: confirmResponse.pollInMs!));
  // Re-call confirmPayment
}
```

### Payment Statuses

```dart
enum PaymentStatus {
  requires_action,  // Additional action needed
  processing,       // Payment in progress
  succeeded,        // Payment completed
  failed,           // Payment failed
  expired,          // Payment expired
}
```

## Error Handling

All errors extend the abstract `PayError` class (which extends `PlatformException`):

```dart
try {
  await payClient.init();
} on PayInitializeError catch (e) {
  print('Initialization failed: ${e.code} - ${e.message}');
}

try {
  final response = await payClient.getPaymentOptions(request: request);
} on GetPaymentOptionsError catch (e) {
  print('Error code: ${e.code}');
  print('Message: ${e.message}');
}

try {
  final actions = await payClient.getRequiredPaymentActions(request: actionsRequest);
} on GetRequiredActionsError catch (e) {
  print('Actions error: ${e.code} - ${e.message}');
}

try {
  final result = await payClient.confirmPayment(request: confirmRequest);
} on ConfirmPaymentError catch (e) {
  print('Confirm error: ${e.code} - ${e.message}');
}
```

| Exception | Description |
|-----------|-------------|
| `PayInitializeError` | Initialization failures |
| `GetPaymentOptionsError` | Errors when fetching payment options |
| `GetRequiredActionsError` | Errors when getting required actions |
| `ConfirmPaymentError` | Errors when confirming payment |

## Complete Example

```dart
import 'package:walletconnect_pay/walletconnect_pay.dart';

class PaymentService {
  late final WalletConnectPay _payClient;

  Future<void> initialize() async {
    _payClient = WalletConnectPay(appId: 'YOUR_APP_ID');
    await _payClient.init();
  }

  Future<ConfirmPaymentResponse> processPayment(
    String paymentLink,
    List<String> accounts,
  ) async {
    // 1. Get payment options
    final optionsResponse = await _payClient.getPaymentOptions(
      request: GetPaymentOptionsRequest(
        paymentLink: paymentLink,
        accounts: accounts,
        includePaymentInfo: true,
      ),
    );

    if (optionsResponse.options.isEmpty) {
      throw Exception('No payment options available');
    }

    // 2. Select option (simplified — use first)
    final selectedOption = optionsResponse.options.first;

    // 3. Get required actions
    final actions = await _payClient.getRequiredPaymentActions(
      request: GetRequiredPaymentActionsRequest(
        optionId: selectedOption.id,
        paymentId: optionsResponse.paymentId,
      ),
    );

    // 4. Sign all actions
    final signatures = <String>[];
    for (final action in actions) {
      final signature = await signTransaction(action.walletRpc);
      signatures.add(signature);
    }

    // 5. Collect data via WebView if required
    if (selectedOption.collectData?.url != null) {
      await showDataCollectionWebView(selectedOption.collectData!.url);
    }

    // 6. Confirm payment
    var response = await _payClient.confirmPayment(
      request: ConfirmPaymentRequest(
        paymentId: optionsResponse.paymentId,
        optionId: selectedOption.id,
        signatures: signatures,
        maxPollMs: 60000,
      ),
    );

    // 7. Poll until final status (if needed)
    while (!response.isFinal && response.pollInMs != null) {
      await Future.delayed(Duration(milliseconds: response.pollInMs!));
      response = await _payClient.confirmPayment(
        request: ConfirmPaymentRequest(
          paymentId: optionsResponse.paymentId,
          optionId: selectedOption.id,
          signatures: signatures,
          maxPollMs: 60000,
        ),
      );
    }

    return response;
  }

  Future<String> signTransaction(WalletRpcAction walletRpc) async {
    // Implement your wallet's signing logic
    // Use walletRpc.chainId, walletRpc.method, walletRpc.params
    throw UnimplementedError('Implement signing logic');
  }
}
```

## Key Differences from WalletKit Integration

| Aspect | WalletKit | Standalone |
|--------|-----------|------------|
| Package | `reown_walletkit` | `walletconnect_pay` |
| Client | `walletKit.pay` | `WalletConnectPay()` instance |
| Init | Auto with WalletKit | Manual `payClient.init()` |
| `isPaymentLink()` | Built-in via WalletKit | Implement manually |
| Auth | Project ID | API Key or App ID |
| WebView bridge | N/A | `ReactNativeWebView` JS channel |
