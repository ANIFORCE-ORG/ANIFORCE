# Blue Whale Feature Migration: Phase 1 Integration Design

## 1. Source System Summary

The reference system from `蓝鲸数字营销平台分析/采集结果` is an operations backend for cross-border advertising teams. It is centered on:

- Service market for ad-account rental
- Advertising account management
- Rental and recharge orders
- Business/BM asset management
- Funds, recharge, withdrawal, and financial ledger
- BI spend analysis

It is not primarily an optimization agent. Its strongest product value is operational control of ad account resources, funds, delivery status, and spend visibility.

For ANIFORCE, Phase 1 should not copy the whole order/finance/rental system. The right integration is to absorb the operational capabilities that support the agent-driven media-buying loop:

```text
Account assets -> spend visibility -> operational status -> agent diagnosis -> action queue
```

## 2. Blue Whale Functional Inventory

### 2.1 Home / Workbench

Observed functions:

- Greeting and user entry
- Service entry cards
- Account/fund shortcuts
- Notifications and work orders
- Language switch

Migration value:

- Low direct value for Phase 1.
- Useful as inspiration for Today View entry points.

ANIFORCE mapping:

- Replace workbench with `Today View`.
- Show: account health, spend anomalies, pending actions, sync status, budget warnings.

### 2.2 Service Market

Observed functions:

- Facebook rental market
- Account product cards
- Account type description: "三不限账户"
- Selling points: unlimited budget/domain/page, global account supply, 24/7 service
- "Rent now" flow

Migration value:

- If ANIFORCE becomes an account-resource platform, this matters.
- For Phase 1 agent product, keep only the concept of account supply/source metadata.

ANIFORCE mapping:

- Do not build a rental marketplace in Phase 1.
- Add account source/type fields to PlatformAccount:
  - owned
  - client-owned
  - agency-provided
  - rented
  - test/sandbox

### 2.3 Account Management

Observed functions:

- Platform filter: Facebook
- Spend range cards:
  - `$0-10`
  - `$10-100`
  - `$100-500`
  - `$500-1000`
  - `$1000-2000`
  - `$2000+`
- Each range shows total, normal, banned counts
- Account tabs:
  - Normal
  - Clearing
  - Banned
  - Cleared
  - Recycled
- Filters:
  - Account type
  - Account property
  - Account name / ID
  - Remark
  - Delivery time
- Table fields:
  - Account ID
  - Account name
  - Account type
  - Account property
  - BMID
  - Timezone
  - Accumulated spend
  - Delivery time
  - Remark
  - Updated time
  - Created time
  - Survival time
  - Usage time
  - Return time
  - Actions
- Row actions:
  - Recharge
  - Spend analysis
  - Transaction details
  - Clearing request
  - BM adjustment
- Export

Migration value:

This is the most important Blue Whale module for Phase 1. ANIFORCE needs durable platform account inventory, status, spend, and health.

ANIFORCE mapping:

- Build `PlatformAccount` model and page.
- Add account health/status to Today View.
- Feed account status into Agent diagnosis.
- Let Agent detect:
  - banned/disabled account
  - stale sync
  - zero spend account
  - high spend account without conversions
  - account balance/credit risk
  - timezone mismatch
  - account unused after delivery/connect

### 2.4 Order Management

Observed functions:

- Rental order management
- Recharge order management
- Platform tabs: All / Facebook
- Delivery tabs:
  - Normal delivery
  - Abnormal delivery
- Order status cards:
  - Total orders
  - Delivering
  - Pending confirmation
  - Paid
- Filters:
  - Order number
  - Business number
  - Created time
  - Completed time
- Table fields:
  - Order number
  - Platform
  - Account type
  - Account property
  - Timezone
  - Business number
  - Ad industry
  - Order amount
  - Payment status
  - Delivery status
  - Remark
  - Refund reason
  - Created time
  - Completed time
  - Operation
- Row action: extract account

Migration value:

Order management is only necessary if ANIFORCE handles account procurement or wallet recharge. It is not required for the first agent optimization loop.

