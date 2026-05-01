# Preview provenance

Use `preview-pptx` whenever the review needs to trust the final rendered artifact.

Recommended flow:

1. `render`
2. `preview-pptx`
3. inspect `preview-manifest.json`
4. compare/promote only after provenance matches

The manifest captures:

- `preview_source`
- `backend_requested`
- `backend_used`
- `office_conversion_strategy`
- slide ordering and file pairing