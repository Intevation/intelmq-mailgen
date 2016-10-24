# quick and dirty setup for a complete testing system
#
# WARNING use at your own risk!
#
# It is dirty because this script
# * just makes many assumptions
# * does not care for edge cases (or some defects)
# * is in danger of being out of sync with the authoritative docs for each bot
#
# call as root on an Ubuntu 14.04 LTS system which has recent 
# packages of intelmq-mailgen, intelmq-manager installed with
#  bash -x
#

#
# certbund_contact setup
# MUST adhere to /usr/share/doc/intelmq/bots/experts/certbund_contact/README.md.gz
#

dbuser=intelmq
intelmqdbpasswd=`tr -dc A-Za-z0-9_ < /dev/urandom | head -c 14`

sudo -u postgres bash -x << EOF
if psql -lqt | cut -d \| -f 1 | grep -qw contactdb; then
    echo "database already exists - no need for setup"
else
    createdb --encoding=UTF8 --template=template0 contactdb
    psql -f /usr/share/intelmq/certbund_contact/initdb.sql   contactdb
    psql -f /usr/share/intelmq/certbund_contact/defaults.sql contactdb

    psql -c "CREATE USER $dbuser WITH PASSWORD '$intelmqdbpasswd';"
    psql -c "GRANT SELECT ON ALL TABLES IN SCHEMA public TO $dbuser;" contactdb
fi
EOF

#
# bots/output/postgresql setup
# MUST adhere to /usr/share/doc/intelmq/bots/outputs/postgresql/README.md
#
INITDB_FILE=/tmp/initdb.sql

if [ ! -s "$INITDB_FILE" ] ; then
  intelmq_psql_initdb
fi

sudo -u postgres bash -x << EOF
  if psql -lqt | cut -d \| -f 1 | grep -qw intelmq-events; then
    echo "database already exists - no need for setup"
  else
    createdb --owner=$dbuser intelmq-events
    psql intelmq-events <"$INITDB_FILE"
  fi
EOF

#
# intelmq mailgen setup
# MUST adhere to /usr/share/doc/intelmq-mailgen/README.md.gz
#
maildbuser=intelmq_mailgen
maildbpasswd=`tr -dc A-Za-z0-9_ < /dev/urandom | head -c 14`

sudo -u postgres bash -x << EOF
  psql -c "CREATE USER $maildbuser WITH PASSWORD '$maildbpasswd';"
  psql -f /usr/share/intelmq-mailgen/sql/notifications.sql intelmq-events
  psql -c "GRANT eventdb_insert TO $maildbuser" intelmq-events  
  psql -c "GRANT eventdb_send_notifications TO $maildbuser" intelmq-events
EOF

cat /usr/share/doc/intelmq-mailgen/examples/intelmq-mailgen.conf.example | \
  sed -e "s/your DB password/$maildbpasswd/" \
      -e 's/"port": 25/"port": 8025/' \
  > /etc/intelmq/intelmq-mailgen.conf

ghome=/etc/intelmq/mailgen/gnupghome

mkdir "$ghome"
chown intelmq.intelmq "$ghome"
sudo -u intelmq bash -x <<EOF
  chmod og-rwx "$ghome"
  GNUPGHOME="$ghome" \
    gpg2 --import /usr/share/intelmq-mailgen/tests/keys/test1.sec

  cat - >"$ghome/gpg.conf" <<FOF
  personal-digest-preferences SHA256
  no-emit-version
  comment Key verification <https://example.org/hints-about-verification>
FOF
EOF

cp /usr/share/doc/intelmq-mailgen/examples/example-template.txt \
   /etc/intelmq/mailgen/templates/template-generic_malware.txt


# intelmq overall setup
etcdir=/opt/intelmq/etc

sudo -u intelmq bash -x <<EOF
cat - >$etcdir/startup.conf <<FOF
{
    "postgresql-output": {
        "group": "Output",
        "name": "PostgreSQL",
        "module": "intelmq.bots.outputs.postgresql.output"
    },
    "cert-bund-contact-database-expert": {
        "group": "Expert",
        "name": "CERT-bund Contact Database",
        "module": "intelmq.bots.experts.certbund_contact.expert",
   },
    "shadowserver-parser": {
        "group": "Parser",
        "name": "ShadowServer",
        "module": "intelmq.bots.parsers.shadowserver.parser",
    },
    "fileinput-collector": {
        "group": "Collector",
        "name": "Fileinput",
        "module": "intelmq.bots.collectors.file.collector_file",
    }
}
FOF

cat - >$etcdir/runtime.conf <<FOF
{
    "postgresql-output": {
        "autocommit": true,
        "database": "intelmq-events",
        "host": "localhost",
        "password": "$intelmqdbpasswd",
        "port": 5432,
        "sslmode": "require",
        "table": "events",
        "user": "$dbuser"
    },
    "cert-bund-contact-database-expert": {
        "database": "contactdb",
        "host": "localhost",
        "password": "$intelmqdbpasswd",
        "port": 5432,
        "sslmode": "require",
        "user": "$dbuser"
    },
    "shadowserver-parser": {
        "feedname": "Botnet-Drone-Hadoop",
        "override": true
    },
    "fileinput-collector": {
        "chunk_replicate_header": true,
        "chunk_size": null,
        "delete_file": true,
        "feed": "FileCollector",
        "path": "/tmp/",
        "postfix": ".csv",
        "rate_limit": 300
    }
}
FOF

cat - >$etcdir/pipeline.conf <<FOF
{
    "fileinput-collector": {
        "destination-queues": [
            "shadowserver-parser-queue"
        ]
    },
    "shadowserver-parser": {
        "source-queue": "shadowserver-parser-queue"
        "destination-queues": [
            "cert-bund-contact-database-expert-queue"
        ]
    },
    "cert-bund-contact-database-expert": {
        "source-queue": "cert-bund-contact-database-expert-queue"
        "destination-queues": [
            "postgresql-output-queue"
        ]
    },
    "postgresql-output": {
        "source-queue": "postgresql-output-queue"
    }
}
FOF

# necessary because of https://github.com/certtools/intelmq/issues/754
cat - >$etcdir/system.conf <<FOF
{
    "logging_level": "INFO",
    "logging_path": "/opt/intelmq/var/log/"
}
FOF
EOF

echo TODO: import contact database, e.g. follow the ripe import readme
echo TODO: as root: start dsmtp
echo TODO: as intelmq: copy shadowdsrv_botnet_droneTESTDATA.csv in /tmp/