ANIFORCE mapping:

- Do not build full order management in Phase 1.
- Add lightweight `AccountProvisioningRecord` only if account resources are supplied internally.
- Keep fields:
  - source order id
  - platform
  - account type
  - account property
  - timezone
  - delivery status
  - delivered account id
  - remark

### 2.5 Asset Management

Observed functions:

- Business number / BM management
- Platform filter
- Time filter
- Business number type
- Table fields:
  - Platform
  - Business number type
  - Business number / BMID
  - Added time
  - Edit / delete

Migration value:

Useful for Meta account operations. In ANIFORCE, this should be part of platform account metadata, not a standalone operations-heavy module initially.

ANIFORCE mapping:

- Add `business_manager_id` / `asset_owner_id` to PlatformAccount.
- Later add `PlatformAsset` model for BM, pixel, page, app, conversion event.
- Agent can diagnose missing/invalid assets.

### 2.6 Finance Management

Observed functions:

- Fund dashboard:
  - Platform balance
  - Available balance
  - Frozen amount
- Tabs:
  - Recharge records
  - Withdrawal records
  - Fund ledger
- Filters:
  - Transaction status
  - Transaction hash
- Table fields:
  - Flow ID
  - Recharge amount
  - Arrived amount
  - Transaction hash
  - Transaction status
  - Currency
  - Network type
  - Receiving address
  - Remark
  - Created time
  - Transaction time
  - Remaining time
  - Operation

Migration value:

Full wallet/ledger is not needed for Phase 1 unless ANIFORCE acts as an account agency or payment intermediary. But budget and balance awareness are important for agent decisions.

ANIFORCE mapping:

- Phase 1 only needs account/project budget and spend visibility.
- Add optional `AccountBalanceSnapshot` later:
  - platform_account_id
  - available_balance
  - frozen_balance
  - currency
  - credit_limit
  - last_sync_at
- Do not implement deposit/withdrawal flow now.

### 2.7 BI Analysis

Observed functions:

- Account spend analysis
- Filters:
  - Date range
  - Account property
  - Account ID
  - Account name
- Charts:
  - Spend trend
  - Spend by account property pie chart
- Account spend list
- Export

Migration value:

Highly relevant. This should become a normalized spend analysis and agent diagnosis input.

ANIFORCE mapping:

- Build Spend Analysis view as part of Phase 1.
- Use normalized `MetricSnapshot`.
- Add chart breakdowns:
  - by platform
  - by account
  - by project
  - by campaign
  - by status
- Feed agent:
  - spend concentration
  - wasted spend
  - account-level delivery trend
  - budget utilization

## 3. Phase 1 Migration Scope

Phase 1 should migrate these Blue Whale capabilities:

### Must Have

1. Platform account inventory
2. Account status tabs and count cards
3. Account spend range cards
4. Account filters and table
5. Account row actions:
   - sync
   - spend analysis
   - transaction/spend detail
   - remark/edit
6. Account-level spend analysis
7. Basic fund/budget visibility:
   - project budget
   - account spend
   - available budget if known
8. Agent account-health diagnosis
9. Agent action queue from account/spend findings

### Should Have

1. Export account list / spend list
2. Business manager / BMID fields
3. Account delivery/connect time
4. Account survival/usage time
5. Account timezone and currency
6. Account source/type/property

### Not Phase 1

1. Full account rental market
2. Full rental order flow
3. Deposit / withdrawal / crypto transaction flow
4. Refund workflow
5. Work order system
6. Complex financial ledger

## 4. Data Model Changes

### 4.1 PlatformAccount

Add model:

```text
platform_accounts
  id
  workspace_id nullable
  project_id nullable
  platform
  external_account_id
  account_name
  account_type
  account_property
  account_source
  business_manager_id
  timezone
  currency
  status
  lifecycle_status
  accumulated_spend
  available_balance nullable
  credit_limit nullable
  delivered_at nullable
  last_used_at nullable
  returned_at nullable
  last_synced_at nullable
  remark
  token_encrypted nullable
  refresh_token_encrypted nullable
  raw_json
  created_at
  updated_at
```

