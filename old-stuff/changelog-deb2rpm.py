#!/usr/bin/python3
# -*- coding: utf-8 -*-
from __future__ import print_function

import sys
import os
import re
import warnings
import datetime
import textwrap

from pathlib import Path
from debian.changelog import Changelog


if len(sys.argv) < 2:
    print("No Changelog file given.", file=sys.stderr)
    sys.exit(1)

if len(sys.argv) > 2:
    print("Too many arguments given.", file=sys.stderr)
    sys.exit(1)

filename = sys.argv[1]

changelog_file = Path(filename)

if not changelog_file.exists():
    print("File {!r} does not exists.".format(filename), file=sys.stderr)
    sys.exit(1)

if not changelog_file.is_file():
    print("File {!r} is not a regular file.".format(filename), file=sys.stderr)
    sys.exit(1)

# print("Lese {!r} ...".format(filename), file=sys.stderr)

ch = None

re_emptyline = re.compile(r'^\s*$')
re_start_line = re.compile(r'^  \* (.*)')
re_next_line = re.compile(r'^    (.*)')

def mangle_changes(changes):

    clist = []
    change = None

    for line in changes:

        if re_emptyline.match(line):
            continue

        m = re_start_line.match(line)
        if m:
            if change:
                clist.append(change)
            change = m.group(1)
            continue

        m = re_next_line.match(line)
        if m:
            if change:
                change += ' ' + m.group(1)
            else:
                change = m.group(1)
            continue

        warnings.warn("Could not evaluate Changelog entry {!r}.".format(line), SyntaxWarning)

    if change:
        clist.append(change)

    return clist

with changelog_file.open('r', encoding='utf-8', errors='backslashreplace') as fh:

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        ch = Changelog(fh)

        if len(w):
            print("There were {nr} warnings on reading {f!r}.".format(nr=len(w), f=filename),
                    file=sys.stderr)
            sys.exit(5)

    # print("Changelog {f!r} hat {nr} Einträge.".format(f=filename, nr=len(ch)), file=sys.stderr)

    days = {}

    for block in ch:

        lines = []
        day_str = re.sub(r'\s+\d\d:\d\d:\d\d\s+[+-]?\d{4}$', '', block.date)
        date = datetime.datetime.strptime(day_str, '%a, %d %b %Y')

        day = date.strftime('%Y-%m-%d')
        author = block.author
        version = str(block.version) + '-1'
        lines.append('*   {date} {author} {version}'.format(
            date=date, author=author, version=version))

        changes = mangle_changes(block._changes)

        if day not in days:
            days[day] = {
                    'date': date.strftime('%a %b %d %Y'),
                    'author': author,
                    'version': version,
                    'changes': changes,
            }
        else:
            for change in changes:
                days[day]['changes'].append(change)

    for day in reversed(sorted(days.keys())):
        lines = []
        block = days[day]
        lines.append('*   {date} {author} {version}'.format(
            date=block['date'], author=block['author'], version=block['version']))

        for change in block['changes']:
            for line in textwrap.wrap(
                    change, width=70, initial_indent="-   ", subsequent_indent="    "):
                lines.append(line)

        print('\n'.join(lines))

