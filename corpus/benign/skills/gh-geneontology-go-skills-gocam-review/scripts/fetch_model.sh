#!/usr/bin/env bash
# fetch_model.sh — download a GO-CAM model, read-only, from Noctua's public
# download route. No token, no cookie, nothing is written to Noctua.
#
# usage: fetch_model.sh <model id | Noctua URL> [outdir] [dev|production] [--dry-run]
#   model id   gomodel:ZFIN_ZDB-GENE-991207-22, ZFIN_ZDB-GENE-991207-22,
#              gomodel:68d3f4b800000234, or a Noctua URL that contains the id
#              (…/editor/graph/gomodel:X, …?model_id=gomodel:X, …/download/gomodel:X/owl);
#              a URL also names the server, which wins over the environment word
#   dev / --dev            http://noctua-dev.berkeleybop.org
#   production (default)   http://noctua.geneontology.org
#   outdir     default: $PWD   (arguments may come in any order)
#
# Writes <outdir>/<id>.ttl (the route is called /owl but the body is Turtle)
# and <outdir>/<id>.gpad, and prints both paths. Exit 1 if the model is not
# found or the body is not a model.
set -euo pipefail
dry=0; env=""; out=""; arg=""
for a in "$@"; do
    case "$a" in
        --dry-run) dry=1 ;;
        --dev|dev) env=dev ;;
        --prod|--production|prod|production) env=production ;;
        *) if [ -z "$arg" ]; then arg="$a"; else out="$a"; fi ;;
    esac
done
[ -n "$arg" ] || { sed -n '2,17p' "$0" >&2; exit 2; }
# A file the curator supplied (a Noctua "Export OWL"/Turtle, often saved as .txt): copy it
# under a timestamped name so the version checked is known, and stop.
if [ -f "$arg" ]; then
    out="${out:-$PWD}"; mkdir -p "$out"
    base="$(basename "$arg")"; stamp="$(date +%Y%m%dT%H%M%S)"
    if head -n 50 "$arg" | grep -qiE '^\s*(@prefix|prefix|@base|base)\b'; then
        dst="$out/supplied-$stamp-${base%.*}.ttl"
    else
        echo "the file does not look like Turtle (first bytes: $(head -c 80 "$arg" | tr '\n' ' ')); OWL functional syntax and JSON are not read here" >&2; exit 1
    fi
    cp -- "$arg" "$dst"
    echo "model:  supplied file $arg"
    echo "ttl:    $dst"
    exit 0
fi
# A Noctua URL names its own server; an explicit environment that disagrees is overridden, with a note.
url_env=""
case "$arg" in
    *noctua-dev.berkeleybop.org*) url_env=dev ;;
    *noctua.geneontology.org*)    url_env=production ;;
esac
if [ -n "$url_env" ] && [ -n "$env" ] && [ "$url_env" != "$env" ]; then
    echo "note: the URL is on the $url_env server; using that rather than '$env'" >&2
fi
env="${url_env:-${env:-production}}"
out="${out:-$PWD}"
case "$env" in
    production) host="http://noctua.geneontology.org" ;;
    dev)        host="http://noctua-dev.berkeleybop.org" ;;
esac
# Pull the id out of whatever was given: strip query strings and fragments first.
id="$arg"
case "$id" in
    *model_id=*)   id="${id#*model_id=}"; id="${id%%[&#]*}" ;;
    */download/*)  id="${id#*/download/}"; id="${id%%[/?#]*}" ;;
    */graph/*)     id="${id#*/graph/}"; id="${id%%[/?#]*}" ;;
esac
id="${id%%[?#]*}"
while [ "${id%/}" != "$id" ]; do id="${id%/}"; done
id="${id#gomodel:}"
case "$id" in
    *[!A-Za-z0-9_:.-]*|'') echo "that does not look like a model id: '$arg'" >&2; exit 2 ;;
esac
if [ "$dry" -eq 1 ]; then echo "would fetch gomodel:$id from $host into $out"; exit 0; fi
mkdir -p "$out"
ttl="$out/$id.ttl"; gpad="$out/$id.gpad"
code="$(curl -sS --retry 3 --retry-delay 2 -o "$ttl" -w '%{http_code}' "$host/download/gomodel:$id/owl" || echo "curl-failed")"
case "$code" in
    200) ;;
    400|404) echo "no model gomodel:$id on $host (HTTP $code; an unknown id answers 400)" >&2; rm -f "$ttl"; exit 1 ;;
    curl-failed) echo "could not reach $host (network or DNS); the model was not checked" >&2; rm -f "$ttl"; exit 1 ;;
    *) echo "$host answered HTTP $code for gomodel:$id; try again later" >&2; rm -f "$ttl"; exit 1 ;;
esac
if ! head -n 50 "$ttl" | grep -qiE '^\s*(@prefix|prefix|@base|base)\b'; then
    echo "the download for gomodel:$id is not Turtle (first bytes: $(head -c 80 "$ttl" | tr '\n' ' '))" >&2
    rm -f "$ttl"; exit 1
fi
curl -fsS --retry 2 -o "$gpad" "$host/download/gomodel:$id/gpad" 2>/dev/null || { echo "note: no GPAD export for gomodel:$id (continuing with the Turtle only)" >&2; rm -f "$gpad"; }
echo "model:  gomodel:$id ($env, $host)"
echo "id:     $id"
echo "env:    $env"
echo "ttl:    $ttl"
[ -f "$gpad" ] && echo "gpad:   $gpad"
exit 0