Recommended `status`:

```text
active
clearing
banned
cleared
recycled
disconnected
sync_failed
```

Recommended `account_property`:

```text
BM
personal
agency
direct
unknown
```

### 4.2 AccountSpendSnapshot

Add model:

```text
account_spend_snapshots
  id
  platform_account_id
  project_id nullable
  date
  spend
  impressions
  clicks
  conversions
  revenue
  cpa
  roas
  currency
  raw_json
  created_at
```

This can later be merged into a generalized `MetricSnapshot`, but Phase 1 can keep account-level spend snapshots explicit.

### 4.3 AccountTransaction

Add lightweight transaction model only for spend/recharge visibility:

```text
account_transactions
  id
  platform_account_id
  transaction_type: recharge | spend | adjustment | refund | transfer
  amount
  currency
  status
  external_transaction_id nullable
  occurred_at
  raw_json
  created_at
```

No deposit/withdrawal workflow in Phase 1.

### 4.4 AgentAction Additions

AgentAction should support account-level resources:

```text
resource_type: platform_account | campaign | project | creative | tracking
resource_id
action_type:
  sync_account
  inspect_account
  analyze_spend
  pause_campaign
  reduce_budget
  increase_budget
  refresh_creative
  check_tracking
  mark_account_risk
```

## 5. Backend API Design

### 5.1 Platform Accounts

```text
GET /api/v1/platform-accounts
POST /api/v1/platform-accounts/test
GET /api/v1/platform-accounts/{id}
PATCH /api/v1/platform-accounts/{id}
POST /api/v1/platform-accounts/{id}/sync
GET /api/v1/platform-accounts/summary
GET /api/v1/platform-accounts/{id}/transactions
GET /api/v1/platform-accounts/{id}/spend
```

Query filters:

```text
project_id
platform
status
account_type
account_property
spend_min
spend_max
keyword
delivered_from
delivered_to
```

### 5.2 Spend Analysis

```text
GET /api/v1/spend-analysis/accounts
GET /api/v1/spend-analysis/trend
GET /api/v1/spend-analysis/breakdown
```

Filters:

```text
date_from
date_to
project_id
platform
platform_account_id
account_property
```

### 5.3 Agent Diagnosis

```text
POST /api/v1/projects/{project_id}/actions/generate-account-diagnosis
GET /api/v1/projects/{project_id}/actions?resource_type=platform_account
```

Diagnosis examples:

- Active account with zero spend for 7 days
- Banned account still assigned to active project
- High spend account without conversion data
- Account timezone mismatches project target market
- Sync stale for more than 24 hours
- Available balance low
- Spend concentration too high in one account

## 6. Frontend Integration Design

### 6.1 Navigation

Do not copy Blue Whale's exact nav. Recommended ANIFORCE nav:

```text
Today
Projects
Ad Accounts
Campaigns
Creatives
Spend Analysis
Agent Actions
Project Brain
```

Phase 1 should add:

- `Ad Accounts`
- `Spend Analysis`
- `Agent Actions`

### 6.2 Ad Accounts Page

Inspired by Blue Whale account management.

Layout:

```text
Header: platform tabs + actions
Spend range cards
Status tabs
Filters
Account table
```

Spend range cards:

- `$0-10`
- `$10-100`
- `$100-500`
- `$500-1000`
- `$1000-2000`
- `$2000+`

Each card:

- total count
- active count
- banned/risk count

Status tabs:

- Active
- Clearing
- Banned
- Cleared
- Recycled
- Disconnected
- Sync Failed

Table columns:

- Account ID
- Account name
- Platform
- Type
- Property
- BMID / Asset owner
- Timezone
- Currency
- Accumulated spend
- Available balance
- Delivered/connected time
- Survival time
- Last used time
- Last synced time
- Remark
- Status
- Actions

Row actions:

- Sync
- Spend analysis
- Transactions
- Edit remark
- Generate diagnosis

### 6.3 Spend Analysis Page

Inspired by Blue Whale BI Analysis.

