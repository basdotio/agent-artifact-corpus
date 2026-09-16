# agent-artifact-corpus
#
# This repository owns the samples and the rules about them. It does not own the scorer:
# running a scanner over the corpus lives in that scanner's repository, where a drift gate
# can compare a generated report against a committed one.
#
# Keeping the scorer out is load-bearing rather than tidy. A label's `truth` block is written
# in technique names no scanner owns, so it has to be checkable with no build of any scanner
# present — which is also what lets someone benchmark their own tool against this corpus
# without us being involved.

HARNESS := cd harness && go run ./cmd/corpus

.PHONY: validate check-docs stats fetch derive derive-write test fmt help

help:
	@echo "validate      check every label, the taxonomy, every manifest entry and the doc pairs (offline)"
	@echo "stats         corpus composition, by credibility and by dimension x tier"
	@echo "fetch         materialise named layer-2 entries: make fetch E=\"id1 id2\""
	@echo "derive        dry-run coordinate derivation:  make derive E=\"skillsgoat\""
	@echo "derive-write  write derived labels into corpus/: make derive-write E=\"skillsgoat\""
	@echo "test          harness unit tests"

## Dry run. Reports what coordinates an upstream would yield and where the mapping is
## incomplete. Writes nothing — reading coverage must not rewrite the corpus.
derive:
	@$(HARNESS) derive $(E)

## Writes. Separate target rather than a flag on `derive` so that materialising the corpus is
## always something you asked for by name, never a side effect of looking at it.
derive-write:
	@$(HARNESS) derive $(E) --write

## Offline. Runs both checks and reports both, rather than stopping at the first — the same
## discipline the corpus applies to the scanners it measures.
## The subshell matters: HARNESS begins with `cd harness`, and without the parentheses that
## cd leaks into the rest of the recipe, so the recursive make runs from harness/ and reports
## "No rule to make target".
validate:
	@rc=0; ( $(HARNESS) validate ) || rc=$$?; \
	 $(MAKE) --no-print-directory check-docs || rc=1; \
	 exit $$rc

## Every hand-written document exists in both languages.
##
## This is a shell loop and not a Go package on purpose. It asks whether a file exists, which
## is what shell is for; it was 74 lines of Go plus 105 of test, which is four times the data
## it guards.
##
## It catches a MISSING translation, never a stale one. No line-count or heading-count
## heuristic is attempted: Chinese and English prose differ in length for ordinary reasons, so
## such a check would cry wolf and train people to ignore it. Content drift between the two
## languages is a real hole and it is named here rather than papered over.
check-docs:
	@missing=0; \
	for f in README.md docs/*.md; do \
	  case "$$f" in *.zh-CN.md) continue;; esac; \
	  z="$${f%.md}.zh-CN.md"; \
	  [ -f "$$z" ] || { echo "  - $$f has no Chinese counterpart; expected $$z"; missing=1; }; \
	done; \
	for z in README.zh-CN.md docs/*.zh-CN.md; do \
	  e="$${z%.zh-CN.md}.md"; \
	  [ -f "$$e" ] || { echo "  - $$z has no English counterpart; expected $$e"; missing=1; }; \
	done; \
	[ -f NOTICE.zh-CN.md ] || { echo "  - NOTICE has no Chinese counterpart; expected NOTICE.zh-CN.md"; missing=1; }; \
	if [ $$missing -ne 0 ]; then \
	  echo "docs: every hand-written document in this repository exists in both languages"; \
	  exit 1; \
	fi; \
	echo "documents   English and Chinese paired"

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
