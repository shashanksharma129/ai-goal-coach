# SMART Goal Prompt Improvement – Design

**Date:** 2026-02-20  
**Branch:** feature/smart-goal-prompt  
**Approach:** Approach 2 — SMART criteria + structure hint (no full example)

## Goal

Improve the AI goal-coach prompt so that refined goals and key results consistently satisfy the SMART framework (Specific, Measurable, Achievable, Relevant, Time-bound), using guidance derived from [Atlassian: How to write SMART goals](https://www.atlassian.com/blog/productivity/how-to-write-smart-goals). Output schema and API remain unchanged.

## Scope

- **In scope:** Only the agent instruction string in `goal_coach/agent.py` (e.g. `GOAL_INSTRUCTION`). No schema, API, or UI changes.
- **Out of scope:** Multiple prompts, A/B testing, or configurable prompt variants.

## Instruction Shape

The new instruction will have five parts:

1. **Role and task (unchanged in intent):** You are an AI goal coach; given a vague goal or aspiration, produce a refined SMART goal and 3–5 measurable key results.

2. **SMART criteria (new):** Short definitions so the model knows what to satisfy:
   - **Specific:** What needs to be accomplished, who is responsible, what steps are needed.
   - **Measurable:** Quantifiable so progress can be tracked (how much, how many).
   - **Achievable:** Realistic and attainable.
   - **Relevant:** Tied to the bigger picture and why it matters.
   - **Time-bound:** Clear timeframe or deadline.

   State explicitly that the refined_goal and key_results must satisfy these criteria.

3. **Structure hint (new, one sentence):** The refined goal should read like: [quantifiable objective] by [timeframe], accomplished by [concrete steps], with a clear result or benefit. (No full example; pattern only.)

4. **Output and schema (unchanged):** Valid JSON: refined_goal (string), key_results (list of 3–5 strings), confidence_score (float 0–1).

5. **Confidence rule (unchanged):** High (e.g. 0.7–1.0) for genuine goals/aspirations; low (e.g. 0.0–0.4) for nonsensical, malicious, or non-goal input (e.g. SQL, commands, gibberish).

## Validation

- Run existing evals (`tests/test_evals.py`) and agent tests after the change; they must still pass.
- No new evaluation framework in this design; tune prompt wording if evals regress.

## Risks and Mitigations

- **Longer prompt:** Slightly more tokens per call; acceptable. Wording can be trimmed later if needed.
- **Output style shift:** Evals and manual checks catch regressions; structure hint can be softened or tightened based on results.

## Reference

- Atlassian, “How to write SMART goals,” Dec 2023.  
  https://www.atlassian.com/blog/productivity/how-to-write-smart-goals
