# Contributing

Keep changes scoped to an observable behavior: preparation, review, submission, collection, install or export. Describe the trigger and resulting behavior in your pull request. Preserve attribution and add a focused regression for a demonstrated reliability defect.

Install the runtime's requirements in an isolated environment, then run:

```bash
python scripts/check.py
python scripts/run_tests.py
```

The test runner blocks outbound connections; tests use local synthetic media and mocked provider responses. Do not add provider keys, paid calls, private footage or signed URLs to CI. Source/recipe changes must invalidate earlier approval and stage reuse. A timed-out billed POST is ambiguous and must not automatically requeue.

For provider changes, cite current primary documentation and separate mocked/local validation from an authorized live run. For masks/tracking/audio changes, include actual full-clip review evidence for media you can share. Passing test counts do not establish visual quality.

Do not add the tutorial, upstream branded artwork or example footage to this repository. Use your own media or explicitly redistributable fixtures. Runtime data, models and credentials belong outside version control.
