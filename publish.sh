#!/usr/bin/env bash
set -eu

# Setup
temp_dir="$(mktemp -d)"

function on_exit() {
	rm -rf "$temp_dir"
}

trap on_exit EXIT SIGINT SIGTERM

# Execution
set -x

[[ -f output/index.html ]]
[[ -f output/pages/index.html ]]
[[ -f output/pages/scp-001.html ]]

# NOTE: we aren't copying the JSON file,
# it's too big and we don't want to use GitHub LFS

cp -a static output/*.html output/pages  "$temp_dir"
git checkout gh-pages
cp -a "$temp_dir"/* .
git add .
git commit -m 'Update generated files.'
git push
git checkout -
