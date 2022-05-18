import os
import sys
from functools import cached_property, partial

import toml

DEFAULT_CONFIG_PATH = "config.toml"

# Always open files using UTF-8
open = partial(open, encoding='utf-8')

class Configuration:
    def __init__(self):
        if len(sys.argv) >= 2:
            path = sys.argv[1]
        else:
            path = DEFAULT_CONFIG_PATH

        with open(path) as file:
            self.data = toml.load(file)

    @cached_property
    def output_path(self):
        return os.path.join('output', self.data['output-path'])

    @cached_property
    def save_page_offset(self):
        return int(self.data['save-page-offset'])

    @property
    def default_site(self):
        return self.data['sites'][0]

    @cached_property
    def crom_base_urls(self):
        return [f"http://{site}.wikidot.com/" for site in self.data['sites']]
