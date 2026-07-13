# Agent Intelligence Evaluation Baseline

This directory contains stable, user-centered evaluation cases for Agent behavior changes.

`intelligence_baseline.json` separates expected and forbidden behavior from model-specific output wording. A run should be classified with one primary failure category:

- `intent_error`
- `context_error`
- `clarification_error`
- `tool_error`
- `evidence_error`
- `decision_error`
- `execution_error`
- `response_error`

The baseline is evaluated before and after changes to prompts, business skills, context, tools, or models. Exact prose matching is intentionally excluded; task completion, evidence, safety, and user effort are the acceptance criteria.
