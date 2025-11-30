# Copyright (c) Microsoft. All rights reserved.

"""Utility modules."""

from .prompts import *
from .search_client import get_search_client, search_legal_context

__all__ = [
    'get_search_client',
    'search_legal_context',
]
