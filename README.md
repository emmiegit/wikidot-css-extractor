# wikidot-css-extractor

An ad hoc system to pull style and component info from pages on the SCP Wiki. It uses the [Crom API](https://api.crom.avn.sh/) as its data source, causing this to be easily adapted by any wiki which is backed up by Crom.

It looks for inline styling, CSS modules, included pages, and CSS classes. In the absence of proper Wikidot tools to understand what styling is used on a site, this can help fill that gap.

Requires Python 3.8+.

**You can see the collected data here: https://ammongit.github.io/wikidot-css-extractor/**

### Execution

First, you need to install all the Python dependencies:

```
$ pip install -r requirements.txt
```

Then you need to edit `config.toml` to have the settings appropriate for your site.
Usually this is just editing `sites` to have the Wikidot names for your site. (e.g. `fondationscp` for FR)

For any of the other tools to work, you will want a downloaded local copy of all the page sources.
You pull this using `fetch.py`. This can take several minutes, depending on the size of your site.

```
$ ./fetch.py
```

There will now be a JSON file in `output/` with the filename specified in `config.toml` (default `output/results.json`).

If you are interested in searching through the gathered JSON data, you can use `grep.py`. (See also: [grep](https://en.wikipedia.org/wiki/Grep))  
Here is its usage information:

```
usage: grep.py [-h] [-i] [-v] [--compact] [--color {always,never,auto}] pattern [path]

grep for wikidot sites

positional arguments:
  pattern               The regular expression to search for
  path                  The file containing page sources to look through

optional arguments:
  -h, --help            show this help message and exit
  -i, --ignore-case     Whether to ignore case when searching
  -v, --invert-match    Invert the sense of matching, selecting all lines which don't match
  --compact             Whether to display the results in compact / line mode
  --color {always,never,auto}, --colour {always,never,auto}
                        Whether to use colors to highlight results
```

An example would be:

```
$ ./grep.py -i 'module redirect'
```

Which would find all instances of "module redirect" across all pages, case-insensitively.

To generate the HTML report visible, run the builder:

```
$ ./build.py
```

The generated HTML files are in `output/`.

If this repository is a fork, and you can push to it, you can publish a [GitHub Pages](https://pages.github.com/) site using:

```
$ ./publish.sh
```

This may take some time due to the size of the files. The large JSON blob (`output/results.json`) is _not_ uploaded.

### Composition

This repository has a few scripts:

* `fetch.py` retrieves all page sources via the Crom API, extracting styles and other information.
* `build.py` builds a static HTML page which contains the scraped information in a readable way. Presently this information is hosted on this repository's GitHub pages site.
* `publish.sh` takes the data created by `fetch.js` and `build.py` and pushes them to the `gh-pages` branch. You can do this manually, if you prefer.
* `grep.py` permits searching over all pages, as if using `grep` over a Wikidot site.

Previously it made use of these scripts:

* `scraper.js` runs through pages and looks for any CSS. Any styles, as well as the entire page sources are written to `extracted-styles.json`.
* `merge.js` is able to merge different JSON files into one. Because the scraper can continue off from incomplete jobs (anything remaining in `extracted-styles.json`), this can be used to take incomplete results and combine them.

This was prior to the switch of using the Crom API to retrieve Wikidot page sources instead of relying on scraping.

### Licensing

This code is available under the terms of the MIT License.
