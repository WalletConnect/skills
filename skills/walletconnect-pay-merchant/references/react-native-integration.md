# React Native Integration

> Use this when building a mobile POS terminal, payment kiosk, or any React Native app that creates USDC payment requests and displays QR codes for customers to scan and pay.

## When to Choose React Native

- Building a mobile point-of-sale (POS) terminal
- Want to display QR codes on a device screen for in-person payments
- Need a native mobile app with payment creation + status polling
- Building a merchant-facing mobile app with transaction history

## Requirements

- React Native 0.73+ or Expo 50+
- TypeScript recommended
- `@tanstack/react-query` for data fetching and polling
- `zustand` for state management (optional but recommended)

## Installation

```bash
npm install @tanstack/react-query zustand react-native-qrcode-svg
```

For secure API key storage (recommended):
```bash
# Expo
npx expo install expo-secure-store

# Bare React Native (alternative)
npm install react-native-keychain
```

Store API keys using `expo-secure-store` (Expo) or `react-native-keychain` (bare RN) rather than AsyncStorage or environment variables bundled into the app. This ensures credentials are encrypted at rest on the device.

---

## Environment / Configuration

Store merchant credentials securely. Never hardcode API keys.

```typescript
// For Expo, use env vars prefixed with EXPO_PUBLIC_
EXPO_PUBLIC_API_URL=<api-base-url>
EXPO_PUBLIC_DEFAULT_MERCHANT_ID=<your-merchant-id>
EXPO_PUBLIC_DEFAULT_CUSTOMER_API_KEY=<your-customer-api-key>
```

---

## Type Definitions

```typescript
// types.ts
export type PaymentStatus =
  | "requires_action"
  | "processing"
  | "succeeded"
  | "failed"
  | "expired"
  | "cancelled";

export interface StartPaymentRequest {
  referenceId: string;
  amount: {
    value: string; // cents as string
    unit: string;  // "iso4217/USD"
  };
}

export interface StartPaymentResponse {
  paymentId: string;
  gatewayUrl: string;
  expiresAt: number | null;
}

export interface PaymentStatusResponse {
  status: PaymentStatus;
  isFinal: boolean;
  pollInMs: number;
}

export interface DisplayAmount {
  formatted?: string;
  assetSymbol?: string;
  decimals?: number;
  iconUrl?: string;
  networkName?: string;
}

export interface AmountWithDisplay {
  unit?: string;
  value?: string;
  display?: DisplayAmount;
}

export interface BuyerInfo {
  accountCaip10?: string;
  accountProviderName?: string;
  accountProviderIcon?: string;
}

export interface TransactionInfo {
  networkId?: string;
  hash?: string;
  nonce?: number;
}

export interface SettlementInfo {
  status?: string;
  txHash?: string;
}

export interface PaymentRecord {
  paymentId: string;
  merchantId?: string;
  referenceId?: string;
  status: PaymentStatus;
  isTerminal: boolean;
  fiatAmount?: AmountWithDisplay;
  tokenAmount?: AmountWithDisplay;
  buyer?: BuyerInfo;
  transaction?: TransactionInfo;
  settlement?: SettlementInfo;
  createdAt?: string;
  lastUpdatedAt?: string;
  settledAt?: string;
}

export interface TransactionsResponse {
  data: PaymentRecord[];
  nextCursor?: string | null;
}
```

---

## API Client

