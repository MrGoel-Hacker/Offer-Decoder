# Dodo Payments setup

## What this change does

| Customer billing country | Original pack | Introductory pack (75% off) | Reports |
| --- | --- | --- | --- |
| United States | $20 | **$5 USD total** | 3 |
| India | ₹500 | **₹125 INR total** | 3 |

The final prices include applicable taxes. This is a one-time purchase, available once per Google account across both regions. No subscription is created. Pricing after the first pack is not configured; after three credits are used, users can access their existing reports but cannot purchase the introductory pack again.

**Previewing/decoding remains free. Saving a new report consumes one credit.** Reopening or explicitly sharing that saved report costs no additional credits. Deleting it does not refund a credit. Existing saved reports retain their current access rules. Saved reports still expire after 90 days; unused credits have no automatic expiry.

## 1. Create two products in Dodo's test dashboard

Create two **one-time** products with these exact final prices:

- US: USD **5.00** (500 cents), **tax inclusive**.
- India: INR **125.00** (12,500 paise), **tax inclusive**.

The app displays the original prices and 75% introductory saving. The Dodo products already contain the discounted prices: do not apply another coupon. Disable product discounts, purchasing power parity, adaptive/localized pricing, and pay-what-you-want. The backend checks product configuration before opening checkout and verifies the final amount, currency, product, quantity, and billing country when payment succeeds.

Copy the two product IDs. Use test keys with test products; live IDs are separate.

## 2. Configure the backend

Add these to your backend's private environment (Render → service → Environment, or `backend/.env` locally):

```dotenv
APP_PUBLIC_URL=https://offerdecoder.online
DODO_PAYMENTS_ENVIRONMENT=test_mode
DODO_PAYMENTS_API_KEY=<test API key>
DODO_PAYMENTS_WEBHOOK_KEY=<webhook signing secret>
DODO_PRODUCT_ID_US=<US test product ID>
DODO_PRODUCT_ID_IN=<India test product ID>
```

Keep your existing MongoDB and Google sign-in configuration. Do not put these secrets in React environment variables, GitHub commits, or chat. For local development set `APP_PUBLIC_URL=http://localhost:3000` and use a public HTTPS tunnel to the backend for webhook delivery.

Install the updated `backend/requirements.txt` and build the frontend. Render's existing build command already does both. Without payment configuration, pricing remains visible and checkout reports that payments are unavailable; new report saves still require credits, so configure and test payments before releasing this change to users.

## 3. Register the webhook

In Dodo's matching test environment, register:

```text
https://offerdecoder.online/api/billing/webhook
```

Subscribe to `payment.succeeded` and `refund.succeeded`. Copy the endpoint's signing secret into `DODO_PAYMENTS_WEBHOOK_KEY` and restart the backend. No bearer authentication is required for this endpoint; it verifies Dodo's signature and timestamp against the raw body.

Credits are granted only from a verified webhook, never from redirect query parameters. Duplicate deliveries grant no extra credits. Any successful refund, including a partial refund, removes the account's remaining pack credits, preserves existing reports, and prevents a replayed success event from restoring credits. Refund handling retrieves the payment from Dodo to resolve the original order, including when events arrive out of order.

## 4. Test before switching to live

1. Sign in with a test Google account and open `/billing`.
2. Choose the real customer billing country, independently of the offer-letter country. Confirm that checkout shows $5 USD or ₹125 INR total.
3. Complete Dodo's test payment flow. Confirm that the return page eventually shows three credits and that the webhook delivery succeeds in Dodo's dashboard.
4. Save three distinct reports. The fourth save should request credits. Reopening and sharing should still work. Retry a save or resend the webhook: neither should change the balance again.
5. With another test account, verify cancellation and an unsuccessful payment grant no credits. Verify a refund removes unused credits.

Checkout from an unsaved report opens in another tab so the original result stays available. Keep that report tab open, then return to save after payment. No offer-letter draft is written to browser storage.

Concurrent checkout creation is locked in MongoDB. Repeated checkout attempts reuse the same hosted session. An unpaid expired session can be refreshed after 24 hours plus a safety minute; a session with an unsettled payment cannot be replaced. An account's first checkout fixes its billing region; it cannot open a competing introductory checkout in the other region.

### Automated checks

```bash
cd backend
pip install -r requirements.txt
pip install pytest pytest-xdist mongomock-motor
pytest tests/test_billing.py tests/test_auth.py tests/test_quickscan_us.py tests/test_us_decoder.py
cd ../frontend
yarn install --frozen-lockfile
GENERATE_SOURCEMAP=false yarn build
```

The billing tests use a fake MongoDB with the real Dodo SDK, HTTP mock transport, and actual signed webhook payloads. They make no payment requests. The existing live API suite still needs a running backend and MongoDB; its report tests seed test credits directly.

## 5. Go live

Create the two equivalent live-mode products and a live webhook endpoint, then replace all four Dodo credentials/product values with their live counterparts and set `DODO_PAYMENTS_ENVIRONMENT=live_mode`. Use your actual HTTPS `APP_PUBLIC_URL`, rebuild/deploy the reviewed code, and complete a small real checkout/refund to verify your account configuration.

Do not mix test and live purchases in the production database: introductory purchase eligibility is stored per account. Use a separate database for staging/test-mode payments.

## API and database notes

- `GET /api/billing/packs`: public prices and configuration availability.
- `GET /api/billing/status`: authenticated credit balance and purchase/refund status.
- `POST /api/billing/checkout`: authenticated body `{"region":"in"}` or `{"region":"us"}`. Returns `checkoutUrl`.
- `POST /api/billing/webhook`: signed Dodo events.
- `POST /api/reports`: now requires a UUID `requestId` as well as the existing report data. Reuse that ID for retries of the same payload. A changed payload needs a fresh ID. No credits returns HTTP 402.

No manual database migration is required. Orders use MongoDB's unique `_id` and new billing fields are added to users as needed. The credit debit and report-save reservation are one atomic user-document update. A failed report insert can be retried with the same request ID without another debit. This works on standalone MongoDB as well as Atlas. Reservation records retain only an ID, payload hash, and creation timestamp, not report contents.

References: [Dodo checkout sessions](https://docs.dodopayments.com/developer-resources/checkout-session), [official Python SDK](https://github.com/dodopayments/dodopayments-python).
