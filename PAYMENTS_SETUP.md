# Dodo Payments: one report per purchase

Launch pricing: India INR 125 (reference price INR 500); USA USD 5
(reference price USD 20). These are one-time purchases, not subscriptions.
The report's selected country (India or USA) determines its salary and tax rules.
Billing country selects the checkout product and currency independently.

## Configure and test

1. In Dodo **test mode**, create two one-time products at the final launch prices:
   - India: INR 125 (`12500` paise).
   - USA: USD 5 (`500` cents).
   Disable pay-what-you-want, PPP, localized prices, additional discounts and
   customer-editable quantities. These two products use their base currency.
   Do not apply another 75% discount: the launch discount is already in the price.
2. In the Render service's Environment settings, add these values securely:

   ```text
   APP_PUBLIC_URL=https://offerdecoder.online
   DODO_PAYMENTS_ENVIRONMENT=test_mode
   DODO_PAYMENTS_API_KEY=<test API key; never commit or paste into chat>
   DODO_PRODUCT_IN=<India test product ID>
   DODO_PRODUCT_US=<USA test product ID>
   DODO_PAYMENTS_ENABLED=true
   DISABLE_ESLINT_PLUGIN=true
   ```

   Existing `MONGO_URL` and `DB_NAME` settings are also required. The Codex OAuth
   connection does not provide credentials to the deployed Render server.
3. Deploy the code. The Render build command must build React as well as install
   Python dependencies. `render.yaml` includes the combined command. For an
   existing service configured manually, copy its `buildCommand` into Render's
   Settings; editing the YAML alone does not update a non-Blueprint service.
   Also use the YAML's start command (`--no-access-log`) so Uvicorn does not log
   private bearer report links. Restrict access to any platform request logs.
   `DISABLE_ESLINT_PLUGIN=true` avoids the existing CRA 5 / ESLint 9 build-plugin
   incompatibility. It skips build-time linting, not compilation.
4. Test both country choices using Dodo test payment details. Confirm success,
   cancellation, pending payment, revisiting a purchased link, refund/revocation,
   and expiry. Do not pay again while a payment is pending.

## Before enabling real payments

Complete Dodo merchant approval, configure checkout tax treatment and currency
settings, and publish the required support/refund/privacy policies. Repeat the
product configuration in **live mode** using separate live product IDs. Put the
live API key and live product IDs into Render and change the environment to
`live_mode` only after the test checkout flow has passed.

Do not enable payments before these configuration steps. With
`DODO_PAYMENTS_ENABLED=false` (the default), the previous free flow stays active.
With it enabled but missing or invalid payment configuration, purchases fail
closed rather than silently serving paid reports for free.

## Fulfillment and privacy

- The backend saves an immutable report snapshot before redirecting to checkout.
  A purchase cannot be reused to decode another offer or change its salary inputs.
- The server retrieves its stored checkout session and payment from Dodo. Only a
  successful payment for the matching checkout, product, quantity, country and
  currency, meeting the stored price, can unlock the snapshot. No browser return
  parameters grant access. Refunds or disputes block future retrieval.
- This implementation uses authoritative server-side API reads for fulfillment;
  no webhook or webhook secret is required. Orders remain pending until the
  customer opens or revisits their private link, when verification is retried.
- Report links are bearer secrets: anyone who has a link can open it. Tokens are
  random, only their SHA-256 hashes are stored in MongoDB, responses are not cached,
  and checkout/report pages skip Clarity, PostHog and Emergent analytics scripts.
  Do not send private report URLs to analytics or include them in support logs.
- Offer details/results expire after 90 days. A link is saved in the current
  browser session for recovery. Bookmark the private purchased link for later.
  There is no email delivery or cross-device account recovery in this version.

## Offline regression checks

```text
python -m unittest discover -s backend/tests -p test_payments.py -v
```

These mock Dodo and MongoDB. They do not create products or charge cards. Existing
API regression tests assume the original free mode; run them with payments off.
