# Visual regression

For critical regression checks, the default recommended path is to trust the rendered artifact first and the spec preview second.

Recommended sequence:

1. `ppt-creator render ...`
2. `ppt-creator review-pptx ...` or `ppt-creator preview-pptx ...`
3. `ppt-creator compare-pptx before.pptx after.pptx ...`
4. inspect `guidance`, `top_regressions`, `added_slide_numbers`, and `removed_slide_numbers`
5. promote the approved preview set only after sign-off

Primary commands:

- `ppt-creator preview ... --baseline-dir ...`
- `ppt-creator preview-pptx ... --baseline-dir ...`
- `ppt-creator review-pptx ... --baseline-dir ...`
- `ppt-creator compare-pptx before.pptx after.pptx ...`

Use `--fail-on-regression` to turn the diff into an operational gate.