# review-pptx

`review-pptx` runs the QA flow against the rendered artifact instead of only the JSON spec.

Use it when visual sign-off matters more than authoring-time heuristics.

```bash
ppt-creator review-pptx outputs/deck.pptx outputs/review_artifacts \
  --report-json outputs/review_artifacts/report.json
```