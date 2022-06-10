"""Setuptools setup file for intelmq-mailgen.
"""

# Always prefer setuptools over distutils
from setuptools import setup
# To use a consistent encoding
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name='intelmqmail',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='1.3.0',

    description='A mail sending module for IntelMQ',

    # The project's main homepage.
    url='https://github.com/intevation/intelmq-mailgen',

    # Author details
    author='Intevation GmbH',
    author_email='info@intevation.de',

    # Choose your license
    license='GNU Affero General Public License',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],

    # What does your project relate to?
    keywords='intelmq mailer postgresql abuse-handling',

    packages=['intelmqmail'],

    install_requires=[
        'psycopg2',
        'gpg >= 1.10',  # /!\ can (probably) **not** be installed via pip
        # Additional requirements:
        # * GnuPG (v>=2.2) for python3-gpg
        # * (optional) pyxarf v>0.0.5 for python3 installed
        #    https://github.com/xarf/python-xarf
        #    (v==0.0.5 does **not** work)
        #    version 2502a80ae9178a1ba0b76106c800d0e4b779d8da shall work
    ],

    entry_points={
        'console_scripts': [
            'intelmqcbmail = intelmqmail.cb:main',
        ],
    },
)
