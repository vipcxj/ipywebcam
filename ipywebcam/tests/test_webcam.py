#!/usr/bin/env python
# coding: utf-8

# Copyright (c) Xiaojing Chen.
# Distributed under the terms of the Modified BSD License.

import pytest

from ..webcam import WebCamWidget


def test_example_creation_blank():
    w = WebCamWidget()
    assert w.value == 'Hello World'
