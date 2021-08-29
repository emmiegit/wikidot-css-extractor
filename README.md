# wikidot-css-extractor

An ad hoc system to pull CSS from pages on the SCP Wiki (though it could be adapted to work on any site supported by Crom). It looks for both inline styling (e.g. `style="color: red;"`), CSS modules (i.e. `[[module CSS]]`), as well as any CSS classes referenced. In the absence of proper Wikidot tools to understand what styling is used on a site, this can help fill that gap.

**You can see the collected data here: https://ammongit.github.io/wikidot-css-extractor/**

### Utilization

This repository has a few scripts:

* `fetch.py` retrieves all page sources via the Crom API, retrieves styles, and writes them to `extracted-styles.json`
* `build.py` builds a static HTML page which contains the scraped information in a readable way. Presently this information is hosted on this repository's GitHub pages site.
* `publish.sh` takes the data created by `fetch.js` and `build.py` and pushes them to the `gh-pages` branch. You can do this manually, if you prefer.

Previously it made use of these scripts:

* `scraper.js` runs through pages and looks for any CSS. Any styles, as well as the entire page sources are written to `extracted-styles.json`.
* `merge.js` is able to merge different JSON files into one. Because the scraper can continue off from incomplete jobs (anything remaining in `extracted-styles.json`), this can be used to take incomplete results and combine them.

This was prior to the switch of using the Crom API to retrieve Wikidot page sources instead of relying on scraping.

### Licensing

This code is available under the terms of the MIT License.
