#!/usr/bin/env python3

import asyncio
import itertools
import json
import os
import re
import traceback

import aiohttp

OUTPUT_FILENAME = 'output/results.json'

REGEX_WIKIDOT_URL = re.compile(r'^https?://([\w\-]+)\.wikidot\.com/(.+)$')
REGEX_MODULE_CSS = re.compile(r'\[\[module +css\]\]\n(.+?)\n\[\[/module\]\]', re.IGNORECASE | re.DOTALL)
REGEX_INLINE_CSS = re.compile(r'style="(.+?)"[^\]]*?\]\]', re.MULTILINE | re.IGNORECASE)
REGEX_INCLUDES = re.compile(r'\[\[include +([^ \n]+)(?: |\]\])', re.MULTILINE | re.IGNORECASE)
REGEX_CLASSES = re.compile(r'class="([^\]]+?)"', re.MULTILINE | re.IGNORECASE)

CROM_ENDPOINT = "https://api.crom.avn.sh/"
CROM_SITES = ["http://scp-wiki.wikidot.com/"]
CROM_RETRIES = 3
CROM_HEADERS = {
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

CROM_QUERY = """
{
    pages(
        filter: {
            anyBaseUrl: $anyBaseUrl,
        },
        sort: {
            order: ASC,
            key: CREATED_AT,
        },
        after: $cursor,
    ) {
        edges {
            node {
                url,
                wikidotInfo {
                    title,
                    category,
                    wikidotId,
                    source,
                }
            }
        },
        pageInfo {
            hasNextPage,
            endCursor,
        }
    }
}
"""

class Container:
    __slots__ = ("value",)

    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

class CromError(RuntimeError):
    def __init__(self, errors):
        super().__init__(self._get_message(errors))
        self.errors = errors

    @staticmethod
    def _get_message(errors):
        if len(errors) == 1:
            return errors[0]
        else:
            return errors

class Crawler:
    def __init__(self):
        self.cursor = None
        self.pages = {}
        self.path = OUTPUT_FILENAME

    def load(self, path=OUTPUT_FILENAME):
        with open(path) as file:
            data = json.load(file)

        self.cursor = data['cursor']
        self.pages = data['pages']
        self.path = path

    def save(self):
        data = {
            'cursor': self.cursor,
            'pages': self.pages,
        }

        with open(self.path, 'w') as file:
            json.dump(data, file, indent=4)
            file.write('\n')

    async def raw_request(self, session, query, variables):
        for key, value in variables.items():
            query = query.replace(key, json.dumps(value))

        payload = json.dumps({ 'query': query }).encode('utf-8')

        async with session.post(CROM_ENDPOINT, data=payload, headers=CROM_HEADERS) as r:
            json_body = await r.json()

            if 'errors' in json_body:
                raise CromError(json_body['errors'])

            return json_body['data']

    async def next_pages(self, session):
        variables = {
            "$anyBaseUrl": CROM_SITES,
            "$cursor": self.cursor,
        }

        json_body = await self.raw_request(session, CROM_QUERY, variables)
        pages = json_body['pages']
        page_info = pages['pageInfo']

        has_next_page = page_info['hasNextPage']
        self.cursor = page_info['endCursor']
        return pages['edges'], has_next_page

    @staticmethod
    def process_edge(edge):
        # Extract fields
        node = edge['node']
        url = node['url']
        slug = REGEX_WIKIDOT_URL.match(url)[2]

        # Scrape styling from page source
        wikidot_info = node['wikidotInfo']
        source = wikidot_info['source']

        if source is None:
            # This can happen sometimes, for some reason
            # It's obviously a problem, so let's just catch it here explicitly
            return None, slug

        module_styles = REGEX_MODULE_CSS.findall(source)
        inline_styles = REGEX_INLINE_CSS.findall(source)
        includes = REGEX_INCLUDES.findall(source)
        classes = Crawler.get_css_classes(source)

        # Build and page object
        page = {
            'url': url,
            'slug': slug,
            'title': wikidot_info['title'],
            'category': wikidot_info['category'],
            'wikidot_page_id': wikidot_info['wikidotId'],
            'source': source,
            'module_styles': module_styles,
            'inline_styles': inline_styles,
            'includes': includes,
            'classes': classes,
        }

        return page, slug

    @staticmethod
    def get_css_classes(source):
        # For each classes field, it splits along spaces to get each one separately.
        # It then uses itertools.chain() to effectively flatten this 'list of lists'.
        # We then explicitly remove any blank entries, and then cast to list.
        classes_lists = [classes[1].split(' ') for classes in REGEX_CLASSES.finditer(source)]

        return list(filter(None, itertools.chain(*classes_lists)))

    async def retry(self, coro):
        # Retry loop
        for _ in range(CROM_RETRIES):
            try:
                return await coro()
            except (KeyboardInterrupt, GeneratorExit, SystemExit):
                self.save()
                raise
                sys.exit(1)
            except:
                print("Error fetching pages from Crom:")
                print(traceback.format_exc())
                print()
            print("Making another attempt...")
        print("Giving up...")

    async def fetch_all(self):
        has_next_page = True
        last_slug = Container()
        last_page_count = 0

        async with aiohttp.ClientSession() as session:
            async def pull_pages():
                print(f"+ Requesting next batch of pages (last page '{last_slug.get()}')")

                # Make request
                edges, has_next_page = await self.next_pages(session)

                # Parse out results
                for edge in edges:
                    page, slug = self.process_edge(edge)
                    last_slug.set(slug)

                    if page is not None:
                        self.pages[slug] = page

            while has_next_page:
                await self.retry(pull_pages)

                # Save periodically
                # We don't save after every hit, unlike in the scraper,
                # because Crom is a lot faster and we don't want to thrash our disk.
                total_pages = len(self.pages)
                if total_pages - last_page_count >= 500:
                    self.save()
                    print(f"Now at {total_pages:,} saved pages")
                    last_page_count = total_pages

        return self.pages

if __name__ == '__main__':
    crawler = Crawler()

    if os.path.exists(OUTPUT_FILENAME):
        crawler.load()
        print("Loaded previous crawler state")
    else:
        print("No previous crawler state, starting fresh")

    asyncio.run(crawler.fetch_all())
