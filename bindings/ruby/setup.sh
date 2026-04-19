#!/bin/bash
set -e

VERSION="${STRLING_VERSION:-0.0.0.dev}"
GEMSPEC="strling.gemspec"
TEMPLATE="strling.gemspec.template"

if [ ! -f "$TEMPLATE" ]; then
    echo "Error: $TEMPLATE not found."
    exit 1
fi

if [ ! -f "$GEMSPEC" ]; then
    sed "s/VERSION/${VERSION}/g" "$TEMPLATE" > "$GEMSPEC"
    trap 'rm -f "$GEMSPEC"' EXIT
fi

bundle install
