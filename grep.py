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
Match = namedtuple('Match', ('line_number', 'line_content', 'spans'))

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
        message = f"{Fore.RED}{message}{Style.RESET}"

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
            page_matches[slug] = matches

    return page_matches

# Printing results

def print_filename(slug):
    if USE_COLOR:
        print(f"{Fore.MAGENTA}{slug}{Fore.RESET}:", end='')
    else:
        print(f"{slug}:", end='')

def print_line_no(line_number):
    if USE_COLOR:
        print(f"{Fore.GREEN}{line_number}{Fore.RESET}:", end='')
    else:
        print(f"{line_number}:", end='')

def print_line_matches(match):
    if USE_COLOR:
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


def print_match_compact(slug, matches):
    for match in matches:
        print_filename(slug)
        print_line_no(match.line_number)
        print_line_matches(match)
        print()

def print_match_page(slug, matches):
    print_filename(slug)
    print()

    for match in matches:
        print_line_no(match.line_number)
        print_line_matches(match)
        print()

    print()

def print_grep_results(page_matches, compact):
    print_match = print_match_compact if compact else print_match_page

    for slug, matches in page_matches.items():
        print_match(slug, matches)

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
    print_grep_results(results, args.compact)
