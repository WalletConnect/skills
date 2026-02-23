# Kotlin — Standalone Pay SDK

> Use this when your wallet does **not** use WalletConnect WalletKit.
> The Standalone SDK provides all Pay features without the WalletKit dependency.

## Requirements

- Android SDK 23+
- App ID or API Key from [dashboard.walletconnect.com](https://dashboard.walletconnect.com)
- Contact WalletConnect team to obtain access credentials

## Installation

`build.gradle.kts`:
```kotlin
dependencies {
    implementation("com.walletconnect:pay:1.0.0")  // check GitHub for latest
}
```

**JNA issue fix** (if you encounter JNA-related errors):
```kotlin
implementation("com.walletconnect:pay:1.0.0") {
    exclude(group = "net.java.dev.jna", module = "jna")
}
implementation("net.java.dev.jna:jna:5.17.0@aar")
```

## Initialization

In your `Application.onCreate()`:
```kotlin
import com.walletconnect.pay.Pay
import com.walletconnect.pay.WalletConnectPay

WalletConnectPay.initialize(
    Pay.SdkConfig(
        apiKey = "your-api-key",      // provide apiKey OR appId
        appId = "your-project-id",    //
        packageName = "com.your.app"  // required
    )
)

check(WalletConnectPay.isInitialized) { "Pay SDK not initialized" }
```

## Payment Link Detection

The standalone SDK does not include `isPaymentLink()`. Detect payment links by checking:
- Domain is `pay.walletconnect.com` or a subdomain
- URI contains `pay_` prefix in the path, `pay=` query parameter, or `pay.` hostname

```kotlin
fun isPaymentLink(uri: String): Boolean {
    val host = Uri.parse(uri).host ?: return false
    return host == "pay.walletconnect.com" || host.endsWith(".pay.walletconnect.com")
}
```

## Get Payment Options

```kotlin
val result = WalletConnectPay.getPaymentOptions(
    paymentLink = "https://pay.walletconnect.com/pay_xxx",
    accounts = listOf(
        "eip155:1:0xYourAddress",
        "eip155:8453:0xYourAddress",
        "eip155:10:0xYourAddress",
        "eip155:137:0xYourAddress",
        "eip155:42161:0xYourAddress"
    )
)

result.onSuccess { response ->
    val paymentId = response.paymentId
    val options = response.options        // List<Pay.PaymentOption>
}.onFailure { handleError(it) }
```

## Get Required Actions

```kotlin
val actionsResult = WalletConnectPay.getRequiredPaymentActions(
    paymentId = paymentId,
    optionId = selectedOption.id
)

actionsResult.onSuccess { actions ->
    actions.forEach { action ->
        when (action) {
            is Pay.RequiredAction.WalletRpc -> {
                val rpc = action.action
                // rpc.chainId: "eip155:8453"
                // rpc.method:  "eth_signTypedData_v4"
                // rpc.params:  JSON string
            }
        }
    }
}
```

## Signing

```kotlin
val signatures = actions.map { action ->
    when (action) {
        is Pay.RequiredAction.WalletRpc -> {
            val rpc = action.action
            when (rpc.method) {
                "eth_signTypedData_v4" -> wallet.signTypedData(rpc.chainId, rpc.params)
                "personal_sign"        -> wallet.personalSign(rpc.chainId, rpc.params)
                else -> throw UnsupportedOperationException("Unsupported: ${rpc.method}")
            }
        }
    }
}
// Critical: preserve order — signatures[i] must correspond to actions[i]
```

## Data Collection WebView

```kotlin
// Check per-option
selectedOption.collectData?.url?.let { baseUrl ->
    val prefillBase64 = Base64.encodeToString(
        JSONObject(mapOf("fullName" to "John Doe", "dob" to "1990-01-15"))
            .toString().toByteArray(),
        Base64.NO_WRAP or Base64.URL_SAFE
    )
    val url = Uri.parse(baseUrl).buildUpon()
        .appendQueryParameter("prefill", prefillBase64)
        .build().toString()

    // Show WebView with AndroidWallet JS bridge
    // Listen for IC_COMPLETE → proceed to confirmPayment
    //         IC_ERROR     → show error
}
```

## Confirm Payment

```kotlin
val confirmResult = WalletConnectPay.confirmPayment(
    paymentId = paymentId,
    optionId = selectedOption.id,
    signatures = signatures
    // Do NOT pass collectedData — WebView handles this
)

confirmResult.onSuccess { response ->
    when (response.status) {
        Pay.PaymentStatus.SUCCEEDED      -> showSuccess()
        Pay.PaymentStatus.PROCESSING     -> showProcessing()
        Pay.PaymentStatus.FAILED         -> showFailure()
        Pay.PaymentStatus.EXPIRED        -> showExpired()
        Pay.PaymentStatus.REQUIRES_ACTION -> handleAdditional()
    }
}
```

## Error Handling

```kotlin
result.onFailure { error ->
    when (error) {
        is Pay.GetPaymentOptionsError.InvalidPaymentLink -> showError("Invalid payment link")
        is Pay.GetPaymentOptionsError.PaymentExpired    -> showError("Payment expired")
        is Pay.GetPaymentOptionsError.PaymentNotFound   -> showError("Payment not found")
        is Pay.GetPaymentOptionsError.InvalidAccount    -> showError("Invalid account format")
        is Pay.GetPaymentOptionsError.Http              -> showError("Network error")
        else -> showError("Unknown error: ${error.message}")
    }
}
```

## Complete ViewModel Example

```kotlin
class PaymentViewModel : ViewModel() {

    fun processPayment(paymentLink: String, walletAddress: String) {
        viewModelScope.launch {
            val accounts = listOf(1, 8453, 10, 137, 42161).map { chain ->
                "eip155:$chain:$walletAddress"
            }

            WalletConnectPay.getPaymentOptions(paymentLink, accounts)
                .onSuccess { response ->
                    val option = response.options.first()

                    WalletConnectPay.getRequiredPaymentActions(response.paymentId, option.id)
                        .onSuccess { actions ->
                            val signatures = signActions(actions)

                            if (option.collectData?.url != null) {
                                _showWebView.emit(option.collectData!!.url)
                                // wait for IC_COMPLETE, then call confirmPayment
                                return@onSuccess
                            }

                            confirmPayment(response.paymentId, option.id, signatures)
                        }
                        .onFailure { _error.emit(it.message ?: "Failed to get actions") }
                }
                .onFailure { _error.emit(it.message ?: "Failed to get options") }
        }
    }

    private suspend fun signActions(actions: List<Pay.RequiredAction>): List<String> =
        actions.map { action ->
            when (action) {
                is Pay.RequiredAction.WalletRpc -> yourWallet.sign(action.action)
            }
        }
}
```

## Key Differences from WalletKit Integration

| Aspect | WalletKit | Standalone |
|--------|-----------|------------|
| Package | `com.reown:walletkit` | `com.walletconnect:pay` |
| Client | `WalletKit.Pay` | `WalletConnectPay` |
| Init | Auto with WalletKit | Manual `WalletConnectPay.initialize()` |
| `isPaymentLink()` | Built-in | Implement manually |
| Auth | Project ID | API Key or App ID |
