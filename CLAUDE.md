# Claude Code Instructions

## Testing

After making non-trivial changes to `instagiffer.py` or test code, run the smoke test
to verify the app still fully works:

```
make test
```

This launches the app via GUI automation, loads a video, applies crop/effects/caption,
creates a GIF, verifies the output, and generates a bug report. Run this between logical
change sets — don't batch up many changes before testing.
