#!/usr/bin/env python3

import json

import jinja2

STYLES_FILENAME = 'extracted-styles.json'
OUTPUT_HTML = 'index.html'

def build_html(pages):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader('.'),
        autoescape=jinja2.select_autoescape(),
    )

    template = env.get_template('page')
    return template.render(pages=pages)

def load_pages(path):
    # Schema:
    # { slug: { pageSource: string, styles: string[] } }

    with open(path) as file:
        data = json.load(path)

    return [
        {
            'slug': slug,
            'source': value['pageSource'],
            'styles': value['styles'],
        }
        for slug, value in data.items()
    ]

if __name__ == '__main__':
    pages = load_pages(STYLES_FILENAME)
    html = build_html(pages)

    with open(OUTPUT_HTML, 'w') as file:
        file.write(html)
