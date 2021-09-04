from functools import cached_property

import toml


class Config:
    def __init__(self, path):
        with open(path) as file:
            self.data = toml.load(file)

    @cached_property
    def save_page_offset(self):
        return int(self.data['save-page-offset'])

    @property
    def default_site(self):
        return self.data['sites'][0]

    @cached_property
    def crom_base_urls(self):
        return [f"http://{site}.wikidot.com/" for site in self.data['sites']]