```typescript
// services/client.ts
const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL;

const DEFAULT_TIMEOUT_MS = 30000;

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: { method?: string; body?: unknown; headers?: Record<string, string>; timeout?: number } = {}
  ): Promise<T> {
    const { body, headers, method = "GET", timeout = DEFAULT_TIMEOUT_MS } = options;
    const url = `${this.baseUrl.replace(/\/+$/, "")}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json", ...headers },
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP error ${response.status}`);
      }

      return response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === "AbortError") {
        throw new Error(`Request timeout after ${timeout}ms`);
      }
      throw error;
    }
  }

  get<T>(endpoint: string, options?: { headers?: Record<string, string> }) {
    return this.request<T>(endpoint, options);
  }

  post<T>(endpoint: string, body?: unknown, options?: { headers?: Record<string, string> }) {
    return this.request<T>(endpoint, { ...options, method: "POST", body });
  }
}

export const apiClient = new ApiClient(API_BASE_URL!);

export function getApiHeaders(merchantId: string, customerApiKey: string): Record<string, string> {
  return {
    "Api-Key": customerApiKey,
    "Merchant-Id": merchantId,
    "Sdk-Name": "pos-device",
    "Sdk-Version": "1.0.0",
    "Sdk-Platform": "react-native",
  };
}
```

---

## Payment Service

```typescript
// services/payment.ts
import { StartPaymentRequest, StartPaymentResponse, PaymentStatusResponse } from "./types";
import { apiClient, getApiHeaders } from "./client";

export async function startPayment(
  request: StartPaymentRequest,
  merchantId: string,
  apiKey: string
): Promise<StartPaymentResponse> {
  return apiClient.post<StartPaymentResponse>(
    "/merchant/payment",
    request,
    { headers: getApiHeaders(merchantId, apiKey) }
  );
}

export async function getPaymentStatus(
  paymentId: string,
  merchantId: string,
  apiKey: string
): Promise<PaymentStatusResponse> {
  return apiClient.get<PaymentStatusResponse>(
    `/merchant/payment/${paymentId}/status`,
    { headers: getApiHeaders(merchantId, apiKey) }
  );
}

export async function cancelPayment(
  paymentId: string,
  merchantId: string,
  apiKey: string
): Promise<void> {
  await apiClient.post(
    `/payments/${paymentId}/cancel`,
    {},
    { headers: getApiHeaders(merchantId, apiKey) }
  );
}
```

---

## Transaction Service

```typescript
// services/transactions.ts
import { TransactionsResponse } from "./types";

export interface GetTransactionsOptions {
  status?: string | string[];
  sortBy?: "date" | "amount";
  sortDir?: "asc" | "desc";
  limit?: number;
  cursor?: string;
  startTs?: string;
  endTs?: string;
}

export async function getTransactions(
  merchantId: string,
  apiKey: string,
  options: GetTransactionsOptions = {}
): Promise<TransactionsResponse> {
  const params = new URLSearchParams();

  if (options.status) {
    const statuses = Array.isArray(options.status) ? options.status : [options.status];
    statuses.forEach((s) => params.append("status", s));
  }
  if (options.sortBy) params.append("sortBy", options.sortBy);
  if (options.sortDir) params.append("sortDir", options.sortDir);
  if (options.limit) params.append("limit", options.limit.toString());
  if (options.cursor) params.append("cursor", options.cursor);
  if (options.startTs) params.append("startTs", options.startTs);
  if (options.endTs) params.append("endTs", options.endTs);

  const qs = params.toString();
  const url = `${process.env.EXPO_PUBLIC_API_URL}/merchants/payments${qs ? `?${qs}` : ""}`;

  const response = await fetch(url, {
    headers: getApiHeaders(merchantId, apiKey),
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : {};

  if (!response.ok) {
    throw new Error(data.message || `Failed to fetch transactions: ${response.status}`);
  }

  return data;
}
```

---

## React Query Hooks

### useStartPayment

```typescript
import { useMutation } from "@tanstack/react-query";
import { startPayment } from "./payment";

export function useStartPayment(merchantId: string, apiKey: string) {
  return useMutation({
    mutationFn: (request: StartPaymentRequest) =>
      startPayment(request, merchantId, apiKey),
  });
}
```

### usePaymentStatus (with smart polling)

This is the key hook — it polls the API and stops automatically when the payment is final.

