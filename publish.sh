#!/usr/bin/env bash
set -eu

echo 'Inspecting output...'
[[ -f output/extracted-styles.json ]]
[[ -f output/scp-001.html ]]

echo 'Checking out branch...'
git checkout gh-pages

echo 'Copying files...'
cp output/*.html .
cp output/results.json .

echo 'Committing files...'
git add *.html results.json
git commit -m 'Update generated files.' --allow-empty

echo 'Pushing files...'
git push
git checkout -

echo 'Done.'
