Server side API of contactdb interface for intelmq-fody.

## Configuration
Uses environment variable ```CONTACTDB_SERVE_CONF_FILE``` to read
a configuration file, otherwise falls back to 
reading `/etc/intelmq/contactdb-serve.conf`.

Contents see
```sh
python3 -m contactdb_api --example-conf
```
There must be a database user which can write to contactdb.
If there is none yet, you can create one with something like:
```sh
createuser apiuser --pwprompt
psql -c "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO apiuser;" contactdb
psql -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO apiuser;" contactdb

```

### LogLevel DDEBUG

There is an additional loglevel `DDEBUG`
for more details than `DEBUG`.

## Run diagnostic mode main()

```sh
python3 -m contactdb_api
```

## Run tests

```sh
python3 -m unittest
```

## Installation
For a production setup `checkticket.py` has to be installed
with a webserver running `wsgi.multithread == False` and will try
to import the `contactdb\_api` module.