```typescript
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { getPaymentStatus } from "./payment";
import { PaymentStatusResponse } from "./types";

const KNOWN_STATUSES = ["requires_action", "processing", "succeeded", "failed", "expired", "cancelled"];

function normalizePaymentStatus(data: PaymentStatusResponse): PaymentStatusResponse {
  if (!KNOWN_STATUSES.includes(data.status)) {
    return { ...data, status: "failed", isFinal: true };
  }
  return data;
}

export function usePaymentStatus(
  paymentId: string | null,
  merchantId: string,
  apiKey: string,
  options: {
    enabled?: boolean;
    onTerminalState?: (data: PaymentStatusResponse) => void;
  } = {}
) {
  const { enabled = true, onTerminalState } = options;
  const hasCalledCallback = useRef(false);
  const callbackRef = useRef(onTerminalState);

  useEffect(() => { callbackRef.current = onTerminalState; }, [onTerminalState]);
  useEffect(() => { hasCalledCallback.current = false; }, [paymentId]);

  const query = useQuery<PaymentStatusResponse, Error>({
    queryKey: ["paymentStatus", paymentId],
    queryFn: async () => {
      if (!paymentId) throw new Error("Payment ID required");
      const data = await getPaymentStatus(paymentId, merchantId, apiKey);
      return normalizePaymentStatus(data);
    },
    enabled: enabled && !!paymentId,
    refetchOnWindowFocus: false,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.isFinal) return false;

      const pollInMs = data?.pollInMs;
      if (typeof pollInMs !== "number" || !Number.isFinite(pollInMs) || pollInMs <= 0) {
        return 2000;
      }
      return pollInMs;
    },
    retry: 3,
  });

  useEffect(() => {
    if (query.data?.isFinal && !hasCalledCallback.current && callbackRef.current) {
      hasCalledCallback.current = true;
      callbackRef.current(query.data);
    }
  }, [query.data]);

  return query;
}
```

### useTransactions (with infinite scroll)

```typescript
import { useInfiniteQuery } from "@tanstack/react-query";
import { getTransactions, GetTransactionsOptions } from "./transactions";

type FilterType = "all" | "pending" | "completed" | "failed" | "expired" | "cancelled";

function filterToStatusArray(filter: FilterType): string[] | undefined {
  switch (filter) {
    case "pending": return ["requires_action", "processing"];
    case "completed": return ["succeeded"];
    case "failed": return ["failed"];
    case "expired": return ["expired"];
    case "cancelled": return ["cancelled"];
    default: return undefined;
  }
}

export function useTransactions(
  merchantId: string,
  apiKey: string,
  options: { enabled?: boolean; filter?: FilterType; startTs?: string; endTs?: string } = {}
) {
  const { enabled = true, filter = "all", startTs, endTs } = options;

  const query = useInfiniteQuery({
    queryKey: ["transactions", filter, startTs, endTs],
    queryFn: ({ pageParam }) =>
      getTransactions(merchantId, apiKey, {
        status: filterToStatusArray(filter),
        sortBy: "date",
        sortDir: "desc",
        limit: 20,
        cursor: pageParam as string | undefined,
        startTs,
        endTs,
      }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
    enabled,
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    retry: 2,
  });

  const transactions = query.data?.pages.flatMap((page) => page.data) ?? [];

  return { ...query, transactions };
}
```

---

## Amount Utilities

```typescript
// utils/currency.ts

/** Convert dollar amount to cents string. Uses Math.round to avoid floating-point issues. */
export const amountToCents = (amount: string): string =>
  Math.round(parseFloat(amount) * 100).toString();

/** Check if cents would overflow u64 (API limit) */
export function exceedsU64Max(dollarAmount: string): boolean {
  if (!dollarAmount || dollarAmount === ".") return false;
  const parts = dollarAmount.includes(".") ? dollarAmount.split(".") : [dollarAmount];
  const whole = (parts[0] || "0").replace(/^0+/, "") || "0";
  const fractional = (parts[1] || "").padEnd(2, "0").slice(0, 2);
  return BigInt(whole + fractional) > BigInt("18446744073709551615");
}

/** Format cents string to display string: "500" → "$5.00" */
export function formatFiatAmount(amountCents?: string, currency = "USD"): string {
  if (!amountCents) return "-";
  const parsed = parseInt(amountCents, 10);
  if (isNaN(parsed)) return "-";
  const value = (parsed / 100).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return currency === "EUR" ? `${value}€` : `$${value}`;
}
```

