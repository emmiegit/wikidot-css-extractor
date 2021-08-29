#!/usr/bin/env python3

import json
import os
from collections import defaultdict, namedtuple
from datetime import datetime

import jinja2

STYLES_FILENAME = 'output/results.json'
OUTPUT_HTML = 'index.html'

CountedItems = namedtuple('CountedItems', ('module_styles', 'inline_styles', 'classes'))

def build_html(pages, counts):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader('.'),
        autoescape=True,
    )
    env.globals['now'] = datetime.utcnow
    env.filters['commaify'] = lambda number: format(number, ',d')

    html_pages = {}

    page_template = env.get_template('page.j2')
    index_template = env.get_template('index.j2')

    for page in pages:
        slug = page['slug']

        print(f"Generating page for {slug}...")
        html_pages[slug] = page_template.render(
            slug=slug,
            title=page['title'],
            source=page['source'],
            module_styles=page['moduleStyles'],
            inline_styles=page['inlineStyles'],
            classes=page['classes'],
        )

    print("Generating index...")
    html_pages['index'] = index_template.render(
        pages=pages,
        module_styles=counts.module_styles,
        inline_styles=counts.inline_styles,
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
        if slug.startswith('scp-'):
            return slug[4:].zfill(4)
        else:
            return slug

    # Schema:
    # { slug: { pageSource: string, styles: string[] } }
    #  - or -
    # { slug: { error: string } }

    with open(path) as file:
        data = json.load(file)

    pages = [
        {
            'slug': slug,
            'title': value['pageTitle'],
            'source': value['pageSource'],
            'module_styles': value['moduleStyles'],
            'inline_styles': value['inlineStyles'],
            'classes': value['classes'],
        }
        for slug, value in data.items()
        if value.get('error') is None
    ]
    pages.sort(key=page_key)

    return pages

def deduplicate_items(pages):
    module_styles_count = defaultdict(int)
    inline_styles_count = defaultdict(int)
    classes_count = defaultdict(int)

    for page in pages:
        for style in page['moduleStyles']:
            module_styles_count[style] += 1

        for style in page['inlineStyles']:
            inline_styles_count[style] += 1

        for klass in page['classes']:
            classes_count[klass] += 1

    def convert(counts):
        items = [(item, count) for item, count in counts.items()]
        items.sort(key=lambda item: item[1])
        items.reverse()
        return items

    module_styles = convert(module_styles_count)
    inline_styles = convert(inline_styles_count)
    classes = convert(classes_count)

    return CountedItems(
        module_styles=module_styles,
        inline_styles=inline_styles,
        classes=classes,
    )

if __name__ == '__main__':
    pages = load_pages(STYLES_FILENAME)
    counts = deduplicate_items(pages)
    generated_html = build_html(pages, counts)
    write_html(generated_html)
