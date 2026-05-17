# Baseline management

Only promote a baseline after the new preview set has been reviewed.

Recommended sequence:

1. render the updated deck
2. generate real previews with `preview-pptx` or run `review-pptx`
3. compare against the approved baseline with `compare-pptx`
4. inspect provenance guidance and top regressions
5. promote the new preview set

```bash
ppt-creator promote-baseline outputs/current_previews outputs/golden_previews
```