#!/usr/bin/env python3
"""Lancador principal da assistente virtual Lucy."""

import sys
from lucy.cli import main

if __name__ == "__main__":
    sys.exit(main(default_lang="pt"))
