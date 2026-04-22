#!/usr/bin/env bash

# Module Pedagogy:
# This script takes the packaged STRling VS Code payload from dist/ and copies
# it into the active VS Code server extension directory for the current user.
# It owns the final installation step, ownership repair, cache cleanup, and the
# metadata refresh needed to make the extension visible in WSL sessions.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dist_dir="${script_dir}/dist"
target_home="${HOME}"
target_extensions_dir="${target_home}/.vscode-server/extensions"
target_extension_dir="${target_extensions_dir}/strling-lang.vscode-strling-0.1.0"
cached_vsix_dir="${target_home}/.vscode-server/data/CachedExtensionVSIXs"

if [[ ! -f "${dist_dir}/package.json" ]]; then
  echo "Packaged extension payload is missing. Run npm run package first." >&2
  exit 1
fi

home_owner="$(stat -c '%u:%g' "${target_home}")"

rm -rf "${target_extension_dir}"
mkdir -p "${target_extension_dir}"

cp -R "${dist_dir}/." "${target_extension_dir}/"

rm -f "${target_extension_dir}/vscode-strling.vsix"

chown -R "${home_owner}" "${target_extension_dir}"

mkdir -p "${cached_vsix_dir}"
find "${cached_vsix_dir}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +

echo "Installed STRling extension into ${target_extension_dir}"