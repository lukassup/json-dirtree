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
import hashlib
import json
import logging
import os
import shlex
import subprocess
import sys
try:
    from shutil import which
except ImportError:
    from distutils.spawn import find_executable as which


BASE_DIR = os.path.dirname(__file__)


class JSONDirTreeException(Exception):
    pass


class MissingExecutableError(JSONDirTreeException):
    pass


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


def run(command, stdin=None):
    """Execute a shell command and return the output and stderr)"""
    if getattr(subprocess.Popen, '__enter__', None) and getattr(subprocess.Popen, '__exit__', None):
        with subprocess.Popen(
                shlex.split(command),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True) as proc:
            try:
                out, err = proc.communicate(input=stdin, timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, err = proc.communicate()
            finally:
                rc = proc.returncode
    else:
        proc = subprocess.Popen(
                shlex.split(command),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True)
        try:
            out, err = proc.communicate(input=stdin)
        except Exception:
            proc.kill()
            out, err = proc.communicate()
        finally:
            rc = proc.returncode
    return rc, out, err


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


def get_openssl_prop(cert_path, prop_name):
    """Get a single certificate property by its name."""
    rc, out, _ = run('openssl x509 -noout -%s -in %s' % (prop_name, cert_path))
    success = rc == 0
    if not success:
        logging.warning('unable to get certificate %s for %s', prop_name, cert_path)
    key, _, value = out.partition('=')
    return success, key, value.rstrip()


def get_openssl_modulus_digest(cert_path, digest_type='sha256'):
    """Compute digest for OpenSSL certificate key modulus."""
    rc, out, _ = run('openssl x509 -noout -modulus -in %s' % cert_path)
    success = rc == 0
    if not success:
        logging.warning('unable to get certificate modulus for %s', cert_path)
        # raise error
    key, _, value = out.partition('=')
    hash_func = getattr(hashlib, digest_type)
    value = value.rstrip().encode()
    digest = hash_func(value).hexdigest()
    return success, digest


def is_cert_valid(cert_path):
    """Test if certificate is expired."""
    rc, out, _ = run('openssl x509 -noout -checkend 0 -in %s' % cert_path)
    valid = rc == 0
    return valid


def check_certificates(path, hidden=False, recursive=False,
                       props=('subject', 'issuer', 'startdate', 'enddate', 'serial')):
    """Check all certificates under a given path."""
    tree = {}
    for item in os.listdir(path):
        # handle files
        if hidden or not item.startswith('.'):
            fullpath = os.path.join(path, item)
            if os.path.isdir(fullpath) and recursive:
                # recurse into directories
                tree[item] = check_certificates(fullpath, hidden, recursive, props)
            elif os.path.isfile(fullpath):
                # handle certs
                tree[item] = {}
                for prop in props:
                    success, key, value = get_openssl_prop(fullpath, prop)
                    if not success:
                        break
                    tree[item][key] = value
                if not success:
                    tree.pop(item, None)
                    continue
                # modulus
                success, digest = get_openssl_modulus_digest(fullpath)
                tree[item]['modulusSHA256'] = digest
                # is_expired
                expired = not is_cert_valid(fullpath)
                tree[item]['expired'] = expired
        # NOTE: only files and directories are handled
    return tree


def find_expired_certs(path, hidden=False, recursive=False):
    tree = {}
    for item in os.listdir(path):
        # handle files
        if hidden or not item.startswith('.'):
            fullpath = os.path.join(path, item)
            if os.path.isdir(fullpath) and recursive:
                # recurse into directories
                tree[item] = find_expired_certs(fullpath, hidden, recursive)
            elif os.path.isfile(fullpath):
                # is_expired
                tree[item] = not is_cert_valid(fullpath)
        # NOTE: only files and directories are handled
    return tree


@cli.command('check')
@cli.option('-x', '--expired', help='find expired certs', action='store_true', default=False)
@cli.option('-a', '--hidden', help='search hidden files', action='store_true', default=False)
@cli.option('dirs', nargs='*', help='source directories (default: ./src/* )',
            default=glob.glob('src/*'))
def check_certs_command(dirs, hidden, expired):
    """Verifies TLS certificate validity in directories."""
    if not which('openssl'):
        raise MissingExecutableError("executable 'openssl' not found")
    cli.log.info('verifying TLS certificates in directories: %r', dirs)
    for d in dirs:
        if expired:
            tree = find_expired_certs(d, hidden, recursive=True)
        else:
            tree = check_certificates(d, hidden, recursive=True)
        print(json.dumps(tree, indent=2))


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
