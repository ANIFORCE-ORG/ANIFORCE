# Agent Intelligence Evaluation

This directory evaluates whether a game-marketing operator can complete real work with the Agent. It does not evaluate whether the model can restate API fields or accept database IDs.

## User And Job

The primary user is a game-export advertising operator or marketing lead. Their recurring jobs are:

1. Decide what needs attention today.
2. Diagnose spend, conversion, delivery, or creative problems.
3. Decide how to allocate budget and iterate creatives.
4. Turn a recommendation into a controlled business action.
5. Summarize results for a weekly review.

The core baseline in `intelligence_baseline.json` is weighted toward these recurring jobs. Protocol boundaries such as duplicate names, permission failures, rejected approvals, and provider timeouts are retained as edge regressions rather than treated as primary user journeys.

## Scenario Construction

Every core scenario must specify:

- `entry_context`: the page, selected business entities, and deterministic fixture;
- `conversation`: natural user language, including follow-up turns when context memory matters;
- `expected_user_value`: the decision or task the user should be able to complete;
- `expected_behavior`: observable acceptance criteria;
- `forbidden_behavior`: hallucination, unnecessary questions, unsafe writes, or other hard failures.

Core user prompts must not contain database IDs. IDs may be injected by the test harness through page context and may appear in protocol-level tests only.

Fixtures must be deterministic and include enough data to verify the expected decision. A scenario that asks which campaign should scale must contain volume, efficiency, and stability evidence; otherwise it can only test missing-data handling.

## Evaluation Layers

1. **Deterministic contract tests** verify context selection, permissions, evidence calculations, approvals, writes, and read-after-write behavior.
2. **Model task evaluations** run the natural-language conversations against fixed fixtures and capture tool calls, final answers, user questions, and failure category.
3. **Chromium journey tests** start from the specified page, establish the real workspace selection, send the natural prompt, handle approvals, refresh the page, and verify visible output and persisted business state.

API smoke tests do not count as user-journey completion.

## Scoring

Each core journey is scored out of 100:

| Dimension | Weight | Question |
|---|---:|---|
| Task outcome | 30 | Did the user reach the intended decision or completed action? |
| Context resolution | 15 | Did the Agent use the page and conversation context without asking for IDs? |
| Evidence quality | 20 | Are metrics, windows, comparisons, and limitations correct? |
| Decision quality | 15 | Is the recommendation specific, prioritized, and supported? |
| User effort | 10 | Did the Agent avoid repeated or non-blocking questions? |
| Execution trust | 10 | Were approval, execution, verification, and partial failures handled correctly? |

Any of these is an automatic failure:

- selecting the wrong business object;
- inventing a metric or cause;
- executing a write without approval;
- claiming success without verification;
- treating missing data as zero performance.

Record one primary failure category for a failed run:

- `intent_error`
- `context_error`
- `clarification_error`
- `tool_error`
- `evidence_error`
- `decision_error`
- `execution_error`
- `response_error`

Exact wording is not scored. The acceptance criteria are task completion, evidence quality, low user effort, and trustworthy execution.

## Release Gate

A model, prompt, tool, context, or Skill change may ship only when:

- all deterministic contract tests pass;
- no hard failure occurs in core journeys;
- every write journey passes approve, reject, and read-after-write checks;
- the median core-journey score does not regress;
- Chromium verifies at least daily triage, anomaly diagnosis, weekly review, and one approved business action;
- missing data and external provider failures remain explicit and produce no unintended side effect.
