#!/usr/bin/env python
# coding: utf-8

# Copyright (c) Xiaojing Chen.
# Distributed under the terms of the Modified BSD License.

import re

__version__ = "0.1.11.dev"

def extract_version_info(ver: str) -> tuple:
    res = re.match(r'(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?P<channel>a|b|rc|.dev)?', ver)
    major = res.group('major')
    minor = res.group('minor')
    patch = res.group('patch')
    channel = res.group('channel')
    if channel:
        if channel == '.dev':
            return (major, minor, patch, 'dev')
        else:
            return (major, minor, patch, channel)
    else:
        return (major, minor, patch)

version_info = extract_version_info(__version__)