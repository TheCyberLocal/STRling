#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"
dist_dir="${script_dir}/dist"
server_dir="${dist_dir}/server"
vendor_dir="${server_dir}/libs"
vendor_venv_dir="${dist_dir}/.vendor-venv"
python_cmd="${PYTHON:-python3}"
python_binding_src="${repo_root}/bindings/python/src/STRling"

rm -rf "${dist_dir}"
mkdir -p "${server_dir}" "${vendor_dir}" "${dist_dir}/out"

cleanup() {
  rm -rf "${vendor_venv_dir}"
}

trap cleanup EXIT

cp "${script_dir}/package.json" "${dist_dir}/package.json"
cp "${script_dir}/.vscodeignore" "${dist_dir}/.vscodeignore"

cp "${script_dir}/README.md" "${dist_dir}/README.md"
cp "${script_dir}/language-configuration.json" "${dist_dir}/language-configuration.json"
cp "${script_dir}/strling-icon.png" "${dist_dir}/strling-icon.png"
cp "${repo_root}/LICENSE" "${dist_dir}/LICENSE"
cp "${script_dir}/server/server.py" "${server_dir}/server.py"
cp "${script_dir}/server/island_extractor.py" "${server_dir}/island_extractor.py"

"${python_cmd}" -m venv "${vendor_venv_dir}"

venv_python="${vendor_venv_dir}/bin/python"
if [[ ! -x "${venv_python}" ]]; then
  venv_python="${vendor_venv_dir}/Scripts/python.exe"
fi

if [[ ! -x "${venv_python}" ]]; then
  echo "Failed to locate the temporary packaging Python environment." >&2
  exit 1
fi

"${venv_python}" -m pip install \
  --target "${vendor_dir}" \
  --implementation py \
  --only-binary=:all: \
  --no-user \
  --upgrade \
  pygls \
  lsprotocol

cp -R "${python_binding_src}" "${vendor_dir}/STRling"

npx esbuild "${script_dir}/client/extension.ts" \
  --bundle \
  --outfile="${dist_dir}/out/extension.js" \
  --external:vscode \
  --platform=node