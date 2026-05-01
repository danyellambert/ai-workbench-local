# compare-pptx

`compare-pptx` generates previews from two rendered `.pptx` artifacts and compares them slide-by-slide.

Recommended usage:

```bash
ppt-creator compare-pptx outputs/v1.pptx outputs/v2.pptx outputs/compare_v1_v2 \
  --write-diff-images --fail-on-regression
```

Review:

- `top_regressions`
- `added_slide_numbers`
- `removed_slide_numbers`
- provenance guidance in the comparison report