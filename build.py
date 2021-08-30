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
SCP_SLUG_REGEX = re.compile(r'^scp-([0-9]+)(.*)$')

COMPARISON_FUNCTIONS = {
    '>': lambda x, y: x > y,
    '<': lambda x, y: x < y,
    '>=': lambda x, y: x >= y,
    '<=': lambda x, y: x <= y,
    '==': lambda x, y: x == y,
    '!=': lambda x, y: x != y,
}

def get_include_url(include):
    match = INCLUDE_REGEX.match(include)
    if match is None:
        return None

    site, page = match.groups()
    if site is None:
        site = CURRENT_SITE

    return f"https://{site}.wikidot.com/{page}"


def build_html(pages, counts):
    # Build jinja environment and helpers
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader('templates'),
        autoescape=True,
    )
    env.globals['cmp'] = lambda x, operator, y: COMPARISON_FUNCTIONS[operator](x, y)
    env.globals['get_include_url'] = get_include_url
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

    for page in pages:
        slug = page['slug']

        print(f"Generating page for {slug}...")
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
    html_pages['includes'] = includes_template.render(includes=counts.includes)
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

def load_pages(path):
    def page_key(page):
        slug = page['slug']
        if slug.startswith('adult:'):
            # Fake page object
            return page_key({ 'slug': slug[6:] })

        match = SCP_SLUG_REGEX.match(slug)
        if match is None:
            return slug
        else:
            number = int(match[1])
            suffix = match[2]
            return f"scp-{number:07}{suffix}"

    with open(path) as file:
        data = json.load(file)

    pages = list(data['pages'].values())
    pages.sort(key=page_key)

    return pages

def deduplicate_items(pages):
    module_styles_count = defaultdict(int)
    inline_styles_count = defaultdict(int)
    classes_count = defaultdict(int)
    includes_count = defaultdict(int)

    for page in pages:
        for style in page['module_styles']:
            module_styles_count[style] += 1

        for style in page['inline_styles']:
            inline_styles_count[style] += 1

        for include in page['includes']:
            includes_count[include] += 1

        for klass in page['classes']:
            classes_count[klass] += 1

    def convert(counts):
        items = [(item, count) for item, count in counts.items()]
        items.sort(key=lambda item: item[1])
        items.reverse()
        return items

    module_styles = convert(module_styles_count)
    inline_styles = convert(inline_styles_count)
    includes = convert(includes_count)
    classes = convert(classes_count)

    # This is more complicated than convert(),
    # since we need to fold both by sites and then pages within them.
    site_includes_count = includes_by_site(includes_count)
    site_includes = ((site, convert(pages)) for site, pages in site_includes_count.items())
    site_includes = [(site, sum(count for _, count in pages), pages) for site, pages in site_includes]
    site_includes.sort(key=lambda item: item[1])
    site_includes.reverse()

    return CountedItems(
        module_styles=module_styles,
        inline_styles=inline_styles,
        includes=includes,
        site_includes=site_includes,
        classes=classes,
    )

def includes_by_site(includes_count):
    site_includes_count = defaultdict(lambda: defaultdict(int))

    for include, count in includes_count.items():
        match = INCLUDE_REGEX.match(include)
        if match is None:
            continue

        site, page = match.groups()
        if site is None:
            site = CURRENT_SITE

        site_includes_count[site][page] += 1

    return site_includes_count

if __name__ == '__main__':
    pages = load_pages(STYLES_FILENAME)
    counts = deduplicate_items(pages)
    generated_html = build_html(pages, counts)
    write_html(generated_html)
