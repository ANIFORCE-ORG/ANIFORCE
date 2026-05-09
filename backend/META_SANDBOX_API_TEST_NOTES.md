# Meta Sandbox API Test Notes

Date: 2026-05-09

This note records the current Meta Marketing API integration status, sandbox test result, and known blockers for future API handoff.

## 1. Test Inputs

Meta sample code provided:

- App ID: `1293993012834979`
- Sandbox ad account ID: `1943996592887453`
- System account ID format: `act_1943996592887453`
- Access token: provided by the user and saved locally through the platform connection sandbox import flow.
- Intended Campaign objective: `OUTCOME_TRAFFIC`
- Intended Campaign status: `PAUSED`
- Intended buying type: `AUCTION`
- Intended special ad categories: `[]`

Do not commit or share raw access tokens. The token used in this test is sensitive and should be rotated before production usage.

## 2. Implemented API Flow

### Platform Connection

The system now separates platform connection from ad account resource management.

- Platform connection page:
  - `http://127.0.0.1:3010/platform-connections`
- Ad account management page:
  - `http://127.0.0.1:3010/platform-accounts`

Backend endpoints:

- `GET /api/v1/platform/connections/meta/config`
- `PUT /api/v1/platform/connections/meta/config`
- `POST /api/v1/platform/connect?platform=meta`
- `GET /api/v1/platform/meta/oauth/callback`
- `POST /api/v1/platform/connect-token`
- `GET /api/v1/platform/accounts`
- `POST /api/v1/platform/meta/campaigns`

### Sandbox Token Import

For sandbox/internal testing, the platform connection page includes a "开发 / 沙盒 Token 导入" area.

This imports a Meta token and sandbox ad account into the system without putting token input inside the ad account management page.

The sandbox account was imported successfully:

```json
{
  "platform": "meta",
  "account_id": "act_1943996592887453",
  "account_name": "Meta Sandbox Ad Account",
  "status": "active",
  "source_type": "sandbox-token-import",
  "has_token": true
}
```

## 3. OAuth / HTTPS Findings

Facebook Login rejected the original local HTTP callback:

```text
http://127.0.0.1:8010/api/v1/platform/meta/oauth/callback
```

Error observed:

```text
Facebook detected that aniforce is not using a secure connection.
```

To address this locally, a self-signed HTTPS backend was started:

```text
https://localhost:8443
```

Current local callback:

```text
https://localhost:8443/api/v1/platform/meta/oauth/callback
```

Meta App dashboard must contain:

- App Domains:
  - `localhost`
- Valid OAuth Redirect URIs:
  - `https://localhost:8443/api/v1/platform/meta/oauth/callback`

If Meta rejects local self-signed HTTPS, use one of:

- ngrok with verified account and authtoken
- Cloudflare Tunnel
- a real HTTPS staging domain

Local ngrok was present but not usable:

```text
ERR_NGROK_4018: Usage of ngrok requires a verified account and authtoken.
```

## 4. Campaign Creation Test

Test endpoint:

```http
POST /api/v1/platform/meta/campaigns
```

Test payload:

```json
{
  "platform_account_id": "9924b13d-c6f2-4a77-bf61-2a07a4cc5f11",
  "project_id": "5712c180-b67e-4aff-a388-79024da34bd3",
  "name": "ANIFORCE Sandbox Campaign 2",
  "objective": "OUTCOME_TRAFFIC",
  "status": "PAUSED",
  "budget": 10,
  "budget_type": "daily",
  "special_ad_categories": [],
  "create_local_record": true
}
```

Backend sends Meta API params equivalent to the Java sample:

```text
name=ANIFORCE Sandbox Campaign 2
objective=OUTCOME_TRAFFIC
status=PAUSED
buying_type=AUCTION
special_ad_categories=[]
daily_budget=1000
```

Result:

```json
{
  "detail": "Meta campaign creation failed: TimeoutError"
}
```

## 5. Current Blocker

The local backend can run and the system API flow is wired correctly, but requests to Meta Graph API time out from this machine/network.

Known symptoms:

- Previous Meta API test report also showed `graph.facebook.com` timeout.
- Sandbox token import eventually succeeded by falling back to the provided account ID after Meta account sync could not complete quickly.
- Campaign creation reaches the Meta adapter but times out before Meta returns a Campaign ID.

This is a network reachability issue, not a local request shape issue.

Required external connectivity:

```text
https://graph.facebook.com
```

## 6. What Has Been Verified

- Backend service starts on:
  - `http://127.0.0.1:8010`
  - `https://localhost:8443`
- Frontend build passes with `npm exec vite build`.
- Platform connection page opens.
- Sandbox token import UI exists.
- Sandbox account is persisted in SQLite.
- Campaign creation endpoint reaches the Meta connector.
- Campaign payload now includes `buying_type=AUCTION`.
- Empty exception messages were fixed; timeout now returns `TimeoutError`.

## 7. Recommended Next Steps

1. Test from a network/server that can access `graph.facebook.com`.
2. Prefer a real HTTPS staging domain for OAuth callback instead of local self-signed HTTPS.
3. If testing locally, configure ngrok:

   ```bash
   ngrok config add-authtoken <token>
   ngrok http 8010
   ```

   Then set the generated HTTPS URL as:

   ```text
   https://<ngrok-domain>/api/v1/platform/meta/oauth/callback
   ```

4. Rotate the sample access token before sharing with a broader team.
5. Add token encryption before production.
6. After Campaign creation succeeds, extend the flow to create:
   - Ad Set
   - Creative
   - Ad

