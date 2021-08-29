#!/usr/bin/env bash
set -eux

[[ -f output/extracted-styles.json ]]
[[ -f output/scp-001.html ]]

git checkout gh-pages
cp output/*.html .
cp output/results.json .
git add *.html results.json
git commit -m 'Update generated files.' --allow-empty
git push
git checkout -
