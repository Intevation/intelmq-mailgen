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
If there is none yet, you can create one with something likes
```sh
createuser apiuser --pwprompt
psql -c "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO apiuser;" contactdb
psql -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO apiuser;" contactdb

```

## Run diagnostic mode main()

```sh
python3 -m contactdb_api
```

## Run tests

```sh
python3 -m unittest
```
