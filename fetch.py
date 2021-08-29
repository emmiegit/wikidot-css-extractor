#!/usr/bin/env python3

import asyncio
import json
import os
import re
import traceback

import aiohttp

OUTPUT_FILENAME = 'output/results.json'

REGEX_WIKIDOT_URL = re.compile(r'^https?://([\w\-]+)\.wikidot\.com/(.+)$')
REGEX_MODULE_CSS = re.compile(r'\[\[module +css\]\]\n(.+?)\n\[\[/module\]\]', re.IGNORECASE | re.DOTALL)
REGEX_INLINE_CSS = re.compile(r'style="(.+?)"[^\]]*?\]\]', re.MULTILINE | re.IGNORECASE)
REGEX_CLASSES = re.compile(r'class="([^\]]+?)"', re.MULTILINE | re.IGNORECASE)

CROM_ENDPOINT = "https://api.crom.avn.sh/"
CROM_SITES = ["http://scp-wiki.wikidot.com/"]
CROM_IGNORE_TAGS = ["redirect"]
CROM_RETRIES = 5
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
            notTag: $notTag,
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

    async def raw_request(self, session, query, variables):
        for key, value in variables.items():
            query = query.replace(key, json.dumps(value))

        payload = json.dumps({ 'query': query }).encode('utf-8')

        async with session.post(CROM_ENDPOINT, data=payload, headers=CROM_HEADERS) as r:
            json_body = await r.json()

            if 'errors' in json_body:
                raise CromError(json_body['errors'])

            return json_body['data']

    async def next_pages_direct(self, session):
        variables = {
            "$anyBaseUrl": CROM_SITES,
            "$notTag": CROM_IGNORE_TAGS,
            "$cursor": self.cursor,
        }

        json_body = await self.raw_request(session, CROM_QUERY, variables)
        pages = json_body['pages']
        page_info = pages['pageInfo']

        has_next_page = page_info['hasNextPage']
        self.cursor = page_info['endCursor']
        return pages['edges'], has_next_page

    async def next_pages(self, session):
        for _ in range(CROM_RETRIES):
            try:
                return await self.next_pages_direct(session)
            except:
                print("Error fetching pages from Crom:")
                print(traceback.format_exc())
                print()

            print("Making another attempt...")

        raise RuntimeError("Repeatedly failed to query Crom! Failing")

    @staticmethod
    def process_edge(edge):
        # Extract fields
        node = edge['node']
        url = node['url']
        slug = REGEX_WIKIDOT_URL.match(url)[2]

        # Scrape styling from page source
        wikidot_info = node['wikidotInfo']
        source = wikidot_info['source']

        module_styles = REGEX_MODULE_CSS.findall(source)
        inline_styles = REGEX_INLINE_CSS.findall(source)
        classes = REGEX_CLASSES.findall(source)

        # Return page object
        return {
            'url': url,
            'slug': slug,
            'title': wikidot_info['title'],
            'category': wikidot_info['category'],
            'wikidot_page_id': wikidot_info['wikidotId'],
            'source': source,
            'module_styles': module_styles,
            'inline_styles': inline_styles,
            'classes': classes,
        }

    async def fetch_all(self):
        has_next_page = True
        last_slug = None

        async with aiohttp.ClientSession() as session:
            while has_next_page:
                print(f"+ Requesting next batch of pages (last page '{last_slug}')")

                # Make request
                edges, has_next_page = await self.next_pages(session)

                # Parse out results
                for edge in edges:
                    self.pages[slug] = self.process_edge(edge)

                # Save progress
                self.save()
                last_slug = slug

        return self.pages

if __name__ == '__main__':
    crawler = Crawler()

    if os.path.exists(OUTPUT_FILENAME):
        crawler.load()
        print("Loaded previous crawler state")
    else:
        print("No previous crawler state, starting fresh")

    asyncio.run(crawler.fetch_all())
