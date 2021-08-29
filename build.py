#!/usr/bin/env python3

import json
import os
from collections import defaultdict
from datetime import datetime

import jinja2

STYLES_FILENAME = 'output/extracted-styles.json'
OUTPUT_HTML = 'index.html'

def build_html(pages, styles):
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
            styles=page['styles'],
        )

    print("Generating index...")
    html_pages['index'] = index_template.render(pages=pages, styles=styles)
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
    # - or -
    # { slug: { error: string } }

    with open(path) as file:
        data = json.load(file)

    pages = [
        {
            'slug': slug,
            'title': value['pageTitle'],
            'source': value['pageSource'],
            'styles': value['styles'],
        }
        for slug, value in data.items()
        if value.get('error') is None
    ]
    pages.sort(key=page_key)

    return pages

def deduplicate_styles(pages):
    styles_count = defaultdict(int)
    for page in pages:
        for style in page['styles']:
            styles_count[style] += 1

    styles = []
    for style, count in styles_count.items():
        styles.append((style, count))

    styles.sort(key=lambda item: item[1])
    return styles

if __name__ == '__main__':
    pages = load_pages(STYLES_FILENAME)
    styles = deduplicate_styles(pages)
    generated_html = build_html(pages, styles)
    write_html(generated_html)
