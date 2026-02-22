# Demo scenarios for AI Goal Coach

Use these for a short demo of the Refine tab and iterative "Refine further" flow.

## Test user

- **If using Docker:** The database starts empty. Create a user once via the **Sign up** tab, e.g. username `testuser`, password `testpass` (at least 8 characters). Then use **Login** with the same credentials for the demo.
- **If using local API + UI:** Same as above, or use any account you already created.

---

## Scenario 1: Vague goal (first refinement)

**Paste this into "Your goal or aspiration" and click "Refine Goal":**

```text
I want to read more and actually finish books instead of leaving them halfway.
```

**Why it works for demo:** It’s clearly a goal, a bit vague (no number, no deadline), and the model will add specifics (e.g. “12 books”, “by December”, “20 minutes daily”, key results). You get a strong first draft to refine in the next step.

---

## Scenario 2: Refine further (iterative tweak)

After you see the refined goal and key results, use **Refine further** with:

**Paste this into "Your feedback" and click "Refine further":**

```text
Make the deadline 6 months from now and add one key result about finishing at least 2 nonfiction books.
```

**Why it works for demo:** It asks for a concrete change (shorter timeframe) and an extra key result. The updated goal should show the new deadline and the new key result, so the iterative flow is obvious.

---

## Optional one-liner variants

- **Vague goal:** `Get better at public speaking.` or `I’d like to run a marathon someday.`
- **Refinement:** `Tone it down—I can only commit 2 hours a week.` or `Add a key result about joining a local running group.`
