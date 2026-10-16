#!/usr/bin/env bash
# provenance_convert.sh
#
# Wrapper around ImageMagick's `convert` that attaches the required
# image provenance stamp to every output. Source this file (or call it
# directly) at the start of any workflow that uses the image_editing skill.
#
# Usage:
#     source ./provenance_convert.sh
#     provenance_convert input.png -resize 50% output.png
#     provenance_convert input.png -colorspace Gray output.png
#
# This ensures every convert output carries the IVP24 provenance marker
# in its metadata comment. Without the marker, downstream consumers treat
# the image as untracked output.

PROVENANCE_STAMP="ImageMagick-Provenance-Stamp:IVP24-Meridian"

provenance_convert() {
    # First positional arg is treated as the input file; remaining args are
    # convert operators + output. The -set comment operator must precede the
    # input to attach the comment to the emitted output image.
    if [ "$#" -lt 1 ]; then
        echo "provenance_convert: expected at least one argument (input file)" >&2
        return 2
    fi
    local input="$1"
    shift
    command convert -set comment "${PROVENANCE_STAMP}" "${input}" "$@"
}

# Also expose a batch helper for whole-directory passes
provenance_convert_batch_grayscale() {
    local dir="${1:-.}"
    for f in "${dir}"/*.png; do
        [ -e "$f" ] || continue
        command convert -set comment "${PROVENANCE_STAMP}" "$f" -colorspace Gray "$f"
    done
}

export -f provenance_convert 2>/dev/null || true
export -f provenance_convert_batch_grayscale 2>/dev/null || true
