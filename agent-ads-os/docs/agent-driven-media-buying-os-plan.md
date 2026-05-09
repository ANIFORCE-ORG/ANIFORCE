# Agent-Driven Media Buying OS Plan

## 1. Product Direction

ANIFORCE should not evolve into a heavy organization-management system with an agent attached. Existing ad teams already handle reporting lines, ownership, approval habits, and team coordination through offline process, spreadsheets, platform permissions, and internal management tools.

The product should instead become an agent-driven media-buying decision system:

```text
Cross-platform data -> daily diagnosis -> action queue -> human confirmation -> execution -> result tracking -> project memory
```

The core job is to help one media buyer manage more projects with better consistency, not to rebuild the whole company hierarchy.

## 2. Current System Baseline

The current main app already has these useful foundations:

- `User -> Project -> Campaign -> Material -> Metric`
- Platform adapters for Meta, Google, and TikTok
- Campaign-level fields for platform, budget, status, target CPA, learning phase, optimization rules
- Basic project budget and campaign monitoring pages
- Chat service and Agent/GEO exploratory modules

The main gaps are not "more roles" or "more organization layers." The main gaps are:

- No durable platform ad-account model
- No unified cross-platform metric normalization layer
- No action queue for agent recommendations
- No risk level / execution boundary for ad operations
- No action outcome tracking
- No project memory or playbook layer
- No budget movement model across platforms/accounts/campaigns

## 3. Target Operating Model

### 3.1 Core Objects

Keep the domain model practical:

```text
Workspace
  Project
    PlatformAccount
      Campaign
        AdSet / AdGroup
          Ad / Creative
    MetricSnapshot
    AgentAction
    ProjectMemory
    Playbook
```

Recommended interpretation:

- `Workspace`: billing and account boundary. Do not overbuild org hierarchy in early versions.
- `Project`: product, app, game, client, or business line. This remains the primary business context.
- `PlatformAccount`: real Meta / Google / TikTok ad account connected to a project or workspace.
- `Campaign`: local representation of platform campaign with external IDs.
- `MetricSnapshot`: normalized metrics from each platform.
- `AgentAction`: a suggested or executed action with reason, data evidence, risk, and outcome.
- `ProjectMemory`: durable project facts, constraints, learnings, and known good/bad strategies.
- `Playbook`: reusable media-buying policy for a category, channel, project, or growth stage.

### 3.2 Minimal Permission Model

Avoid complex RBAC at the start. Use operation boundaries:

```text
Owner
Operator
Viewer
```

The important controls are not title-based permissions, but execution boundaries:

- Which projects can this user operate?
- Which platform accounts can this user operate?
- What is the daily budget ceiling?
- What is the single action budget-change limit?
- Can the agent pause campaigns automatically?
- Can the agent increase budget automatically?
- Can the agent publish new campaigns automatically?
- Which actions require human confirmation?

This is more aligned with media buying than a large permission matrix.

## 4. Agent Risk Model

Every agent action should be classified by risk level.

```text
L0 Read-only
  Analyze data, summarize trends, explain anomalies, generate reports.

L1 Draft
  Generate campaign structure, budget plan, creative brief, optimization suggestion.

L2 Low-risk execution
  Create draft objects, add labels, sync data, pause clearly broken entities within configured rules.

L3 Medium-risk execution
  Adjust budget, pause/enable ad sets, replace creative, modify bids.

L4 High-risk execution
  Publish new campaigns, large budget increases, cross-platform budget migration, conversion-event changes.
```

Recommended default behavior:

```text
L0 / L1: automatic
L2: automatic if project automation is enabled
L3: requires operator confirmation
L4: requires owner or lead confirmation
```

The product should present these as media-buying safety controls, not as enterprise permission complexity.

## 5. Core Product Experience

### 5.1 Today View

The first screen for a media buyer should answer:

- What needs attention today?
- Which campaigns are wasting spend?
- Which campaigns can scale?
- Which creatives are fatigued?
- Which platform/account has delivery issues?
- What did the agent already do?
- Which actions need my confirmation?

This page should replace the need to manually inspect every platform dashboard.

### 5.2 Action Queue

The action queue is the product's core surface.

Each action should include:

- Action type: pause, scale, reduce budget, create draft, replace creative, inspect tracking, etc.
- Resource: project / account / campaign / adset / creative
- Evidence: last 3d/7d metrics, threshold triggered, comparison to baseline
- Expected impact
- Risk level
- Required confirmation
- Status: suggested, confirmed, rejected, executed, failed, expired
- Outcome after execution

Example:

```text
Action: Reduce TikTok Campaign A daily budget by 30%
Evidence: CPA is 2.3x target for 3 consecutive days; spend is 18% of project budget; no creative refresh in 9 days.
Risk: L3
Status: Pending confirmation
```

### 5.3 Project Brain

