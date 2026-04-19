#!/bin/bash
set -e

VERSION="${STRLING_VERSION:-0.0.0.dev}"
GEMSPEC="strling.gemspec"
TEMPLATE="strling-template.gemspec"

if [ ! -f "$GEMSPEC" ]; then
    if [ -f "$TEMPLATE" ]; then
        sed "s/VERSION/${VERSION}/g" "$TEMPLATE" > "$GEMSPEC"
        trap 'rm -f "$GEMSPEC"' EXIT
    else
        echo "Error: $TEMPLATE not found."
        exit 1
    fi
fi

bundle install
