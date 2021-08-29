#!/usr/bin/env python3

import json
import re
import sys
from argparse import ArgumentParser
from collections import namedtuple

from colorama import Fore, Back, Style

SEARCH_FILENAME = 'output/results.json'
USE_COLOR = None

RegexOptions = namedtuple('RegexOptions', ('invert', 'flags'))
Match = namedtuple('Match', ('slug', 'line_number', 'line_content', 'span'))

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

    return RegexOptions(
        invert=args.invert_match,
        flags=flags,
    )

def eprint(message):
    if USE_COLOR:
        message = f"{Fore.RED}{message}{Style.RESET_ALL}"

    print(message, file=sys.stderr)

# Main functions

def grep(regex, pages, options):
    if options.invert:
        def line_matches(line):
            match = regex.search(line)
            return (0, 0) if match is None else None
    else:
        def line_matches(line):
            match = regex.search(line)
            return None if match is None else match.span()

    matches = []

    for slug, page in pages.items():
        lines = page['source'].split('\n')
        for i, line in enumerate(lines):
            span = line_matches(line)
            if span is not None:
                matches.append(Match(
                    slug=slug,
                    line_number=i,
                    line_content=line,
                    span=span,
                ))

    return matches

def print_grep_results(matches):
    # TODO
    print(matches)

def load(path):
    with open(path) as file:
        data = json.load(file)

    return data['pages']

if __name__ == '__main__':
    argparser = ArgumentParser(description="grep for wikidot sites")
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
        "--color",
        "--colour",
        default="auto",
        choices=["always", "never", "auto"],
        help="Whether to use colors to highlight results",
    )
    argparser.add_argument(
        "pattern",
        help="The regular expression to search for",
    )
    argparser.add_argument(
        "path",
        nargs="?",
        default=SEARCH_FILENAME,
        help="The file containing page sources to look through",
    )
    args = argparser.parse_args()
    options = get_regex_options(args)
    USE_COLOR = get_color_use(args.color)

    try:
        regex = re.compile(args.pattern, options.flags)
    except re.error as error:
        eprint(f"Invalid regular expression: {error}")
        sys.exit(1)

    try:
        pages = load(args.path)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        eprint(f"Unable to load page data: {error}")
        sys.exit(1)

    results = grep(regex, pages, options)
    print_grep_results(results)
