# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import djclick as click

from ...utils import discover


@click.command()
def command():
    discover.south()
