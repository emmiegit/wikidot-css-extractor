import os
import sys
from functools import cached_property

import tomllib

DEFAULT_CONFIG_PATH = "config.toml"


class Configuration:
    def __init__(self):
        if len(sys.argv) >= 2:
            path = sys.argv[1]
        else:
            path = DEFAULT_CONFIG_PATH

        with open(path, "rb") as file:
            self.data = tomllib.load(file)

    @cached_property
    def output_path(self):
        path = self.data["output-path"]
        if os.path.isabs(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            return path
        else:
            return os.path.join("output", path)

    @cached_property
    def save_page_offset(self):
        return int(self.data["save-page-offset"])

    @property
    def default_site(self):
        return self.data["sites"][0]

    @cached_property
    def crom_base_urls(self):
        return [f"http://{site}.wikidot.com/" for site in self.data["sites"]]