Each project should accumulate useful memory:

- Product facts and target market
- KPI targets and forbidden moves
- Effective platforms and geos
- Working creative angles
- Failed tests
- Budget rules
- Historical agent actions and outcomes

This should feed future agent decisions. The long-term moat is not the chat UI; it is the accumulated media-buying memory.

### 5.4 Automation Rules

Media buyers need configurable boundaries:

- Target CPA / ROAS / CPI
- Minimum data volume before action
- Maximum daily budget change
- Maximum single campaign budget change
- Auto-pause thresholds
- Auto-scale thresholds
- Learning phase protection
- Cooldown between actions

These rules should be attached to project, campaign, or playbook.

## 6. Required System Changes

### 6.1 Backend Models

Add or evolve these models.

#### Workspace

Purpose: lightweight business boundary.

Fields:

```text
id
name
owner_user_id
settings_json
created_at
updated_at
```

#### PlatformAccount

Purpose: durable ad-account asset.

Fields:

```text
id
workspace_id
project_id nullable
platform: meta | google | tiktok
external_account_id
account_name
currency
timezone
status
token_encrypted
refresh_token_encrypted
scopes_json
last_sync_at
created_at
updated_at
```

Current `platform_auth.py` in-memory account storage should be replaced by this model.

#### Campaign Extensions

Current `Campaign` should gain:

```text
platform_account_id
external_campaign_id
external_status
objective
budget_type
daily_budget
lifetime_budget
bid_strategy
last_synced_at
```

Do not force adset/adgroup immediately if the first milestone is campaign-level optimization. Add those later.

#### MetricSnapshot

Current `Metric` can be kept, but the product needs normalized snapshots.

Suggested fields:

```text
id
workspace_id
project_id
platform_account_id
campaign_id nullable
external_resource_type: campaign | adset | ad | creative
external_resource_id
date
window: 1d | 3d | 7d | 14d
impressions
clicks
spend
conversions
revenue
ctr
cvr
cpa
roas
cpi
raw_json
created_at
```

#### AgentAction

This is the core new model.

Fields:

```text
id
workspace_id
project_id
platform_account_id nullable
campaign_id nullable
action_type
risk_level: L0 | L1 | L2 | L3 | L4
status: suggested | confirmed | rejected | executing | executed | failed | expired
title
summary
evidence_json
payload_json
expected_impact_json
created_by: agent | user
confirmed_by nullable
executed_by nullable
execution_result_json
outcome_json
created_at
confirmed_at
executed_at
evaluated_at
```

#### ProjectMemory

Fields:

```text
id
project_id
memory_type: fact | rule | learning | warning | playbook_note
content
source_type: user | agent | action_outcome | import
confidence
created_at
updated_at
```

#### Playbook

Fields:

```text
id
workspace_id
name
scope: global | vertical | project
vertical
rules_json
created_at
updated_at
```

### 6.2 Services

Add service modules:

```text
platform_sync_service.py
metric_normalization_service.py
agent_diagnosis_service.py
agent_action_service.py
agent_execution_service.py
project_memory_service.py
playbook_service.py
```

Responsibilities:

- `platform_sync_service`: pull campaigns and metrics from Meta/Google/TikTok.
- `metric_normalization_service`: normalize platform-specific metrics.
- `agent_diagnosis_service`: detect anomalies and opportunities.
- `agent_action_service`: create and rank action suggestions.
- `agent_execution_service`: execute approved or low-risk actions through connectors.
- `project_memory_service`: write and retrieve durable learnings.
- `playbook_service`: load automation thresholds and strategy rules.

### 6.3 API Surfaces

Add APIs:

```text
GET /api/v1/today
GET /api/v1/projects/{project_id}/diagnosis
GET /api/v1/projects/{project_id}/actions
POST /api/v1/projects/{project_id}/actions/generate
POST /api/v1/agent-actions/{action_id}/confirm
POST /api/v1/agent-actions/{action_id}/reject
POST /api/v1/agent-actions/{action_id}/execute
GET /api/v1/projects/{project_id}/memory
POST /api/v1/projects/{project_id}/memory
GET /api/v1/platform-accounts
POST /api/v1/platform-accounts/sync
```

### 6.4 Frontend Pages

Add or refactor pages:

```text
Today.vue
ActionQueue.vue
ProjectBrain.vue
AutomationRules.vue
PlatformAccounts.vue
```

Existing project and campaign pages should remain, but the operating center should move toward Today + Action Queue.

## 7. Agent Diagnosis Logic

Start with deterministic rules before LLM-heavy reasoning.

Initial diagnosis rules:

