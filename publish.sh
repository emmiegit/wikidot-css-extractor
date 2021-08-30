#!/usr/bin/env bash
set -eux

[[ -f output/results.json ]]
[[ -f output/index.html ]]
[[ -f output/pages/index.html ]]
[[ -f output/pages/scp-001.html ]]

git checkout gh-pages
cp -a output/*.html output/pages output/results.json .
git add *.html pages/ results.json
git commit -m 'Update generated files.'
git push
git checkout -
