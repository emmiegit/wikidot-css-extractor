#!/usr/bin/env python3

import json
import re
import sys
from argparse import ArgumentParser

from colorama import Fore, Back, Style

SEARCH_FILENAME = 'output/results.json'
USE_COLOR = None

# Utility functions

def get_color_use(option):
    if option == 'always':
        return True
    elif option == 'never':
        return False
    else:
        return sys.stdout.isatty()

def eprint(message):
    if USE_COLOR:
        message = f"{Fore.RED}{message}{Style.RESET_ALL}"

    print(message, file=sys.stderr)

# Main functions

def grep(regex, pages):
    ...

def print_grep_results(results):
    ...

def load(path):
    with open(path) as file:
        data = json.load(file)

    return data['pages']

if __name__ == '__main__':
    argparser = ArgumentParser(description="grep for wikidot sites")
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
        default=SEARCH_FILENAME,
        help="The file containing page sources to look through",
    )
    args = argparser.parse_args()
    USE_COLOR = get_color_use(args.color)

    try:
        regex = re.compile(args.pattern)
    except re.error as error:
        eprint(f"Invalid regular expression: {error}")
        sys.exit(1)

    try:
        pages = load(args.path)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        eprint(f"Unable to load page data: {error}")
        sys.exit(1)

    results = grep(regex, pages)
    print_grep_results(results)