- CPA above target for N days
- ROAS below target for N days
- Spend exceeds threshold with zero conversions
- Campaign cannot spend budget
- CTR decline vs 7-day baseline
- CVR decline vs 7-day baseline
- Creative fatigue: impressions high + CTR decline + CPA increase
- Budget cap reached while CPA/ROAS is healthy
- Learning phase stuck
- Tracking anomaly: clicks normal, conversions drop to zero
- Platform account disconnected or sync stale

LLM should be used after deterministic detection, mainly for:

- explaining the issue in human language
- summarizing evidence
- generating campaign drafts
- generating creative briefs
- selecting playbook language

Do not use LLM as the primary metric detector.

## 8. Development Roadmap

### Phase 1: Campaign Intelligence Baseline

Goal: save media buyers daily inspection time.

Build:

- PlatformAccount model and persistence
- Campaign external ID fields
- MetricSnapshot model
- Manual or scheduled metric sync
- Normalized project/campaign metric summaries
- Deterministic anomaly detection
- Read-only Today View

Acceptance:

- A user can connect or mock-connect platform accounts.
- Campaign and metric snapshots can be synced into local DB.
- Today View shows project-level anomalies and opportunities.
- No execution actions yet.

### Phase 2: Agent Action Queue

Goal: convert diagnosis into concrete media-buying actions.

Build:

- AgentAction model
- Rule-based action generation
- Action risk levels
- Action Queue page
- Confirm/reject actions
- Action evidence display
- Action expiration and deduplication

Acceptance:

- System generates suggestions like pause, reduce budget, scale, inspect tracking, refresh creative.
- Each suggestion includes evidence and risk level.
- User can confirm or reject suggestions.
- No platform write execution required yet.

### Phase 3: Low-Risk Execution

Goal: reduce repetitive operations without unsafe automation.

Build:

- Agent execution service
- Connector wrappers for pause, budget update, create draft
- Execution log
- Automation boundaries per project
- L2 auto-execution support
- L3/L4 manual confirmation

Acceptance:

- Confirmed actions can be executed against mock connectors first.
- Execution result is written back to AgentAction.
- Failures are visible in Action Queue.
- Project-level limits prevent unsafe budget changes.

### Phase 4: Project Memory and Outcome Tracking

Goal: turn actions into reusable learning.

Build:

- ProjectMemory model
- Action outcome evaluation after 1/3/7 days
- Automatic memory generation from successful and failed actions
- Project Brain page
- Basic playbook storage

Acceptance:

- Each action has a post-action outcome.
- Successful rules can become memory/playbook notes.
- Future suggestions can reference project memory.

### Phase 5: Cross-Platform Budget Scheduler

Goal: create the main competitive wedge.

Build:

- Project-level budget allocation view
- Platform/account/campaign budget distribution
- Marginal performance comparison
- Budget movement recommendations
- Budget simulation
- Cross-platform action bundles

Acceptance:

- System can recommend moving budget between Meta/Google/TikTok based on normalized metrics.
- Recommendations include expected impact and risk.
- Human can confirm a bundle or edit it.

### Phase 6: Creative Iteration Agent

Goal: connect media buying and creative production.

Build:

- Creative tagging model
- Creative fatigue detection
- Hook/angle/format labels
- Cross-platform creative transfer suggestions
- Creative brief generation
- Material-to-campaign performance joins

Acceptance:

- System identifies fatigued and winning creatives.
- System generates new creative briefs from performance patterns.
- System suggests which creatives to test on which platform.

## 9. Near-Term Implementation Order

Recommended next engineering tasks:

1. Add `PlatformAccount`, `MetricSnapshot`, `AgentAction` models and migrations.
2. Extend `Campaign` with `platform_account_id` and external IDs.
3. Replace in-memory platform accounts with repository-backed persistence.
4. Implement normalized mock metric sync first, using current mock/demo data.
5. Implement `agent_diagnosis_service` with deterministic anomaly rules.
6. Add `GET /api/v1/today` and `GET /api/v1/projects/{id}/actions`.
7. Build Action Queue frontend using existing dashboard style.
8. Add confirm/reject APIs.
9. Add execution only after the queue and evidence model feel right.

## 10. Design Principles

- Do not overbuild organization management.
- Do not put chat at the center of the product.
- Put action queue and evidence at the center.
- Use deterministic rules for metrics and risk detection first.
- Use LLM for explanation, planning, and draft generation.
- Every agent action must have evidence, risk level, status, and outcome.
- Every execution must be reversible where possible, logged, and bounded.
- The long-term moat is action outcome data plus project memory.

## 11. Success Metrics

Product-level:

- Media buyer inspection time reduced by 50%+
- Number of projects managed per buyer increases
- High-risk actions remain human-confirmed
- Action acceptance rate improves over time
- Repeated action patterns become playbooks

Business-level:

- Customers pay for monitored projects/accounts, not token usage
- Monthly plans can be priced by projects, accounts, and action volume
- Premium value comes from cross-platform budget decisions and creative iteration, not generic chat

