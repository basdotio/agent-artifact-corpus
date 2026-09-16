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
	@echo "fetch      materialise layer 2 into ./cache (network; verifies pinned commits)"
	@echo "test       harness unit tests"

## Offline. CI runs this on every change.
validate:
	@$(HARNESS) validate

stats:
	@$(HARNESS) stats

## Network. Refuses to silently re-pull a checkout that has drifted from its pinned commit.
fetch:
	@$(HARNESS) fetch

test:
	@cd harness && go test -race ./...

fmt:
	@cd harness && gofmt -l . && go vet ./...
