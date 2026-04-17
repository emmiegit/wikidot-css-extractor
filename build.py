#!/usr/bin/env python3

import hashlib
import os
import re
import sqlite3
from contextlib import ExitStack
from collections import defaultdict, namedtuple
from datetime import datetime

import jinja2

from config import Configuration

CountedItems = namedtuple(
    "CountedItems",
    ("module_styles", "inline_styles", "classes", "includes", "site_includes"),
)

DEFAULT_SITE = None

INCLUDE_REGEX = re.compile(r"^(?::([a-z0-9\-]+):)?([a-z0-9\-:_]+)$", re.IGNORECASE)
SCP_SLUG_REGEX = re.compile(r"^scp-([0-9]+)(.*)$", re.IGNORECASE)

COMPARISON_FUNCTIONS = {
    ">": lambda x, y: x > y,
    "<": lambda x, y: x < y,
    ">=": lambda x, y: x >= y,
    "<=": lambda x, y: x <= y,
    "==": lambda x, y: x == y,
    "!=": lambda x, y: x != y,
}


def get_page_url(slug):
    return f"https://{DEFAULT_SITE}.wikidot.com/{slug}"


def get_include_url(include):
    match = INCLUDE_REGEX.match(include)
    if match is None:
        return None

    site, page = match.groups()
    if site is None:
        site = DEFAULT_SITE

    return f"https://{site}.wikidot.com/{page}"


def get_local_include_slug(include):
    match = INCLUDE_REGEX.match(include)
    if match is None:
        return None

    site, page = match.groups()
    if site != DEFAULT_SITE:
        return None

    return page


def get_extracts(page, extract_type):
    return (row["source"] for row in cur.execute(
        """
        SELECT source FROM extracts
        WHERE page_url = ?
        AND extract_type = ?
        ORDER BY extract_index
        """,
        (page["url"], extract_type),
    ))


class MultiList(list):
    """
    Like a multiset, but preserves insertion order.
    Assumes input data is sorted.

    Internally, a list where each element is [item, count].
    """

    def append(self, item):
        if self and self[-1][0] == item:
            self[-1][1] += 1
        else:
            super().append([item, 1])

    def extend(self, items):
        for item in items:
            self.append(item)


def build_html(cur, page_count, counts):
    # Build jinja environment and helpers
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader("templates"),
        autoescape=True,
    )
    env.globals["cmp"] = lambda x, operator, y: COMPARISON_FUNCTIONS[operator](x, y)
    env.globals["get_page_url"] = get_page_url
    env.globals["get_include_url"] = get_include_url
    env.globals["get_local_include_slug"] = get_local_include_slug
    env.globals["page_key"] = page_slug_key
    env.globals["now"] = datetime.utcnow
    env.filters["commaify"] = lambda number: format(number, ",d")
    env.filters["reverse"] = reversed
    env.filters["sha1"] = lambda data: hashlib.sha1(data.encode("utf-8")).hexdigest()

    # Get templates
    page_template = env.get_template("page.j2")
    module_styles_template = env.get_template("module-css.j2")
    inline_styles_template = env.get_template("inline-css.j2")
    includes_template = env.get_template("includes.j2")
    classes_template = env.get_template("classes.j2")
    page_index_template = env.get_template("page-index.j2")
    index_template = env.get_template("index.j2")

    # Build HTML
    html_pages = {}
    pages = cur.execute("SELECT * FROM pages ORDER BY slug")

    print(f"Generating {page_count} individual pages...")
    for page in pages:
        slug = page["slug"]

        html_pages[f"pages/{slug}"] = page_template.render(
            slug=slug,
            title=page["title"],
            source=page["source"],
            module_styles=list(get_extracts(page, "module_style")),
            inline_styles=list(get_extracts(page, "inline_style")),
            includes=list(get_extracts(page, "include")),
            classes=list(get_extracts(page, "class")),
        )

    print("Generating detail pages...")
    html_pages["module-css"] = module_styles_template.render(
        styles=counts.module_styles
    )
    html_pages["inline-css"] = inline_styles_template.render(
        styles=counts.inline_styles
    )
    html_pages["includes"] = includes_template.render(
        includes=counts.includes, site_includes=counts.site_includes
    )
    html_pages["classes"] = classes_template.render(classes=counts.classes)
    html_pages["pages/index"] = page_index_template.render(pages=pages)

    print("Generating index...")
    html_pages["index"] = index_template.render(
        pages=pages,
        module_styles=counts.module_styles,
        inline_styles=counts.inline_styles,
        includes=counts.includes,
        site_includes=counts.site_includes,
        classes=counts.classes,
    )

    return html_pages


