#!/usr/bin/env node

const fs = require('fs/promises');
const process = require('process');

async function main() {
  if (process.argv.length < 5) {
    console.error("Usage: merge.js input-file... output-file");
    process.exit(1);
  }

  const inputFiles = process.argv.slice(2);
  const outputFile = inputFiles.pop();
  let object = {};

  for (const inputFile of inputFiles) {
    const inputJSON = await fs.readFile(inputFile);
    const inputObject = JSON.parse(inputJSON);

    object = {
      ...object,
      ...inputObject,
    };
  }

  const json = JSON.stringify(object, null, 4);
  await fs.writeFile(outputFile, json);
}

main();
