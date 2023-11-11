#!/usr/bin/env python3

import json
import re
import sys
from argparse import ArgumentParser
from collections import namedtuple
from functools import partial

from colorama import Fore, Style

WIKIDOT_SITE_REGEX = re.compile(r"^https?://([^\.]+)\.wikidot\.com/.+")
USE_COLOR = None

RegexOptions = namedtuple('RegexOptions', ('invert', 'flags', 'sites'))
Match = namedtuple('Match', ('line_number', 'line_content', 'spans'))

# Always open files using UTF-8
open = partial(open, encoding='utf-8')

# Utility functions

def get_color_use(option):
    if option == 'always':
        return True
    elif option == 'never':
        return False
    else:
        return sys.stdout.isatty()

def get_regex_options(args):
    flags = re.MULTILINE

    if args.ignore_case:
        flags |= re.IGNORECASE

    if args.filter_sites:
        sites = args.filter_sites.split(",")
    else:
        sites = None

    return RegexOptions(
        invert=args.invert_match,
        flags=flags,
        sites=sites,
    )

def eprint(message):
    if USE_COLOR:
        message = f"{Fore.RED}{message}{Fore.RESET}"

    print(message, file=sys.stderr)

def load(path):
    with open(path) as file:
        data = json.load(file)

    return data['pages']

# Search

def grep(regex, pages, options):
    if options.invert:
        def line_matches(line):
            match = regex.search(line)
            return (0, 0) if match is None else ()
    else:
        def line_matches(line):
            return [match.span() for match in regex.finditer(line)]

    page_matches = {}

    for slug, page in pages.items():
        lines = page['source'].split('\n')
        site = WIKIDOT_SITE_REGEX.match(page['url'])[1]

        if options.sites:
            # Check site filter
            if site not in options.sites:
                continue

        matches = []
        for i, line in enumerate(lines):
            spans = line_matches(line)
            if spans:
                matches.append(Match(
                    line_number=i,
                    line_content=line,
                    spans=spans,
                ))

        if matches:
            page_matches[(site, slug)] = matches

    return page_matches

# Printing results

def print_filename(site, slug):
    if USE_COLOR:
        print(f"({Fore.BLUE}{site}{Fore.RESET}) {Fore.MAGENTA}{slug}{Fore.RESET}:", end='')
    else:
        print(f"({site}) {slug}:", end='')

def print_line_no(line_number):
    if USE_COLOR:
        print(f"{Fore.GREEN}{line_number}{Fore.RESET}:", end='')
    else:
        print(f"{line_number}:", end='')

def print_line_matches(match):
    if USE_COLOR:
        assert match.spans, "Spans list is empty"

        # Slice out matches
        index = 0
        for start, end in match.spans:
            message = ''.join((
                # Before
                match.line_content[index:start],

                # Match
                Fore.CYAN,
                Style.BRIGHT,
                match.line_content[start:end],
                Style.RESET_ALL,
            ))

            print(message, end='')

        # After
        print(match.line_content[end:], end='')
    else:
        print(match.line_content, end='')


def print_match_compact(site, slug, matches):
    for match in matches:
        print_filename(site, slug)
        print_line_no(match.line_number)
        print_line_matches(match)
        print()

def print_match_page(site, slug, matches):
    print_filename(site, slug)
    print()

    for match in matches:
        print_line_no(match.line_number)
        print_line_matches(match)
        print()

    print()

def print_grep_results(page_matches, compact):
    print_match = print_match_compact if compact else print_match_page

    for (site, slug), matches in page_matches.items():
        print_match(site, slug, matches)

if __name__ == '__main__':
    argparser = ArgumentParser(description="grep for wikidot sites")
    argparser.add_argument(
        "-F",
        "--fixed",
        "--fixed-string",
        action="store_true",
        default=False,
        dest="fixed_string",
        help="Search for a string literal rather than a regular expression",
    )
    argparser.add_argument(
        "-i",
        "--ignore-case",
        action="store_true",
        default=False,
        help="Whether to ignore case when searching",
    )
    argparser.add_argument(
        "-v",
        "--invert-match",
        action="store_true",
        default=False,
        help="Invert the sense of matching, selecting all lines which don't match",
    )
    argparser.add_argument(
        "--compact",
        action="store_true",
        default=False,
        help="Whether to display the results in compact / line mode",
    )
    argparser.add_argument(
        "--color",
        "--colour",
        default="auto",
        choices=["always", "never", "auto"],
        help="Whether to use colors to highlight results",
    )
    argparser.add_argument(
        "-S",
        "--site",
        default=None,
        dest="filter_sites",
        help="Only search from the following sites (comma-separated)",
    )
    argparser.add_argument(
        "pattern",
        help="The regular expression to search for",
    )
    argparser.add_argument(
        "path",
        nargs="?",
        default="output/results.json",
        help="The file containing page sources to look through",
    )
    args = argparser.parse_args()
    options = get_regex_options(args)
    USE_COLOR = get_color_use(args.color)

    try:
        pattern = args.pattern

        if args.fixed_string:
            pattern = re.escape(pattern)

        regex = re.compile(pattern, options.flags)
    except re.error as error:
        eprint(f"Invalid regular expression: {error}")
        sys.exit(1)

    try:
        pages = load(args.path)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        eprint(f"Unable to load page data: {error}")
        sys.exit(1)

    results = grep(regex, pages, options)
    #print_grep_results(results, args.compact)

    import os
    import requests
    URL_FILENAME_REGEX = re.compile(r"https:\/\/\w+\.discord\w*\.\w+\/(?:.+)\/([^\?]+).*?")
    base_directory = os.path.expanduser("~/incoming/cdndiscord")
    file_directory = os.path.join(base_directory, "files")
    os.makedirs(file_directory, exist_ok=True)

    def download_file(url, filename):
        print(f"Downloading {url} -> {filename}")
        dest = os.path.join(file_directory, filename)
        with open(dest, "wb", encoding=None) as file:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            file.write(r.content)

    def get_extension(url):
        match = URL_FILENAME_REGEX.fullmatch(url)
        if match is None:
            raise RuntimeError(url)
        _, ext = os.path.splitext(match[1])
        return ext

    counter = 0
    urls = {}
    for ((site, slug), matches) in results.items():
        directory = os.path.join(base_directory, site)
        os.makedirs(directory, exist_ok=True)

        page_path = os.path.join(directory, slug.replace(":", "$")) + ".txt"
        with open(page_path, "w") as file:
            for match in matches:
                for (start, end) in match.spans:
                    url = match.line_content[start:end].replace(" ", "%20")
                    ext = get_extension(url)

                    try:
                        filename = urls[url]
                    except KeyError:
                        filename = f"{counter:06}{ext}"
                        counter += 1
                        try:
                            download_file(url, filename)
                            urls[url] = filename
                        except requests.HTTPError:
                            filename = "<BROKEN>"

                    file.write(f"{url} {filename}\n")
