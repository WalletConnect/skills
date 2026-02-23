# Flutter — WalletKit Integration

> **Recommended** if your wallet already uses `reown_walletkit`.
> The Pay client is automatically included as a dependency.

## Requirements

- Flutter 3.0+, Dart 3.0+
- `reown_walletkit: ^1.4.0`
- `webview_flutter: ^4.10.0` (for data collection)
- App ID from [dashboard.walletconnect.com](https://dashboard.walletconnect.com)

## Installation

`pubspec.yaml`:
```yaml
dependencies:
  reown_walletkit: ^1.4.0
  webview_flutter: ^4.10.0
  url_launcher: ^6.1.0
```

```bash
flutter pub get
```

## Initialization

```dart
import 'package:reown_walletkit/reown_walletkit.dart';

final walletKit = await ReownWalletKit.createInstance(
  projectId: 'YOUR_PROJECT_ID',
  metadata: PairingMetadata(
    name: 'My Wallet',
    description: 'My crypto wallet',
    url: 'https://mywallet.com',
    icons: ['https://mywallet.com/icon.png'],
  ),
);

// Pay client available as walletKit.pay
```

## Payment Link Detection

```dart
void handleUri(String uri) {
  if (walletKit.isPaymentLink(uri)) {
    processPayment(uri);
  } else {
    walletKit.pair(uri: Uri.parse(uri));
  }
}
```

## Get Payment Options

```dart
final response = await walletKit.getPaymentOptions(
  request: GetPaymentOptionsRequest(
    paymentLink: uri,
    accounts: [
      'eip155:1:$address',
      'eip155:8453:$address',
      'eip155:10:$address',
      'eip155:137:$address',
      'eip155:42161:$address',
    ],
    includePaymentInfo: true,
  ),
);

// response.paymentId  — use in all subsequent calls
// response.options    — List<PaymentOption>
// response.collectData? — data collection requirement
// response.info?      — merchant name, amount, expiresAt
```

## Get Required Actions

```dart
final actions = await walletKit.getRequiredPaymentActions(
  request: GetRequiredPaymentActionsRequest(
    paymentId: response.paymentId,
    optionId: selectedOption.id,
  ),
);
// actions[i].walletRpc: { chainId, method, params }
```

## Signing (EIP-712)

```dart
// Sign all actions in order — signatures must match actions array
final signatures = <String>[];
for (final action in actions) {
  final rpc = action.walletRpc;
  // Implement signTypedData with your wallet's key management
  final sig = await yourWallet.signTypedData(
    chainId: rpc.chainId,
    params: rpc.params,   // JSON string with [address, typedDataJson]
  );
  signatures.add(sig);
}
```

## Data Collection WebView

```dart
import 'dart:convert';
import 'package:webview_flutter/webview_flutter.dart';

// Build prefill URL
String buildPrefillUrl(String baseUrl, Map<String, String> userData) {
  if (userData.isEmpty) return baseUrl;
  final prefillJson = jsonEncode(userData);
  final prefillBase64 = base64Url.encode(utf8.encode(prefillJson));
  final uri = Uri.parse(baseUrl);
  return uri.replace(
    queryParameters: {...uri.queryParameters, 'prefill': prefillBase64},
  ).toString();
}

// WebView widget
class PayDataCollectionWebView extends StatefulWidget {
  final String url;
  final VoidCallback onComplete;
  final ValueChanged<String> onError;
  const PayDataCollectionWebView({
    required this.url, required this.onComplete, required this.onError
  });
  @override
  State<PayDataCollectionWebView> createState() => _State();
}

class _State extends State<PayDataCollectionWebView> {
  late final WebViewController _controller;
  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..addJavaScriptChannel('ReactNativeWebView', onMessageReceived: (msg) {
        try {
          final data = jsonDecode(msg.message) as Map<String, dynamic>;
          if (data['type'] == 'IC_COMPLETE') widget.onComplete();
          else if (data['type'] == 'IC_ERROR') widget.onError(data['error'] ?? 'Unknown');
        } catch (_) {}
      })
      ..loadRequest(Uri.parse(widget.url));
  }
  @override
  Widget build(BuildContext context) => WebViewWidget(controller: _controller);
}

// Usage — only show when collectData is present
if (response.collectData?.url != null) {
  final url = buildPrefillUrl(response.collectData!.url, {'fullName': 'John Doe'});
  showDataCollectionView(url);
}
```

## Confirm Payment

```dart
var confirmResponse = await walletKit.confirmPayment(
  request: ConfirmPaymentRequest(
    paymentId: response.paymentId,
    optionId: selectedOption.id,
    signatures: signatures,
    maxPollMs: 60000,
  ),
);

// Poll until final status
while (!confirmResponse.isFinal && confirmResponse.pollInMs != null) {
  await Future.delayed(Duration(milliseconds: confirmResponse.pollInMs!));
  confirmResponse = await walletKit.confirmPayment(
    request: ConfirmPaymentRequest(
      paymentId: response.paymentId,
      optionId: selectedOption.id,
      signatures: signatures,
    ),
  );
}

switch (confirmResponse.status) {
  case PaymentStatus.succeeded:   showSuccess(); break;
  case PaymentStatus.processing:  showProcessing(); break;
  case PaymentStatus.failed:      showFailure(); break;
  case PaymentStatus.expired:     showExpired(); break;
  case PaymentStatus.requires_action: handleAdditional(); break;
}
```

## Error Handling

```dart
try {
  final response = await walletKit.getPaymentOptions(request: request);
} on GetPaymentOptionsError catch (e) {
  // e.message describes the failure
  switch (e.code) {
    case 'payment_not_found': showError('Payment not found'); break;
    case 'payment_expired':   showError('Payment expired'); break;
    case 'invalid_account':   showError('Invalid account format'); break;
    case 'compliance_failed': showError('Compliance check failed'); break;
    default: showError('Payment error: ${e.message}');
  }
} on PayError catch (e) {
  showError('SDK error: ${e.message}');
}
```

## Key Data Models

| Model | Key Fields |
|-------|-----------|
| `GetPaymentOptionsRequest` | `paymentLink`, `accounts` (CAIP-10), `includePaymentInfo` |
| `PaymentOptionsResponse` | `paymentId`, `options[]`, `collectData?`, `info?` |
| `PaymentOption` | `id`, `amount`, `account`, `etaS`, `collectData?` |
| `ConfirmPaymentRequest` | `paymentId`, `optionId`, `signatures[]`, `maxPollMs` |
| `ConfirmPaymentResponse` | `status`, `isFinal`, `pollInMs?` |
| `PaymentStatus` enum | `requires_action`, `processing`, `succeeded`, `failed`, `expired` |

## Reference App

See the [reown_walletkit example on GitHub](https://github.com/reown-com/reown_flutter/tree/master/packages/reown_walletkit/example/lib/walletconnect_pay) for a complete working implementation.
