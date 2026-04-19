#!/bin/bash
set -e

VERSION="${STRLING_VERSION:-0.0.0.dev}"
GEMSPEC="strling.gemspec"
TEMPLATE="strling-template.gemspec"
TEMPLATE_STASH=".strling-template.gemspec.setup"
GENERATED_GEMSPEC=0

cleanup() {
    if [ -f "$TEMPLATE_STASH" ]; then
        mv "$TEMPLATE_STASH" "$TEMPLATE"
    fi
    if [ "$GENERATED_GEMSPEC" -eq 1 ] && [ -f "$GEMSPEC" ]; then
        rm -f "$GEMSPEC"
    fi
}

trap cleanup EXIT

if [ ! -f "$TEMPLATE" ]; then
    echo "Error: $TEMPLATE not found."
    exit 1
fi

if [ -f "$TEMPLATE_STASH" ]; then
    rm -f "$TEMPLATE_STASH"
fi

mv "$TEMPLATE" "$TEMPLATE_STASH"

if [ ! -f "$GEMSPEC" ]; then
    sed "s/VERSION/${VERSION}/g" "$TEMPLATE_STASH" > "$GEMSPEC"
    GENERATED_GEMSPEC=1
fi

bundle install
