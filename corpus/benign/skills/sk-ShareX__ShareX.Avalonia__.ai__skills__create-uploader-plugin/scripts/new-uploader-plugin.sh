#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: new-uploader-plugin.sh --plugin-name <name> [options]

Options:
  --plugin-name <name>      Plugin name (required)
  --plugin-id <id>          Plugin id (default: derived from plugin name)
  --display-name <name>     Display name (default: "<PluginStem> Uploader")
  --output-root <path>      Output root (default: src/desktop/plugins)
  --solution-path <path>    Solution path (default: src/desktop/XerahS.sln)
  --add-to-solution         Add generated project to solution under Plugins
  --force                   Overwrite existing plugin folder
  -h, --help                Show this help
USAGE
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: required command not found: $1" >&2
    exit 1
  fi
}

to_pascal_case() {
  local value="$1"
  local cleaned
  cleaned="$(echo "$value" | sed -E 's/[^A-Za-z0-9]+/ /g')"
  local out=""
  local part
  for part in $cleaned; do
    local first rest
    first="${part:0:1}"
    rest="${part:1}"
    out+="${first^^}${rest}"
  done
  if [[ -z "$out" ]]; then
    echo "Error: unable to derive a valid plugin name from '$value'." >&2
    exit 1
  fi
  echo "$out"
}

to_plugin_id() {
  local value="$1"
  local out
  out="$(echo "$value" | sed -E 's/[^A-Za-z0-9]+//g' | tr '[:upper:]' '[:lower:]')"
  if [[ -z "$out" ]]; then
    echo "Error: unable to derive a valid plugin id from '$value'." >&2
    exit 1
  fi
  echo "$out"
}

map_output_relative_path() {
  local rel="$1"
  case "$rel" in
    Plugin.csproj.tmpl) echo "${ASSEMBLY_NAME}.csproj" ;;
    plugin.json.tmpl) echo "plugin.json" ;;
    ConfigModel.cs.tmpl) echo "${CONFIG_MODEL_CLASS}.cs" ;;
    Provider.cs.tmpl) echo "${PROVIDER_CLASS}.cs" ;;
    Uploader.cs.tmpl) echo "${UPLOADER_CLASS}.cs" ;;
    ViewModels/ConfigViewModel.cs.tmpl) echo "ViewModels/${CONFIG_VIEWMODEL_CLASS}.cs" ;;
    Views/ConfigView.axaml.tmpl) echo "Views/${CONFIG_VIEW_CLASS}.axaml" ;;
    Views/ConfigView.axaml.cs.tmpl) echo "Views/${CONFIG_VIEW_CLASS}.axaml.cs" ;;
    *)
      echo "Error: unmapped template file: $rel" >&2
      exit 1
      ;;
  esac
}

PLUGIN_NAME=""
PLUGIN_ID=""
DISPLAY_NAME=""
OUTPUT_ROOT="src/desktop/plugins"
SOLUTION_PATH="src/desktop/XerahS.sln"
ADD_TO_SOLUTION=0
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plugin-name)
      PLUGIN_NAME="${2:-}"
      shift 2
      ;;
    --plugin-id)
      PLUGIN_ID="${2:-}"
      shift 2
      ;;
    --display-name)
      DISPLAY_NAME="${2:-}"
      shift 2
      ;;
    --output-root)
      OUTPUT_ROOT="${2:-}"
      shift 2
      ;;
    --solution-path)
      SOLUTION_PATH="${2:-}"
      shift 2
      ;;
    --add-to-solution)
      ADD_TO_SOLUTION=1
      shift
      ;;
    --force)
      FORCE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [[ -z "$PLUGIN_NAME" ]]; then
        PLUGIN_NAME="$1"
        shift
      else
        echo "Error: unknown option '$1'" >&2
        usage >&2
        exit 1
      fi
      ;;
  esac
done

if [[ -z "$PLUGIN_NAME" ]]; then
  echo "Error: --plugin-name is required." >&2
  usage >&2
  exit 1
fi

require_cmd find
require_cmd sed
require_cmd tr
require_cmd python3

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd "$script_dir/../../../.." && pwd -P)"
template_root="$script_dir/../assets/desktop-plugin-template"

if [[ ! -d "$template_root" ]]; then
  echo "Error: template folder not found: $template_root" >&2
  exit 1
fi

plugin_stem_input="${PLUGIN_NAME%.Plugin}"
PLUGIN_STEM="$(to_pascal_case "$plugin_stem_input")"

if [[ -z "$PLUGIN_ID" ]]; then
  RESOLVED_PLUGIN_ID="$(to_plugin_id "$PLUGIN_STEM")"
else
  RESOLVED_PLUGIN_ID="$(to_plugin_id "$PLUGIN_ID")"
fi

if [[ -z "$DISPLAY_NAME" ]]; then
  RESOLVED_DISPLAY_NAME="${PLUGIN_STEM} Uploader"
else
  RESOLVED_DISPLAY_NAME="$(echo "$DISPLAY_NAME" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
