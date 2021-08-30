#!/usr/bin/env python3

import hashlib
import json
import os
from collections import defaultdict, namedtuple
from datetime import datetime

import jinja2

CountedItems = namedtuple('CountedItems', ('module_styles', 'inline_styles', 'classes', 'includes'))

STYLES_FILENAME = 'output/results.json'
OUTPUT_HTML = 'index.html'

COMPARISON_FUNCTIONS = {
    '>': lambda x, y: x > y,
    '<': lambda x, y: x < y,
    '>=': lambda x, y: x >= y,
    '<=': lambda x, y: x <= y,
    '==': lambda x, y: x == y,
    '!=': lambda x, y: x != y,
}


def build_html(pages, counts):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader('templates'),
        autoescape=True,
    )
    env.globals['cmp'] = lambda x, operator, y: COMPARISON_FUNCTIONS[operator](x, y)
    env.globals['now'] = datetime.utcnow
    env.filters['commaify'] = lambda number: format(number, ',d')
    env.filters['reverse'] = reversed
    env.filters['sha1'] = lambda data: hashlib.sha1(data.encode('utf-8')).hexdigest()

    html_pages = {}

    page_template = env.get_template('page.j2')
    module_styles_template = env.get_template('module-css.j2')
    inline_styles_template = env.get_template('inline-css.j2')
    classes_template = env.get_template('classes.j2')
    index_template = env.get_template('index.j2')

    for page in pages:
        slug = page['slug']

        print(f"Generating page for {slug}...")
        html_pages[f'pages/{slug}'] = page_template.render(
            slug=slug,
            title=page['title'],
            source=page['source'],
            module_styles=page['module_styles'],
            inline_styles=page['inline_styles'],
            classes=page['classes'],
        )

    print("Generating detail pages...")
    html_pages['module-css'] = module_styles_template.render(styles=counts.module_styles)
    html_pages['inline-css'] = inline_styles_template.render(styles=counts.inline_styles)
    html_pages['includes'] = includes_template.render(includes=counts.includes)
    html_pages['classes'] = classes_template.render(classes=counts.classes)

    print("Generating index...")
    html_pages['index'] = index_template.render(
        pages=pages,
        module_styles=counts.module_styles,
        inline_styles=counts.inline_styles,
        includes=counts.includes,
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
            return slug[4:].zfill(10)
        else:
            return slug

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

    return CountedItems(
        module_styles=module_styles,
        inline_styles=inline_styles,
        includes=includes,
        classes=classes,
    )

if __name__ == '__main__':
    pages = load_pages(STYLES_FILENAME)
    counts = deduplicate_items(pages)
    generated_html = build_html(pages, counts)
    write_html(generated_html)
