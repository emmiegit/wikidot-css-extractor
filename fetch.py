#!/usr/bin/env python3

import asyncio
import itertools
import json
import os
import re
import sqlite3
import sys
import time
import traceback
from functools import partial

import aiohttp
from dateutil.parser import isoparse

from config import Configuration

REGEX_CROM_RATE_LIMIT = re.compile(r"(?:in|for) (\d+) seconds?")
REGEX_WIKIDOT_URL = re.compile(r'^https?://([\w\-]+)\.wikidot\.com/(.+)$')
REGEX_MODULE_CSS = re.compile(r'\[\[module +css\]\]\n(.+?)\n\[\[/module\]\]', re.IGNORECASE | re.DOTALL)
REGEX_INLINE_CSS = re.compile(r'style="(.+?)"[^\]]*?\]\]', re.MULTILINE | re.IGNORECASE)
REGEX_INCLUDES = re.compile(r'\[\[include +([a-z0-9:\-_]+?)(?: |\]\])', re.MULTILINE | re.IGNORECASE)
REGEX_CLASSES = re.compile(r'class="([^\]]+?)"', re.MULTILINE | re.IGNORECASE)

CROM_ENDPOINT = "https://api.crom.avn.sh/graphql"
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
            wikidotInfo: {
                createdAt: {
                    gte: $lastCreatedAt,
                },
            },
        },
        sort: {
            order: ASC,
            key: CREATED_AT,
        },
        first: 100,
        after: $cursor,
    ) {
        edges {
            node {
                url,
                wikidotInfo {
                    title,
                    category,
                    createdAt,
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

SQLITE_SEED_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

with open(SQLITE_SEED_PATH) as file:
    SQLITE_SEED = file.read()


def format_date(iso_date):
    if iso_date is None:
        return 'None'

    date = isoparse(iso_date)
    return f"{date.year}/{date.month}/{date.day}"

# Always open files using UTF-8
open = partial(open, encoding='utf-8')

class Container:
    __slots__ = ("value",)

    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

class CromError(RuntimeError):
    def __init__(self, errors):
        super().__init__(self._get_message(errors))
        self.errors = errors
        self.ratelimit = self._get_ratelimit()

    @staticmethod
    def _get_message(errors):
        if len(errors) == 1:
            return errors[0]
        else:
            return errors

    def _get_ratelimit(self):
        for error in self.errors:
            match = REGEX_CROM_RATE_LIMIT.search(error["message"])
            if match is not None:
                return int(match[1])

        return None

class Crawler:
    def __init__(self, config):
        self.config = config
        self.path = config.output_path
        self.connect()

    def connect(self):
        database_exists = os.path.exists(config.output_path)
        self.conn = sqlite3.connect(self.path)
        if database_exists:
            print("Loaded previous crawler state")

            with self.conn as cur:
                result = cur.execute("SELECT cursor_state, last_created_at FROM crawler_state")
                self.cursor, self.last_created_at = result.fetchone()
        else:
            print("No previous crawler state, starting fresh")

            with self.conn as cur:
                cur.executescript(SQLITE_SEED)

            self.cursor = None
            self.last_created_at = None

    def close(self):
        with self.conn as cur:
            cur.execute("DELETE FROM crawler_state")
            cur.execute(
                """
                INSERT INTO crawler_state
                (cursor_state, last_created_at)
                VALUES
                (?, ?)
                """,
                (self.cursor, self.last_created_at),
            )

        self.conn.close()
        self.conn = None

    def write_page(self, page):
        with self.conn as cur:
            cur.execute(
                """
                INSERT INTO pages
                (url, slug, title, category, created_at, wikidot_page_id, source)
                VALUES
                (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (url)
                DO UPDATE
                SET
                    slug = ?,
                    title = ?,
                    category = ?,
                    created_at = ?,
                    wikidot_page_id = ?,
                    source = ?
                """,
                (
                    page['url'],
                    page['slug'],
                    page['title'],
                    page['category'],
                    page['created_at'],
                    page['wikidot_page_id'],
                    page['source'],
                    page['slug'],
                    page['title'],
                    page['category'],
                    page['created_at'],
                    page['wikidot_page_id'],
                    page['source'],
                ),
            )

            cur.execute("DELETE FROM extracts WHERE page_url = ?", (page['url'],))

            def add_extracts(extract_type, extracts):
                for idx, extract in enumerate(extracts):
                    cur.execute(
                        """
                        INSERT INTO extracts
                        (page_url, extract_index, extract_type, source)
                        VALUES
                        (?, ?, ?, ?)
                        """,
                        (
                            page['url'],
                            idx,
                            extract_type,
                            extract,
                        ),
                    )

            add_extracts("module_style", page["module_styles"])
            add_extracts("inline_style", page["inline_styles"])
            add_extracts("include", page["includes"])
            add_extracts("class", page["classes"])

    async def raw_request(self, session, query, variables):
        for key, value in variables.items():
            query = query.replace(key, json.dumps(value))

        payload = json.dumps({ 'query': query }).encode('utf-8')

        try:
            async with session.post(CROM_ENDPOINT, data=payload, headers=CROM_HEADERS) as r:
                json_body = await r.json()

                if 'errors' in json_body:
                    raise CromError(json_body['errors'])

                return json_body['data']
        except CromError as error:
            if error.ratelimit is None:
                raise error

            # Otherwise, try again
            print(f"Ratelimited, trying again after {error.ratelimit} seconds")
            time.sleep(error.ratelimit)
            return await self.raw_request(session, query, variables)

    async def next_pages(self, session):
        variables = {
            "$anyBaseUrl": self.config.crom_base_urls,
            "$lastCreatedAt": self.last_created_at,
            "$cursor": self.cursor,
        }

        json_body = await self.raw_request(session, CROM_QUERY, variables)
        pages = json_body['pages']
        page_info = pages['pageInfo']

        has_next_page = page_info['hasNextPage']
        if has_next_page:
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
            'created_at': wikidot_info['createdAt'],
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

        async with aiohttp.ClientSession() as session:
            async def pull_pages():
                created_at = format_date(self.last_created_at)
                print(f"+ Requesting next batch of pages (last page '{last_slug}', created {created_at})")

                # Make request
                edges, has_next_page = await self.next_pages(session)

                # Parse out results
                for edge in edges:
                    page, slug = self.process_edge(edge)
                    last_slug.set(slug)

                    if page is not None:
                        self.last_created_at = page['created_at']
                        self.write_page(page)

                return has_next_page

            while has_next_page:
                has_next_page = await self.retry(pull_pages)

            print("Hit the end, finished!")

if __name__ == '__main__':
    config = Configuration()
    crawler = Crawler(config)
    asyncio.run(crawler.fetch_all())
