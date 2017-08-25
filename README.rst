.. image:: https://travis-ci.org/lukassup/json-dirtree.svg?branch=master
    :target: https://travis-ci.org/lukassup/json-dirtree

json-dirtree
========

``json-dirtree`` converts file and directory hierarchy to a JSON object

.. _installation:

Installation
------------

Supported versions of Python are: 2.6, 2.7, 3.4, 3.5 and 3.6. The
recommended way to install this package is via `pip
<https://pypi.python.org/pypi/pip>`_.

.. code-block:: bash

    $ git clone https://github.com/lukassup/json-dirtree.git
    $ pip install ./json-dirtree

For instructions on installing python and pip see "The Hitchhiker's Guide to
Python" `Installation Guides
<http://docs.python-guide.org/en/latest/starting/installation/>`_.

Alternatively use ``easy_install``:

.. code-block:: bash

    $ git clone https://github.com/lukassup/json-dirtree.git
    $ easy_install ./json-dirtree

.. _usage:

Usage
-----


.. code-block::

    $ json-dirtree build --help
    usage: json-dirtree build [-h] [-v | -q] [-o DIR] [dirs [dirs ...]]

    Builds JSON output from directory and file tree.

    positional arguments:
    dirs                  source directories (default: ./src/* )

    optional arguments:
    -h, --help            show this help message and exit
    -v, --verbose         more verbose
    -q, --quiet           less verbose
    -o DIR, --out-dir DIR
                            output directory


.. _development:

Development
-----------

Install the ``json-dirtree`` package in editable mode using ``pip``:

.. code-block:: bash

    $ git clone https://github.com/lukassup/json-dirtree.git
    $ pip install -e ./json-dirtree

.. _testing:

Testing
-------

Run the tests:

.. code-block:: bash

    $ git clone https://github.com/lukassup/json-dirtree.git
    $ cd json-dirtree
    $ python2 setup.py test
    $ python3 setup.py test
