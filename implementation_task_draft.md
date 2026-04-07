# Implementation Task Draft

Manual fallback because the current tool environment does not expose a `new_task` tool.

Before execution, please toggle to Act mode.

Refer to @implementation_plan.md for a complete breakdown of the task requirements and steps. You should periodically read this file again.

Implementation context:

1. Expand the existing Python product API into the backend-for-frontend for both the product shell and the AI Lab shell.
2. Reuse existing Python domain/service logic wherever possible; do not duplicate Gradio or Streamlit rendering logic in the new API paths.
3. Extract the Streamlit-only chat orchestration out of `main.py` before wiring the React chat page so both surfaces share the same behavior.
4. Replace all `frontend/src/lib/mock-data.ts` imports with typed API hooks and real loading/error states.
5. Keep the current React route map unless a capability cannot be represented without a small route/sidebar addition.

Plan Document Navigation Commands:

```bash
# Read Overview section
sed -n '/\[Overview\]/,/\[Types\]/p' implementation_plan.md | head -n 1 | cat

# Read Types section
sed -n '/\[Types\]/,/\[Files\]/p' implementation_plan.md | head -n 1 | cat

# Read Files section
sed -n '/\[Files\]/,/\[Functions\]/p' implementation_plan.md | head -n 1 | cat

# Read Functions section
sed -n '/\[Functions\]/,/\[Classes\]/p' implementation_plan.md | head -n 1 | cat

# Read Classes section
sed -n '/\[Classes\]/,/\[Dependencies\]/p' implementation_plan.md | head -n 1 | cat

# Read Dependencies section
sed -n '/\[Dependencies\]/,/\[Testing\]/p' implementation_plan.md | head -n 1 | cat

# Read Testing section
sed -n '/\[Testing\]/,/\[Implementation Order\]/p' implementation_plan.md | head -n 1 | cat

# Read Implementation Order section
sed -n '/\[Implementation Order\]/,$p' implementation_plan.md | cat
```

task_progress Items:
- [ ] Step 1: Extend backend contracts, bootstrap wiring, and workflow-history persistence
- [ ] Step 2: Extract reusable chat orchestration and add AI Lab backend service adapters
- [ ] Step 3: Expand the product API with overview, history, artifact, documents, chat, structured, model-comparison, and EvidenceOps endpoints
- [ ] Step 4: Add the typed frontend API client, query hooks, and shared runtime preference store
- [ ] Step 5: Replace mock-backed product pages with live API integrations
- [ ] Step 6: Replace mock-backed AI Lab pages with live API integrations
- [ ] Step 7: Remove remaining mock data, refresh docs/config, and complete backend/frontend validation