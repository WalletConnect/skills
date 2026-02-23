# Kotlin — WalletKit Integration

> **Recommended** if your wallet already uses WalletConnect WalletKit.
> Pay SDK is automatically included and initializes with WalletKit.

## Requirements

- Android SDK 23+
- WalletKit 1.6.0+
- App ID from [dashboard.walletconnect.com](https://dashboard.walletconnect.com)

## Installation

`settings.gradle.kts`:
```kotlin
allprojects {
    repositories {
        mavenCentral()
        maven { url = uri("https://jitpack.io") }
    }
}
```

`build.gradle.kts`:
```kotlin
val BOM_VERSION = "latest"  // check GitHub releases
releaseImplementation(platform("com.reown:android-bom:$BOM_VERSION"))
releaseImplementation("com.reown:android-core")
releaseImplementation("com.reown:walletkit")
// Pay SDK is automatically included
```

## Initialization

In your `Application.onCreate()`:

```kotlin
import com.reown.android.Core
import com.reown.android.CoreClient
import com.reown.walletkit.client.WalletKit

val appMetaData = Core.Model.AppMetaData(
    name = "My Wallet",
    description = "My Wallet Description",
    url = "https://mywallet.com",
    icons = listOf("https://mywallet.com/icon.png"),
    redirect = "mywallet://wc/request"
)

CoreClient.initialize(
    projectId = "YOUR_PROJECT_ID",
    application = this,
    metaData = appMetaData
)

WalletKit.initialize(Wallet.Params.Init(core = CoreClient)) { error ->
    Log.e("WalletKit", "Init error: $error")
}
// Pay automatically initializes using your project's appId + packageName
```

## Payment Link Detection

```kotlin
fun handleUri(uri: String) {
    if (WalletKit.Pay.isPaymentLink(uri)) {
        processPaymentLink(uri)
    } else {
        WalletKit.pair(Wallet.Params.Pair(uri))
    }
}
```

## Get Payment Options

```kotlin
val result = WalletKit.Pay.getPaymentOptions(
    paymentLink = uri,
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
    val options = response.options          // List<PaymentOption>
    val info = response.info                // merchant name, amount, expiresAt
}
result.onFailure { error -> handleError(error) }
```

## Get Required Actions

```kotlin
val actionsResult = WalletKit.Pay.getRequiredPaymentActions(
    Wallet.Params.RequiredPaymentActions(
        paymentId = paymentId,
        optionId = selectedOption.id
    )
)

actionsResult.onSuccess { actions ->
    // actions: List<Wallet.Model.RequiredAction.WalletRpc>
    // Each has: chainId, method ("eth_signTypedData_v4"), params
}
```

## Signing (EIP-712)

```kotlin
import org.web3j.crypto.StructuredDataEncoder
import org.web3j.crypto.Sign
import org.web3j.crypto.ECKeyPair

fun signTypedDataV4(rpc: Wallet.Model.WalletRpcAction): String {
    val paramsArray = JSONArray(rpc.params)
    val typedData = paramsArray.getString(1)   // index 1 is the typed data JSON
    val encoder = StructuredDataEncoder(typedData)
    val hash = encoder.hashStructuredData()
    val keyPair = ECKeyPair.create(privateKeyBytes)
    val sig = Sign.signMessage(hash, keyPair, false)
    return buildHexSignature(sig)
}

// Sign all actions in order — order must match actions array
val signatures = actions.map { action ->
    when (action) {
        is Wallet.Model.RequiredAction.WalletRpc -> signTypedDataV4(action.action)
    }
}
```

## Data Collection WebView

```kotlin
// Check per-option, not globally
selectedOption.collectData?.let { collectAction ->
    val prefillBase64 = buildPrefill(mapOf(
        "fullName" to "John Doe",
        "dob" to "1990-01-15"
    ))
    val url = Uri.parse(collectAction.url).buildUpon()
        .appendQueryParameter("prefill", prefillBase64)
        .build().toString()
    showDataCollectionWebView(url)
}

fun buildPrefill(data: Map<String, String>): String =
    Base64.encodeToString(
        JSONObject(data).toString().toByteArray(),
        Base64.NO_WRAP or Base64.URL_SAFE
    )
```

WebView JavaScript interface:
```kotlin
addJavascriptInterface(
    object {
        @JavascriptInterface
        fun onDataCollectionComplete(json: String) {
            when (JSONObject(json).optString("type")) {
                "IC_COMPLETE" -> proceedToConfirmPayment()
                "IC_ERROR" -> handleError(JSONObject(json).optString("error"))
            }
        }
    },
    "AndroidWallet"
)
```

## Confirm Payment

```kotlin
val confirmResult = WalletKit.Pay.confirmPayment(
    Wallet.Params.ConfirmPayment(
        paymentId = paymentId,
        optionId = selectedOption.id,
        signatures = signatures
        // Do NOT pass collectedData — WebView handles this internally
    )
)

confirmResult.onSuccess { response ->
    when (response.status) {
        Wallet.Model.PaymentStatus.SUCCEEDED      -> showSuccess()
        Wallet.Model.PaymentStatus.PROCESSING     -> showProcessing()
        Wallet.Model.PaymentStatus.FAILED         -> showFailure()
        Wallet.Model.PaymentStatus.EXPIRED        -> showExpired()
        Wallet.Model.PaymentStatus.REQUIRES_ACTION -> handleAdditionalAction()
    }
}
```

## Error Types

```kotlin
is Wallet.Model.PaymentError.PaymentNotFound   -> "Payment not found"
is Wallet.Model.PaymentError.PaymentExpired    -> "Payment expired"
is Wallet.Model.PaymentError.InvalidAccount    -> "Invalid account format"
is Wallet.Model.PaymentError.ComplianceFailed  -> "Compliance check failed"
is Wallet.Model.PaymentError.InvalidSignature  -> "Invalid signature"
is Wallet.Model.PaymentError.Http              -> "Network error: ${error.message}"
```
