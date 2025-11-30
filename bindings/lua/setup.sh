#!/bin/bash
set -e

# Install dependencies from rockspec
luarocks install --only-deps strling-scm-1.rockspec

# Install test runner
luarocks install busted

# Build/Install the rock locally to ensure paths are correct
luarocks make
