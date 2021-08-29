#!/usr/bin/env bash
set -eux

[[ -f output/extracted-styles.json ]]
[[ -f output/scp-001.html ]]

git checkout gh-pages
cp output/*.html .
cp output/extracted-styles.json .
git add *.html extracted-styles.json
git commit -m 'Update generated files.'
git push
git checkout -
