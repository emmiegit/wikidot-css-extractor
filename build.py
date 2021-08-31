#!/usr/bin/env python3

import hashlib
import json
import os
import re
from collections import defaultdict, namedtuple
from datetime import datetime

import jinja2

CountedItems = namedtuple('CountedItems', ('module_styles', 'inline_styles', 'classes', 'includes', 'site_includes'))

STYLES_FILENAME = 'output/results.json'
OUTPUT_HTML = 'index.html'
CURRENT_SITE = 'scp-wiki'

INCLUDE_REGEX = re.compile(r'^(?::([a-z0-9\-]+):)?([a-z0-9\-:_]+)$', re.IGNORECASE)
SCP_SLUG_REGEX = re.compile(r'^scp-([0-9]+)(.*)$', re.IGNORECASE)

COMPARISON_FUNCTIONS = {
    '>': lambda x, y: x > y,
    '<': lambda x, y: x < y,
    '>=': lambda x, y: x >= y,
    '<=': lambda x, y: x <= y,
    '==': lambda x, y: x == y,
    '!=': lambda x, y: x != y,
}

def get_page_url(slug):
    return f"https://{CURRENT_SITE}.wikidot.com/{slug}"

def get_include_url(include):
    match = INCLUDE_REGEX.match(include)
    if match is None:
        return None

    site, page = match.groups()
    if site is None:
        site = CURRENT_SITE

    return f"https://{site}.wikidot.com/{page}"

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

def build_html(pages, counts):
    # Build jinja environment and helpers
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader('templates'),
        autoescape=True,
    )
    env.globals['cmp'] = lambda x, operator, y: COMPARISON_FUNCTIONS[operator](x, y)
    env.globals['get_page_url'] = get_page_url
    env.globals['get_include_url'] = get_include_url
    env.globals['page_key'] = page_slug_key
    env.globals['now'] = datetime.utcnow
    env.filters['commaify'] = lambda number: format(number, ',d')
    env.filters['reverse'] = reversed
    env.filters['sha1'] = lambda data: hashlib.sha1(data.encode('utf-8')).hexdigest()

    # Get templates
    page_template = env.get_template('page.j2')
    module_styles_template = env.get_template('module-css.j2')
    inline_styles_template = env.get_template('inline-css.j2')
    includes_template = env.get_template('includes.j2')
    classes_template = env.get_template('classes.j2')
    page_index_template = env.get_template('page-index.j2')
    index_template = env.get_template('index.j2')

    # Build HTML
    html_pages = {}

    print(f"Generating {len(pages)} individual pages...")
    for page in pages:
        slug = page['slug']

        html_pages[f'pages/{slug}'] = page_template.render(
            slug=slug,
            title=page['title'],
            source=page['source'],
            module_styles=page['module_styles'],
            inline_styles=page['inline_styles'],
            includes=page['includes'],
            classes=page['classes'],
        )

    print("Generating detail pages...")
    html_pages['module-css'] = module_styles_template.render(styles=counts.module_styles)
    html_pages['inline-css'] = inline_styles_template.render(styles=counts.inline_styles)
    html_pages['includes'] = includes_template.render(includes=counts.includes, site_includes=counts.site_includes)
    html_pages['classes'] = classes_template.render(classes=counts.classes)
    html_pages['pages/index'] = page_index_template.render(pages=pages)

    print("Generating index...")
    html_pages['index'] = index_template.render(
        pages=pages,
        module_styles=counts.module_styles,
        inline_styles=counts.inline_styles,
        includes=counts.includes,
        site_includes=counts.site_includes,
        classes=counts.classes,
    )

    return html_pages

def write_html(html_pages):
    os.makedirs('output', exist_ok=True)

    print("Writing files...")
    for name, html in html_pages.items():
        with open(f"output/{name}.html", 'w') as file:
            file.write(html)

def page_slug_key(slug):
    if slug.startswith('adult:'):
        return page_slug_key(slug[6:])

    match = SCP_SLUG_REGEX.match(slug)
    if match is None:
        return slug
    else:
        number = int(match[1])
        suffix = match[2]
        return f"scp-{number:07}{suffix}"

def load_pages(path):
    with open(path) as file:
        data = json.load(file)

    pages = list(data['pages'].values())
    pages.sort(key=lambda page: page_slug_key(page['slug']))

    return pages

def deduplicate_items(pages):
    print("Processing data...")

    module_styles_count = defaultdict(MultiList)
    inline_styles_count = defaultdict(MultiList)
    classes_count = defaultdict(MultiList)
    includes_count = defaultdict(MultiList)

    for page in pages:
        slug = page['slug']

        for style in page['module_styles']:
            module_styles_count[style].append(slug)

        for style in page['inline_styles']:
            inline_styles_count[style].append(slug)

        for include in page['includes']:
            includes_count[include].append(slug)

        for klass in page['classes']:
            classes_count[klass].append(slug)

    def convert(counts):
        items = [(item, pages, len(pages)) for item, pages in counts.items()]
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

                site_count += count
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
            site = CURRENT_SITE

        site_includes_count[site][include].extend(slugs)

    return site_includes_count

if __name__ == '__main__':
    pages = load_pages(STYLES_FILENAME)
    counts = deduplicate_items(pages)
    generated_html = build_html(pages, counts)
    write_html(generated_html)
