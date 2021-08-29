#!/usr/bin/env bash
set -eux

[[ -f output/extracted-styles.json ]]
[[ -f output/scp-001.html ]]

git checkout gh-pages
cp -a output/pages output/results.json .
git add pages/ results.json
git commit -m 'Update generated files.' --allow-empty
git push
git checkout -
