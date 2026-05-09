# Platform Account Operations and Real Campaign Creation Plan

Date: 2026-05-09

This plan covers two immediate product tracks:

1. Migrate the Blue Whale-style ad account operation capabilities into ANIFORCE.
2. Build the frontend-to-API workflow that connects Meta/Google credentials and creates a real campaign in the ad platform.

## 1. Product Scope

### Track A: Meta Ad Account Operations

The useful Blue Whale functions for ANIFORCE are not order-marketplace features. The core value is account resource operations that support real media buying:

- Open account
- Recharge
- Clear balance / clearing request
- Bind BM / asset
- Recycle account
- Track account status, spend range, balance, BMID, timezone, token state, remark

Phase 1 focuses on Meta because the user need is explicit and Meta API creation is already partially proven.

### Track B: Real Platform Authorization and Campaign Creation

The first complete loop should be:

```text
Frontend starts Meta Business OAuth
-> Meta redirects back with authorization code
-> Backend exchanges code for access token
-> Backend exchanges short-lived token for long-lived token when app secret is configured
-> Backend syncs /me/adaccounts
-> User selects account in create campaign flow
-> Backend calls Meta Marketing API
-> Meta account shows the new Campaign
-> Local system stores a campaign record with remote_campaign_id
```

Google should be prepared in the data model/API, but the first real push should be Meta because Google campaign creation requires stricter developer token, customer ID, and account hierarchy configuration.

## 2. Current Implementation Started

Implemented in this iteration:

- `PlatformAccount` and `PlatformAccountOperation` backend models.
- SQLite-backed `/api/v1/platform/*` API replacing the previous in-memory mock.
- Production OAuth connection endpoints:
  - `POST /api/v1/platform/connect?platform=meta`
  - `GET /api/v1/platform/meta/oauth/callback`
- Internal token import endpoint retained for migration/debugging:
  - `POST /api/v1/platform/connect-token`
- Platform account list:
  - `GET /api/v1/platform/accounts`
- Account operation endpoint:
  - `POST /api/v1/platform/accounts/{account_id}/operations`
- Account operation types:
  - `open`
  - `recharge`
  - `clear`
  - `bind`
  - `recycle`
- Real Meta campaign creation endpoint:
  - `POST /api/v1/platform/meta/campaigns`
- Frontend page:
  - `/platform-accounts`
- Sidebar entry:
  - 广告账户
- New campaign flow enhancement:
  - Select Meta platform
  - Select connected Meta ad account
  - Submit directly to real Meta Campaign creation
  - Submit to real Meta API

## 3. Meta Configuration Required

For real Meta creation, the runtime environment needs:

- `META_APP_ID`
- `META_APP_SECRET`
- `META_OAUTH_REDIRECT_URI`
- `FRONTEND_BASE_URL`
- Meta OAuth permissions:
  - `ads_management`
  - `ads_read`
  - `business_management`
- A Meta ad account where this user/token has campaign creation permission

The Meta App dashboard must include the backend callback URL in Valid OAuth Redirect URIs. The frontend should not ask normal users to paste tokens; manual token import is only kept as an internal migration/debug path.

## 4. User Flow

### Connect Meta Account

1. Open `http://localhost:3010/platform-accounts`.
2. Click `连接 Meta Business`.
3. Log in and authorize in Meta.
4. Meta redirects to backend callback with `code` and `state`.
5. Backend exchanges token and calls `/me/adaccounts`.
6. System saves all authorized ad accounts and returns to the account page.

### Operate Account

On the account table:

- `充值`: increases local balance / available balance and creates operation record.
- `清零`: clears local balance / available balance and marks account as `cleared`.
- `绑定`: writes BMID / asset target.
- `回收`: marks account as `recycled`.
- `断开`: removes token and marks account as disconnected.

### Create Real Meta Campaign

1. Open create campaign flow.
2. Select project.
3. Select platform `Meta`.
4. Select connected Meta account.
5. Complete campaign fields.
6. Submit.
7. Backend calls Meta API:
   - `/{act_account_id}/campaigns`
8. Backend stores local campaign config:
   - `platform_account_id`
   - `remote_campaign_id`
   - `remote_platform`
   - `objective`
   - `budget_type`

## 5. Remaining Work

### Must Do Next

- Add Alembic migration for `platform_accounts` and `platform_account_operations`.
- Add UI for account operation history.
- Add Meta error display with original platform error payload, not only generic message.
- Add one-click sync for Meta accounts from saved token.
- Add account selector into local-only campaign flow so draft records also know target platform account.
- Add `remote_campaign_id` as a first-class campaign field or consistently store it in `config`.

### Before Production

- Encrypt tokens at rest.
- Add permission levels for who can create real platform campaigns.
- Add explicit "confirm before spending" guard.
- Add spend caps per account and per operator.
- Add audit logs for all platform write operations.
- Add OAuth callback with configured redirect domain.
- Add Google account/customer connection flow:
  - developer token
  - customer ID
  - login customer ID
  - refresh token

## 6. Recommended Development Order

1. Run and verify Meta token connection with a real token.
2. Create a paused Meta Campaign in a real ad account.
3. Persist and display remote campaign ID in campaign detail.
4. Add operation history drawer to `/platform-accounts`.
5. Add account sync action and health status.
6. Add Google credential form and account/customer validation.
7. Build ad set / ad / creative upload creation after campaign-level creation is stable.