---

## QR Code Screen (Payment Flow)

```tsx
// screens/ScanScreen.tsx
import { useEffect } from "react";
import { View, Text, ActivityIndicator } from "react-native";
import QRCode from "react-native-qrcode-svg";
import { useStartPayment, usePaymentStatus, useCancelPayment } from "./hooks";
import { amountToCents } from "./currency";

export function ScanScreen({
  amount,
  merchantId,
  apiKey,
  onSuccess,
  onFailure,
}: {
  amount: string;
  merchantId: string;
  apiKey: string;
  onSuccess: (paymentId: string) => void;
  onFailure: (status: string) => void;
}) {
  const startPayment = useStartPayment(merchantId, apiKey);
  const cancelPayment = useCancelPayment();

  // Start payment on mount
  useEffect(() => {
    const referenceId = `pos-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    startPayment.mutate({
      referenceId,
      amount: { value: amountToCents(amount), unit: "iso4217/USD" },
    });
  }, []);

  const paymentId = startPayment.data?.paymentId ?? null;
  const gatewayUrl = startPayment.data?.gatewayUrl ?? "";

  // Poll status
  const { data: statusData } = usePaymentStatus(paymentId, merchantId, apiKey, {
    onTerminalState: (data) => {
      if (data.status === "succeeded") {
        onSuccess(paymentId!);
      } else {
        onFailure(data.status);
      }
    },
  });

  // Cancel on unmount if still pending
  useEffect(() => {
    return () => {
      if (paymentId && statusData?.status === "requires_action") {
        cancelPayment.mutate(paymentId);
      }
    };
  }, [paymentId, statusData?.status]);

  if (startPayment.isPending) {
    return <ActivityIndicator size="large" />;
  }

  if (startPayment.isError) {
    return <Text>Error: {startPayment.error.message}</Text>;
  }

  const isProcessing = statusData?.status === "processing";

  return (
    <View style={{ alignItems: "center", padding: 24 }}>
      <Text style={{ fontSize: 24, fontWeight: "bold", marginBottom: 16 }}>
        ${amount} USDC
      </Text>

      {isProcessing ? (
        <View style={{ alignItems: "center" }}>
          <ActivityIndicator size="large" />
          <Text>Processing payment...</Text>
        </View>
      ) : (
        <View>
          <QRCode value={gatewayUrl} size={256} />
          <Text style={{ marginTop: 8, textAlign: "center", color: "#666" }}>
            Scan to pay
          </Text>
        </View>
      )}
    </View>
  );
}
```

---

## App Setup (React Query Provider)

```tsx
// App.tsx or _layout.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000 },
  },
});

export default function App({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
```

---

## Key Patterns

| Pattern | Implementation |
|---------|---------------|
| Secure credential storage | Use `expo-secure-store` for API keys, never AsyncStorage |
| Smart polling | Use `refetchInterval` that reads `pollInMs` from API response |
| Status normalization | Map unknown statuses to `"failed"` with `isFinal: true` |
| Amount in cents | Always convert with `Math.round(dollars * 100)` — avoids floating-point |
| Cancel on unmount | Cancel pending payments when user navigates away |
| Infinite scroll transactions | Use `useInfiniteQuery` with cursor-based pagination |
| Timeout handling | AbortController with 30s timeout on all API calls |

---

## Key Differences from Next.js Integration

| | React Native | Next.js |
|---|---|---|
| API calls | Direct from device (native fetch) | Via API routes (keys server-side) |
| Credential storage | `expo-secure-store` (encrypted on device) | `.env.local` (server-side only) |
| QR code | `react-native-qrcode-svg` component | `qrcode` package (PNG buffer) |
| Polling | `@tanstack/react-query` `refetchInterval` | `useEffect` + `setTimeout` |
| State management | `zustand` with `react-native-mmkv` | React state or server components |