fi

ASSEMBLY_NAME="XerahS.${PLUGIN_STEM}.Plugin"
NAMESPACE_NAME="ShareX.${PLUGIN_STEM}.Plugin"
PROVIDER_CLASS="${PLUGIN_STEM}Provider"
UPLOADER_CLASS="${PLUGIN_STEM}Uploader"
CONFIG_MODEL_CLASS="${PLUGIN_STEM}ConfigModel"
CONFIG_VIEWMODEL_CLASS="${PLUGIN_STEM}ConfigViewModel"
CONFIG_VIEW_CLASS="${PLUGIN_STEM}ConfigView"
FOLDER_NAME="${PLUGIN_STEM}.Plugin"

plugins_root="$repo_root/$OUTPUT_ROOT"
project_directory="$plugins_root/$FOLDER_NAME"
project_path="$project_directory/${ASSEMBLY_NAME}.csproj"
resolved_solution_path="$repo_root/$SOLUTION_PATH"

if [[ -d "$project_directory" && "$FORCE" -ne 1 ]]; then
  echo "Error: plugin directory already exists: $project_directory. Use --force to overwrite." >&2
  exit 1
fi

if [[ -d "$project_directory" ]]; then
  rm -rf "$project_directory"
fi

mkdir -p "$project_directory"

while IFS= read -r template_file; do
  rel_template="${template_file#${template_root}/}"
  out_rel="$(map_output_relative_path "$rel_template")"
  output_path="$project_directory/$out_rel"
  mkdir -p "$(dirname "$output_path")"

  TEMPLATE_FILE="$template_file" OUTPUT_FILE="$output_path" \
  T_PLUGIN_STEM="$PLUGIN_STEM" \
  T_PLUGIN_ID="$RESOLVED_PLUGIN_ID" \
  T_DISPLAY_NAME="$RESOLVED_DISPLAY_NAME" \
  T_ASSEMBLY_NAME="$ASSEMBLY_NAME" \
  T_NAMESPACE="$NAMESPACE_NAME" \
  T_PROVIDER_CLASS="$PROVIDER_CLASS" \
  T_UPLOADER_CLASS="$UPLOADER_CLASS" \
  T_CONFIG_MODEL_CLASS="$CONFIG_MODEL_CLASS" \
  T_CONFIG_VIEWMODEL_CLASS="$CONFIG_VIEWMODEL_CLASS" \
  T_CONFIG_VIEW_CLASS="$CONFIG_VIEW_CLASS" \
  python3 - <<'PY'
import os

template_path = os.environ["TEMPLATE_FILE"]
output_path = os.environ["OUTPUT_FILE"]

tokens = {
    "__PLUGIN_STEM__": os.environ["T_PLUGIN_STEM"],
    "__PLUGIN_ID__": os.environ["T_PLUGIN_ID"],
    "__DISPLAY_NAME__": os.environ["T_DISPLAY_NAME"],
    "__ASSEMBLY_NAME__": os.environ["T_ASSEMBLY_NAME"],
    "__NAMESPACE__": os.environ["T_NAMESPACE"],
    "__PROVIDER_CLASS__": os.environ["T_PROVIDER_CLASS"],
    "__UPLOADER_CLASS__": os.environ["T_UPLOADER_CLASS"],
    "__CONFIG_MODEL_CLASS__": os.environ["T_CONFIG_MODEL_CLASS"],
    "__CONFIG_VIEWMODEL_CLASS__": os.environ["T_CONFIG_VIEWMODEL_CLASS"],
    "__CONFIG_VIEW_CLASS__": os.environ["T_CONFIG_VIEW_CLASS"],
}

with open(template_path, "r", encoding="utf-8") as f:
    content = f.read()

for key, value in tokens.items():
    content = content.replace(key, value)

with open(output_path, "w", encoding="utf-8", newline="") as f:
    f.write(content)
PY
done < <(find "$template_root" -type f | sort)

if [[ "$ADD_TO_SOLUTION" -eq 1 ]]; then
  require_cmd dotnet
  if [[ ! -f "$resolved_solution_path" ]]; then
    echo "Error: solution file not found: $resolved_solution_path" >&2
    exit 1
  fi
  dotnet sln "$resolved_solution_path" add "$project_path" --solution-folder Plugins
fi

echo "Created plugin scaffold:"
echo "  Folder: $project_directory"
echo "  Project: $project_path"
echo "  PluginId: $RESOLVED_PLUGIN_ID"
echo "  DisplayName: $RESOLVED_DISPLAY_NAME"
echo ""
echo "Next steps:"
echo "  1. Implement upload logic in ${UPLOADER_CLASS}.cs"
echo "  2. Tighten validation and settings in ${PROVIDER_CLASS}.cs and ${CONFIG_MODEL_CLASS}.cs"
echo "  3. Replace the generic config UI with service-specific fields if needed"
echo "  4. Build with: dotnet build $project_path -m:1"