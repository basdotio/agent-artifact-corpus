#!/usr/bin/env bash
# AUTHOR: Erik Schultes (ORCID: 0000-0001-8888-635X)
# SESSION: Making MAC FAIR/npfdo Chat B2
# DATE: 2026-09-28
# URL: https://claude.ai/chat/06e46b23-6173-46d6-a59e-5b7fb629498f
# CREATED_AT: P04/R04 (revised P12/R12)
# DESCRIPTION: Gate then publish one signed np-FDO record; test registry unless "live" is named.
#
# It never reads or uses the signing key; signing happens before this script, in the skill.
# Bash 3.2 compatible (macOS default shell).
#
# Usage:
#   npfdo-gate-publish.sh <signed-file.trig> <expected-artefact-code RA...> <expected-sha256> <test|live>
#
# Environment:
#   NP_JAR   path to nanopub-<version>-jar-with-dependencies.jar (required)

set -u

fail() { echo "FAIL: $1"; exit 1; }

FILE="${1:-}"
CODE="${2:-}"
EXPECT_SHA="${3:-}"
TARGET="${4:-}"

[ -n "$FILE" ]       || fail "no signed file given"
[ -f "$FILE" ]       || fail "file not found: $FILE"
[ -n "$CODE" ]       || fail "no expected artefact code given"
[ -n "$EXPECT_SHA" ] || fail "no expected SHA-256 given"
[ -n "${NP_JAR:-}" ] || fail "NP_JAR is not set"
[ -f "$NP_JAR" ]     || fail "NP_JAR not found: $NP_JAR"

# Target is mandatory; test registry is the default only in the sense that the skill proposes it.
case "$TARGET" in
  test) REGISTRY="https://test.registry.knowledgepixels.com/" ;;
  live) REGISTRY="" ;;   # empty means the jar's default live network
  *) fail "target must be 'test' or 'live' (got: '${TARGET}')" ;;
esac

URI="https://w3id.org/np/${CODE}"

# Gate (a): SHA-256 equal.
GOT_SHA=$(shasum -a 256 "$FILE" | cut -d' ' -f1)
if [ "$GOT_SHA" = "$EXPECT_SHA" ]; then
  echo "PASS gate a: SHA-256 matches ($GOT_SHA)"
else
  echo "got:      $GOT_SHA"
  echo "expected: $EXPECT_SHA"
  fail "gate a: SHA-256 mismatch"
fi

# check -v output is reused for gates (b) and (c).
OUT=$(java -jar "$NP_JAR" check -v "$FILE" 2>&1)

# Gate (b): check -v names the expected Trusty URI.
if printf '%s\n' "$OUT" | grep -q "Signed and trusty: ${URI}"; then
  echo "PASS gate b: check names ${URI}"
else
  fail "gate b: check did not report 'Signed and trusty: ${URI}'"
fi

# Gate (c): the ISSUES block is empty (no lines between ISSUES: and Summary:).
ISS=$(printf '%s\n' "$OUT" | awk '/^ISSUES:/{f=1;next} /^Summary:/{f=0} f' | grep -c .)
if [ "$ISS" = "0" ]; then
  echo "PASS gate c: ISSUES block empty"
else
  printf '%s\n' "$OUT" | awk '/^ISSUES:/{f=1} /^Summary:/{f=0} f'
  fail "gate c: ISSUES block not empty ($ISS line(s))"
fi

echo "ALL GATES PASSED: publishing to ${TARGET}"

# Publish by the method the nanopub skill gives for the target (SKILL.md section
# "7. Wait for explicit publishing instruction").
if [ "$TARGET" = "test" ]; then
  java -jar "$NP_JAR" publish -u "$REGISTRY" "$FILE" || fail "publish to test registry failed"
else
  java -jar "$NP_JAR" publish "$FILE" || fail "publish to live network failed"
fi

# Wait, then fetch back and re-check the fetched copy.
sleep 10
TMP=$(mktemp -t npfdo-fetch-XXXXXX)
if [ "$TARGET" = "test" ]; then
  # Fetch back only from the test registry the record was published to. There is no fallback to
  # w3id: w3id resolves through the live network, so it can never confirm a test publication.
  curl -fsSL -H "Accept: application/trig" "${REGISTRY%/}/np/${CODE}" -o "$TMP" \
    || fail "fetch-back from test registry failed"
else
  # Live: resolve through w3id (SKILL.md passage "Fetching an existing nanopub").
  curl -fsSL -H "Accept: application/trig" "$URI" -o "$TMP" \
    || fail "fetch-back from live network failed"
fi

echo "--- fetched-back check ---"
java -jar "$NP_JAR" check -v "$TMP" 2>&1 | grep -q "Signed and trusty: ${URI}" \
  || fail "fetched copy did not verify as ${URI}"
rm -f "$TMP"

echo "DONE: ${URI} published to ${TARGET} and verified on fetch-back"