Layout:

```text
Filters
Spend trend chart
Spend breakdown chart
Account spend table
Agent observations panel
```

Charts:

- Spend trend by day
- Spend by platform
- Spend by account property
- Spend by account status

Table columns:

- Account name
- Account ID
- Platform
- Accumulated spend
- 7d spend
- CPA
- ROAS
- Status
- Last synced
- Actions

Agent observations:

- "Spend is concentrated in 1 account."
- "3 accounts are active but have zero spend."
- "1 banned account is still attached to active project."

### 6.4 Agent Actions Page

This is where ANIFORCE differs from Blue Whale.

Blue Whale shows operational records. ANIFORCE should show agent-generated decisions.

Action cards:

- Account health actions
- Spend anomaly actions
- Campaign optimization actions
- Creative refresh actions

Each action:

- Title
- Evidence
- Resource
- Risk level
- Suggested action
- Confirm / reject / mark done

## 7. How This Fits the Agent-Driven OS Plan

Blue Whale capabilities should become the operational substrate:

```text
Ad account inventory
  -> account health diagnosis
  -> spend analysis
  -> agent action queue
```

They should not become a separate heavy SaaS module unless account rental and financial settlement become a core revenue model.

The first version should answer:

- Which ad accounts do we have?
- Which accounts are usable?
- Which accounts are consuming budget?
- Which accounts are risky?
- Which accounts need action today?
- What does the agent recommend doing?

## 8. Phase 1 Development Plan

### Sprint 1: Data Models and Mock Data

Build:

- `PlatformAccount`
- `AccountSpendSnapshot`
- `AccountTransaction`
- Repository methods
- Mock seed data based on Blue Whale fields

Acceptance:

- Backend can list accounts with status, spend, BMID, timezone, lifecycle fields.
- Backend can return spend range and status summaries.

### Sprint 2: Platform Account APIs

Build:

- `GET /platform-accounts`
- `GET /platform-accounts/summary`
- `GET /platform-accounts/{id}`
- `PATCH /platform-accounts/{id}`
- `GET /platform-accounts/{id}/transactions`
- `GET /platform-accounts/{id}/spend`

Acceptance:

- Frontend can render account list, filters, status tabs, and summary cards.

### Sprint 3: Ad Accounts Page

Build:

- Ad Accounts route/page
- Spend range cards
- Status tabs
- Filters
- Account table
- Row actions

Acceptance:

- User can inspect account inventory similarly to Blue Whale account page.
- Page is adapted to ANIFORCE style, not copied visually.

### Sprint 4: Spend Analysis Page

Build:

- Spend trend endpoint
- Spend breakdown endpoint
- Spend Analysis page
- Account spend table
- Export placeholder

Acceptance:

- User can see account-level spend trend and distribution.

### Sprint 5: Agent Account Diagnosis

Build:

- Account diagnosis rules
- Generate account-level AgentAction
- Display actions in Agent Actions page

Acceptance:

- System can produce account health suggestions:
  - sync stale account
  - inspect banned account
  - move spend away from risky account
  - investigate high spend without conversion
  - recharge/credit warning if balance data exists

### Sprint 6: Integration into Today View

Build:

- Account health summary cards
- Spend anomaly summary
- Pending agent actions
- Links to account and spend pages

Acceptance:

- Media buyer can start the day from Today View instead of manually checking Blue Whale-like modules.

## 9. What Not to Build Yet

Do not build these in Phase 1:

- Full rental marketplace
- Full order purchasing flow
- Recharge/withdrawal workflow
- Crypto transaction submission
- Refund workflow
- Work order center
- Complex organization permissions

These can be revisited only if ANIFORCE chooses to monetize ad-account supply or agency financial operations.

## 10. Product Positioning After Migration

Blue Whale-like systems answer:

```text
What accounts, orders, funds, and spend records do I have?
```

ANIFORCE should answer:

```text
Which accounts and campaigns need action today, why, and what should the media buyer or agent do next?
```

The migration should preserve operational visibility while adding agent-driven decision and execution capability.

