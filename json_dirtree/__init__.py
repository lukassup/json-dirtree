#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Convert file and directory hierarchy to a JSON object."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals
)

import argparse
import glob
import json
import logging
import os
import sys


BASE_DIR = os.path.dirname(__file__)


class CLI(object):

    """A really basic version of the famous Python Click library."""

    log = logging.getLogger(__name__)
    common_args = argparse.ArgumentParser(add_help=False)
    log_group = common_args.add_mutually_exclusive_group()
    log_group.add_argument(
        '-v',
        '--verbose',
        dest='verbosity',
        default=[logging.INFO],
        action='append_const',
        const=-10,
        help='more verbose',
    )
    log_group.add_argument(
        '-q',
        '--quiet',
        dest='verbosity',
        action='append_const',
        const=10,
        help='less verbose',
    )

    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.subparsers = self.parser.add_subparsers(help='subcommands',
                                                     dest='command')
        self.subparsers.required = True

    def command(self, name, *args, **kwargs):
        """Register a function to the command-line interface."""
        def wrapper(f):
            f.parser = self.subparsers.add_parser(
                    name, *args, description=f.__doc__,
                    parents=[self.common_args], **kwargs)
            if getattr(f, 'cli_args', None) is not None:
                for fargs, fkwargs in f.cli_args:
                    f.parser.add_argument(*fargs, **fkwargs)
            f.parser.set_defaults(action=f)
            return f
        return wrapper

    def option(self, *args, **kwargs):
        """Register CLI arguments for function.

        Accepts the same arguments as ArgumentParser().add_argument(...)
        """
        def wrapper(f):
            if getattr(f, 'cli_args', None) is None:
                f.cli_args = []
            f.cli_args.append((args, kwargs))
            return f
        return wrapper

    def run(self):
        """Parse arguments and run the default action."""
        args = self.parser.parse_args()
        # init logging
        log_level = max(logging.DEBUG, min(logging.CRITICAL, sum(args.verbosity)))
        debug_on = log_level <= logging.DEBUG
        logging.basicConfig(level=log_level)
        kwargs = dict(vars(args))
        # sanitize excess arguments, obiously there are better ways!
        kwargs.pop('action', None)
        kwargs.pop('command', None)
        kwargs.pop('verbosity', None)
        try:
            # callback action
            args.action(**kwargs)
        except Exception as e:
            self.log.error(e, exc_info=debug_on)
            sys.exit(1)
        sys.exit(0)


cli = CLI()


def dirtree(path, hidden=False, readfiles=False, recursive=False):
    """Build file and directory structure into a dictionary."""
    tree = {}
    for item in os.listdir(path):
        # handle hidden files
        if hidden or not item.startswith('.'):
            fullpath = os.path.join(path, item)
            if os.path.isdir(fullpath):
                # handle directories
                if recursive:
                    # recurse into directories
                    tree[item] = dirtree(fullpath, hidden, readfiles, recursive)
                else:
                    tree[item] = {}
            elif os.path.isfile(fullpath):
                # handle files
                if readfiles:
                    # read file contents
                    with open(fullpath) as fr:
                        tree[item] = fr.read()
                else:
                    tree[item] = ''
            else:
                # NOTE: only files and directories are handled
                pass
    return tree


@cli.command('build')
@cli.option('dirs', nargs='*', help='source directories (default: ./src/* )',
            default=glob.glob('src/*'))
@cli.option('-o', '--out-dir', metavar='DIR', help='output directory', default='.')
def build_command(dirs, out_dir):
    """Builds JSON output from directory and file tree."""
    cli.log.info('building JSON tree for dirs: %r', dirs)
    count = 0
    for dir_ in dirs:
        base = os.path.basename(dir_)
        tree = dirtree(dir_, hidden=False, readfiles=True, recursive=True)
        file_name = '{0}.json'.format(base)
        dest_path = os.path.join(out_dir, file_name)
        with open(dest_path, 'w') as fr:
            cli.log.info('writing JSON output to: %r', dest_path)
            json.dump(tree, fr, indent=2)
        count += 1
    cli.log.info('done, %d files written', count)


if __name__ == '__main__':
    cli.run()
