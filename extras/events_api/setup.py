"""A minimal setupfile for eventdb_api."""

from setuptools import setup, find_packages

setup(
    name='intelmq-events-api',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='0.0.1.dev0',

    description='A hug based microservice api to intelmq.',

    packages=find_packages(),

    install_requires=['hug', 'psycopg2'],

)
