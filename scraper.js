#!/usr/bin/env node

const fs = require('fs/promises');
const puppeteer = require('puppeteer');

const BASE_URL = 'https://scp-wiki.wikidot.com/'

const REGEX_MODULE_CSS = /\[\[module +css\]\]\n(.+?)\n\[\[\/module\]\]/gmis;
const REGEX_INLINE_CSS = /style="(.+?)"[^\]]*?\]\]/gi;
const REGEX_CLASSES = /class="([^\]]+?)"/gi;

const STYLES_FILENAME = 'output/extracted-styles.json';

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function scrape(page, url, delayMs) {
  try {
    console.log(`* Scraping ${url}`);

    await page.goto(url);
    await page.waitForTimeout(delayMs);
    await page.waitForSelector('#page-content');

    // Check if the page doesn't exist
    const pageExists = await page.evaluate(() => (
      document.querySelector('#more-options-button') !== null
    ));

    if (!pageExists) {
      console.log('= Page not present, skipping');
      return undefined;
    }

    const pageTitle = await page.evalulate(() => (
      document.querySelector('#page-title').innerHTML
    ));

    // Click "+ options" button
    await page.waitForSelector('#more-options-button');
    await page.focus('#more-options-button');
    await page.click('#more-options-button');

    // Click "page source" button
    await page.waitForSelector('#view-source-button');
    await page.focus('#view-source-button');
    await page.click('#view-source-button');

    // Copy page source
    await page.waitForSelector('.page-source');
    await page.focus('.page-source');

    const pageSource = await page.evaluate(() => {
      const pageSourceElement = document.querySelector('.page-source');
      if (pageSourceElement === null) {
        throw "Can't find page source element";
      }

      return pageSourceElement.innerHTML
        .replace(/<br>/g, '')
        .replace(/&nbsp;/g, ' ')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&amp;/g, '&')
        .replace(/^\n\t/, '');
    });

    // Extract CSS
    const moduleStyles = [];
    for (const match of pageSource.matchAll(REGEX_MODULE_CSS)) {
      moduleStyles.push(match[1]);
    }

    const inlineStyles = [];
    for (const match of pageSource.matchAll(REGEX_INLINE_CSS)) {
      styles.push(match[1]);
    }

    const classes = [];
    for (const match of pageSource.matchAll(REGEX_CLASSES)) {
      const klasses = match[1].split(' ');
      for (const klass of klasses) {
        classes.push(klass);
      }
    }

    return { pageSource, pageTitle, moduleStyles, inlineStyles, classes };
  } catch (error) {
    console.error(error);
    throw error;
  }
}

async function readStyles() {
  try {
    const stylesJSON = await fs.readFile(STYLES_FILENAME);
    const styles = JSON.parse(stylesJSON);
    console.log(`Loaded ${Object.keys(styles).length} styles...`);
    return styles;
  } catch (error) {
    console.log('Cannot load pre-existing styles.');
    return;
  }
}

async function main() {
  const extractedStyles = await readStyles();
  let browser;

  async function saveStyles() {
    const json = JSON.stringify(extractedStyles, null, 4);
    await fs.writeFile(STYLES_FILENAME, json);
  }

  function scpSlug(number) {
    if (number < 1000) {
      return 'scp-' + String(number).padStart(3, '0');
    } else {
      return 'scp-' + String(number).padStart(4, '0');
    }
  }

  async function extract(page, slug) {
    const DELAYS_MS = [500, 2000, 6000];
    const url = BASE_URL + slug;

    // Scraping attempts
    for (let i = 0; i < 3; i++) {
      try {
        extractedStyles[slug] = await scrape(page, url, DELAYS_MS[i]);
        break;
      } catch (error) {
        if (i < 2) {
          console.log('! Failed to scrape, retrying...')
        } else {
          console.log('! Failed to scrape, giving up!')
        }
      }
    }

    // Save every iteration to allow continuation
    await saveStyles();

    // Avoid rate-limiting
    await sleep(2000);
  }

  try {
    console.log("Starting up scraper...");
    browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();

    for (let i = 0; i < 7000; i++) {
      const slug = scpSlug(i);
      if (extractedStyles[slug] === undefined) {
        await extract(page, slug);
      }
    }
  } catch (error) {
    console.error(`Error running scraper: ${error}`);
  } finally {
    await browser.close();
    await saveStyles();
  }
}

main();
