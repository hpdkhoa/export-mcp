"""Email parsers. Each has matches(sender, lines) and parse(lines) -> {"row": [...], "when": sortable time}.

To add a merchant, write a module like shopee.py and list it here.
"""
from . import shopee

PARSERS = [shopee]
