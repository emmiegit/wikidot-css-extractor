#!/usr/bin/env python3

from glob import iglob
import os
import shutil

if __name__ == "__main__":
    base_directory = os.path.expanduser("~/incoming/cdndiscord")
    for site in os.listdir(base_directory):
        if site == "files":
            continue

        print(f"Opening directory {site}")
        directory = os.path.join(base_directory, site)
        for path in iglob(os.path.join(directory, "*.txt")):
            print(f"Processing file {path}")
            with open(path) as file:
                lines = file.read().split("\n")

            for line in lines:
                if not line:
                    continue

                url, filename = line.split()
                if filename == "<BROKEN>":
                    print(f"File at {url} is broken")
                    continue

                source_path = os.path.join(base_directory, "files", filename)
                dest_path = os.path.join(directory, filename)
                if not os.path.isfile(dest_path):
                    print(f"Copying file {filename}")
                    shutil.copyfile(source_path, dest_path)
