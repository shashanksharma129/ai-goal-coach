# Saved Goals List View – Design

**Date:** 2026-02-20  
**Status:** Approved  
**Scope:** Complete Part D of the AI Goal Coach challenge: list view of saved goals + re-add Save in the UI. Single shared list (no auth), newest first, with pagination.

---

## 1. Backend (API)

- **New endpoint: `GET /goals`**
  - **Query params (optional):**
    - `limit` – max goals to return (default 20; cap at 100).
    - `offset` – number to skip (default 0).
  - **Response:** `{ "goals": [ ... ], "total": N }`. Each goal has the same shape as current `POST /goals` response: `id`, `original_input`, `refined_goal`, `key_results`, `confidence_score`, `status`, `created_at`.
  - **Order:** Newest first (`ORDER BY created_at DESC`).
  - **Empty:** `{ "goals": [], "total": 0 }` with HTTP 200.
- **Implementation:** One query with `LIMIT`/`OFFSET` plus a `COUNT(*)` (or equivalent) for `total`. Reuse `get_session()` and `Goal` model.

---

## 2. Frontend (UI)

- **Layout:** Two tabs: **"Refine"** and **"Saved goals"** (Streamlit `st.tabs()`).
- **Refine tab:** Existing flow (input → Refine Goal → show refined goal, key results, confidence). **Re-add "Save Approved Goal"**; on success show e.g. "Goal saved. Check the Saved goals tab."
- **Saved goals tab:**
  - Call `GET /goals?limit=20&offset=<offset>`. Display list newest first.
  - Each item: show at least **refined_goal** and **created_at**; optionally key_results/confidence.
  - **Pagination:** Previous/Next (or page numbers) using `offset = (page - 1) * limit`; show "Showing 1–20 of N" using `total`.
  - **Empty state:** "No saved goals yet. Use the Refine tab to create and save one."

---

## 3. Error Handling & Edge Cases

- **Backend:** Invalid or negative `limit`/`offset` → 400. Cap `limit` at 100. DB errors → 500.
- **Frontend:** If `GET /goals` fails → show "Could not load saved goals. Try again." Save failure → show error, keep refined goal on screen.
- **Pagination:** If current page becomes empty (e.g. after deletions elsewhere), refetch with `offset=0` when `goals` is empty and `offset > 0`.

---

## 4. Testing

- **Backend:** In `test_main.py` (or equivalent): GET returns 200 and `{ "goals": [], "total": 0 }` when empty; after creating goals, GET returns them newest first; `limit`/`offset` return correct slice and `total`; invalid params → 400.
- **Existing:** All current tests remain green; no change to `POST /goals` contract.
- **Frontend:** Manual verification of Refine (with Save) and Saved goals (list + pagination + empty state).

---

## Decisions

- **List scope:** All saved goals from DB (one shared list; no auth).
- **Order:** Newest first.
- **UI pattern:** Tabs (Refine | Saved goals) for clear separation.
- **Pagination:** `limit`/`offset` and `total` in API; simple Previous/Next or page numbers in UI.
