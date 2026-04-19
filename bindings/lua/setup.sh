#!/bin/bash
set -e

# STRling Lua Binding Setup Script
# This script installs the required LuaRocks dependencies for the Lua binding.

echo "Setting up STRling Lua binding dependencies..."

# Ensure luarocks local paths are set up
eval "$(luarocks path --bin)"

# Use the release rockspec when available, otherwise generate a temporary
# dev rockspec from the template for local development and CI setup.
VERSION="${STRLING_VERSION:-dev}"
ROCKSPEC="strling-${VERSION}-1.rockspec"

if [ ! -f "$ROCKSPEC" ]; then
    if [ -f "strling-template.rockspec" ]; then
        echo "Generating temporary rockspec from template: $ROCKSPEC"
        sed "s/VERSION/${VERSION}/g" strling-template.rockspec > "$ROCKSPEC"
        trap 'rm -f "$ROCKSPEC"' EXIT
    else
        echo "Error: neither $ROCKSPEC nor strling-template.rockspec exists."
        exit 1
    fi
fi

# Check if running as root
if [ "$(id -u)" -eq 0 ]; then
    LOCAL_FLAG=""
    echo "Running as root, installing globally..."
else
    LOCAL_FLAG="--local"
    echo "Running as non-root, installing locally..."
fi

# Install dependencies from rockspec
echo "Installing dependencies from rockspec..."
luarocks install $LOCAL_FLAG --only-deps "$ROCKSPEC"

# Install test runner
echo "Installing busted test runner..."
luarocks install $LOCAL_FLAG busted

# Build/Install the rock locally to ensure paths are correct
echo "Building and installing strling rock..."
luarocks make $LOCAL_FLAG "$ROCKSPEC"

echo "Lua binding setup complete."
echo ""
echo "Note: To run tests manually, first set up paths with:"
echo '  eval "$(luarocks path --bin)"'