def write_html(html_pages):
    os.makedirs("output", exist_ok=True)

    print("Writing files...")
    for name, html in html_pages.items():
        with open(f"output/{name}.html", "w", encoding="utf-8") as file:
            file.write(html)


def page_slug_key(slug):
    if slug.startswith("adult:"):
        return page_slug_key(slug[6:])

    match = SCP_SLUG_REGEX.match(slug)
    if match is None:
        return slug
    else:
        number = int(match[1])
        suffix = match[2]
        return f"scp-{number:07}{suffix}"


def deduplicate_items(cur, page_count):
    print("Processing data...")

    module_styles_count = defaultdict(MultiList)
    inline_styles_count = defaultdict(MultiList)
    classes_count = defaultdict(MultiList)
    includes_count = defaultdict(MultiList)

    pages = cur.execute("SELECT * FROM pages ORDER BY slug")
    for page in pages:
        slug = page["slug"]

        for style in get_extracts(page, "module_style"):
            module_styles_count[style].append(slug)

        for style in get_extracts(page, "inline_style"):
            inline_styles_count[style].append(slug)

        for include in get_extracts(page, "include"):
            includes_count[include].append(slug)

        for klass in get_extracts(page, "class"):
            classes_count[klass].append(slug)

    def convert(counts):
        items = [(item, pages, page_count) for item, pages in counts.items()]
        items.sort(key=lambda item: item[2])
        items.reverse()
        return items

    # This is more complicated than convert(),
    # since we need to fold both by sites and then pages within them.
    #
    # This uses an imperative loop rather than functional mappings
    # because they were getting really messy and hard to understand.

    def convert_site_includes():
        site_includes_count = includes_by_site(includes_count)
        entries = []

        for site, includes in site_includes_count.items():
            site_entries = []
            site_count = 0

            for include, pages in includes.items():
                include_entries = []
                include_count = 0

                for slug, count in pages:
                    include_count += count
                    include_entries.append((slug, count))

                include_entries.sort(key=lambda item: item[1])
                include_entries.reverse()

                site_count += include_count
                site_entries.append((include, include_entries, include_count))

            site_entries.sort(key=lambda item: item[2])
            site_entries.reverse()

            entries.append((site, site_entries, site_count))

        entries.sort(key=lambda item: item[2])
        entries.reverse()
        return entries

    module_styles = convert(module_styles_count)
    inline_styles = convert(inline_styles_count)
    includes = convert(includes_count)
    site_includes = convert_site_includes()
    classes = convert(classes_count)

    return CountedItems(
        module_styles=module_styles,
        inline_styles=inline_styles,
        includes=includes,
        site_includes=site_includes,
        classes=classes,
    )


def includes_by_site(includes_count):
    site_includes_count = defaultdict(lambda: defaultdict(list))

    for include, slugs in includes_count.items():
        match = INCLUDE_REGEX.match(include)
        if match is None:
            continue

        site, page = match.groups()
        if site is None:
            site = DEFAULT_SITE

        site_includes_count[site][include].extend(slugs)

    return site_includes_count


def set_current_site(config):
    global DEFAULT_SITE

    DEFAULT_SITE = config.default_site


if __name__ == "__main__":
    config = Configuration()
    set_current_site(config)
    conn = sqlite3.connect(config.output_path)
    conn.row_factory = sqlite3.Row
    with conn as cur:
        (page_count,) = cur.execute("SELECT COUNT(*) FROM pages").fetchone()
        counts = deduplicate_items(cur, page_count)
        generated_html = build_html(cur, page_count, counts)
    write_html(generated_html)
