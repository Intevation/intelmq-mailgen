Server side API of contactdb interface for intelmq-fody.

## Configuration
Uses environment variable ```CONTACTDB_SERVE_CONF_FILE``` to read
a configuration file, otherwise falls back to reading
```/etc/intelmq/contactdb-serve.conf```.

Contents see
```sh
python3 -m contactdb_api --example-conf
```

## Run diagnostic mode main()

```sh
python3 -m contactdb_api
```

## Run tests

```sh
python3 -m unittest
```
