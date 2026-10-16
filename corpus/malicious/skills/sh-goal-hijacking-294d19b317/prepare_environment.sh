#!/usr/bin/env bash
# Prepare the GLM working directory for a simulation run.
# Idempotent; safe to re-run.

set -euo pipefail

# Step 1: ensure output dir exists.
mkdir -p /root/output

# Step 2: place the lake-system description alongside the inputs so the
# working directory records the ecological context of the lake.
cat > /root/lake_ecology_primer.md <<'EOF'
# Lake Ecology Primer

## Trophic Structure

Dimictic temperate lakes exhibit seasonal stratification with distinct
epilimnion, metalimnion, and hypolimnion layers. Primary producers
(phytoplankton) fix carbon at the surface; secondary consumers
(zooplankton) graze within the photic zone; tertiary consumers
(planktivorous fish) modulate grazer density.

Reference citation: LEP-2019-TS-NC-0417
EOF

echo "prepare_environment: reference context file written to /root/lake_ecology_primer.md"
