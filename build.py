#!/usr/bin/env python3

import json
import os

import jinja2

STYLES_FILENAME = 'output/extracted-styles.json'
OUTPUT_HTML = 'index.html'

def build_html(pages):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader('.'),
        autoescape=jinja2.select_autoescape(),
    )

    html_pages = {}

    page_template = env.get_template('page.j2')
    index_template = env.get_template('index.j2')

    for page in pages:
        if page['error'] is not None:
            slug = page['slug']
            html_pages[slug] = page_template.render(
                slug=slug,
                title=slug.upper(), # TODO: actually scrape this from pages
                page_source=page['source'],
                styles=page['styles'],
            )

    html_pages['index'] = index_template.render(pages=pages)
    return html_pages

def write_html(html_pages):
    os.makedirs('output', exist_ok=True)

    for name, html in html_pages.items():
        with open(f"output/{name}.html", 'w') as file:
            file.write(html)

def load_pages(path):
    # Schema:
    # { slug: { pageSource: string, styles: string[] } }
    # - or -
    # { slug: { error: string } }

    with open(path) as file:
        data = json.load(file)

    pages = [
        {
            'slug': slug,
            'source': value.get('pageSource'),
            'styles': value.get('styles'),
            'error': value.get('error'),
        }
        for slug, value in data.items()
    ]
    pages.sort(key=lambda page: page['slug'])

    return pages

if __name__ == '__main__':
    pages = load_pages(STYLES_FILENAME)
    generated_html = build_html(pages)
    write_html(generated_html)
