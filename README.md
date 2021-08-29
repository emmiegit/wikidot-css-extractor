# wikidot-css-scraper

A quick, ad hoc script to scrape both CSS from pages on the SCP Wiki (though it could be adapted to work on any Wikidot site). It looks for both inline styling (e.g. `style="color: red;"`), and CSS modules (i.e. `[[module CSS]]`). In the absence of proper Wikidot tools to understand what styling is used on a site, this can help fill that gap.

This does not search all pages, only mainlist SCP articles (excluding -Js, 001s, etc.)

Available under the terms of the MIT License.
