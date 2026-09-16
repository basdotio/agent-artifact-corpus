# agent-guard-corpus
#
# This repository owns the samples and the rules about them. It does not own the scorer:
# running aguard over the corpus lives in the tool repository, where a drift gate can compare
# a generated report against a committed one. Keeping the scorer out means the corpus
# validates with no build of the tool present.

HARNESS := cd harness && go run ./cmd/corpus

.PHONY: validate stats fetch test fmt help

help:
	@echo "validate   check every _label.yaml and manifest entry; run the leakage gate (offline)"
	@echo "stats      corpus composition"
	@echo "fetch      materialise named layer-2 entries: make fetch E=\"id1 id2\""
	@echo "test       harness unit tests"

## Offline. CI runs this on every change.
validate:
	@$(HARNESS) validate

stats:
	@$(HARNESS) stats

## Network. Name the entries: `make fetch E="datadog-ai-skills skillsgoat"`.
## Bare `make fetch` lists what is available and fetches nothing — one manifest entry is
## 138,133 samples, so there is no fetch-everything default.
## Refuses to silently re-pull a checkout that has drifted from its pinned commit.
fetch:
	@$(HARNESS) fetch $(E)

test:
	@cd harness && go test -race ./...

fmt:
	@cd harness && gofmt -l . && go vet ./...
