"""Setuptools setup file for intelmqmail.

Initially from https://github.com/pypa/sampleproject.
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='intelmqmail',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='0.99',

    description='A mail sending module for IntelMQ',
    long_description=long_description,

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
        'License :: OSI Approved :: GNU Affero General Public License v>=3.0',
        'License :: OSI Approved :: GNU Lesser General Public License v>=2.1',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    # What does your project relate to?
    keywords='intelmq mailer postgresql abuse-handling',

    packages=['intelmqmail'],

    install_requires=[
        'pygpgme>=0.3',
        'psycopg2',
        # Additional requirements:
        # * GnuPG (v>=2) for pygpgme
        # * pyxarf v>0.0.5 installed for python3
        #    https://github.com/xarf/python-xarf
        #    (v==0.0.5 does **not** work)
        #    version 2502a80ae9178a1ba0b76106c800d0e4b779d8da shall work
    ],

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
#    package_data={
#        'sample': ['package_data.dat'],
#    },

    entry_points={
        'console_scripts': [
            'intelmqcbmail = intelmqmail.cb:main',
        ],
    },
)
