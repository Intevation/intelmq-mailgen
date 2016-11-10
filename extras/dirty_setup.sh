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
# To user other than the build in configuration for intelmq 
# place the common configuration files for /opt/intelmq/etc
# in a directory named "ds-templates" in your CWD.
#
# The files in this directory can contain some key words of the form
# @keyword@, which will be substituted by this script.  Know key words
# are defined in TEMPLATE_VARS, they are replaced by the content of
# the global variables of the same name.

# -------------------------------------------------------------------
# Copyright (C) 2016 by Intevation GmbH
# Author(s):
# Bernhard Reiter <bernhard.reiter@intevation.de>
# Sascha Wilde <wilde@intevation.de>

# This program is free software under the GNU GPL (>=v2)
# Read the file COPYING coming with the software for details.

# Templating code derived from xen-make-guest
# Copyright (C) 2008-2016 by Intevation GmbH
# Author(s):
# Sascha Wilde <wilde@intevation.de>
# Thomas Arendsen Hein <thomas@intevation.de>
# -------------------------------------------------------------------

#
# certbund_contact setup
# MUST adhere to /usr/share/doc/intelmq/bots/experts/certbund_contact/README.md.gz
#

TEMPLATE_VARS="intelmqdbpasswd dbuser"
TEMPLATE_PATH="$PWD/ds-templates"

dbuser=intelmq
intelmqdbpasswd=`tr -dc A-Za-z0-9_ < /dev/urandom | head -c 14`

fill_in_template()
# $1 TEMPLATE_CONTENT
# return TEMPLATE_CONTENT with variables of the form @varname@ substituted.
{
  local template="$1"
  local substexp=""
  for var in $TEMPLATE_VARS ; do
    substexp="${substexp}s/@$var@/\${$var//\//\\\\/}/g;"
  done
  substexp="\"${substexp}\""
  local content=$( echo "$template" | eval sed $substexp )
  echo "$content"
}

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
  psql -c "GRANT eventdb_insert TO $dbuser" intelmq-events
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

declare -A default_templates

default_templates[startup.conf]=$( cat <<EOF
{
    "postgresql-output": {
        "group": "Output",
        "name": "PostgreSQL",
        "module": "intelmq.bots.outputs.postgresql.output"
    },
    "cert-bund-contact-database-expert": {
        "group": "Expert",
        "name": "CERT-bund Contact Database",
        "module": "intelmq.bots.experts.certbund_contact.expert"
   },
    "shadowserver-parser": {
        "group": "Parser",
        "name": "ShadowServer",
        "module": "intelmq.bots.parsers.shadowserver.parser"
    },
    "fileinput-collector": {
        "group": "Collector",
        "name": "Fileinput",
        "module": "intelmq.bots.collectors.file.collector_file"
    }
}
EOF
)

default_templates[runtime.conf]=$( cat <<EOF
{
    "postgresql-output": {
        "autocommit": true,
        "database": "intelmq-events",
        "host": "localhost",
        "password": "@intelmqdbpasswd@",
        "port": 5432,
        "sslmode": "require",
        "table": "events",
        "user": "@dbuser@"
    },
    "cert-bund-contact-database-expert": {
        "database": "contactdb",
        "host": "localhost",
        "password": "@intelmqdbpasswd@",
        "port": 5432,
        "sslmode": "require",
        "user": "@dbuser@"
    },
    "shadowserver-parser": {
        "feedname": "Botnet-Drone-Hadoop",
        "overwrite": true
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
EOF
)

default_templates[pipeline.conf]=$( cat <<EOF
{
    "fileinput-collector": {
        "destination-queues": [
            "shadowserver-parser-queue"
        ]
    },
    "shadowserver-parser": {
        "source-queue": "shadowserver-parser-queue",
        "destination-queues": [
            "cert-bund-contact-database-expert-queue"
        ]
    },
    "cert-bund-contact-database-expert": {
        "source-queue": "cert-bund-contact-database-expert-queue",
        "destination-queues": [
            "postgresql-output-queue"
        ]
    },
    "postgresql-output": {
        "source-queue": "postgresql-output-queue"
    }
}
EOF
)

default_templates[defaults.conf]=$( cat <<EOF
{
    "accuracy": 100,
    "broker": "redis",
    "destination_pipeline_db": 2,
    "destination_pipeline_host": "127.0.0.1",
    "destination_pipeline_port": 6379,
    "error_dump_message": true,
    "error_log_exception": true,
    "error_log_message": true,
    "error_max_retries": 3,
    "error_procedure": "pass",
    "error_retry_delay": 15,
    "http_proxy": null,
    "http_ssl_proxy": null,
    "http_user_agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
    "http_verify_cert": true,
    "load_balance": false,
    "logging_handler": "file",
    "logging_level": "INFO",
    "logging_path": "/opt/intelmq/var/log/",
    "logging_syslog": "/dev/log",
    "rate_limit": 0,
    "source_pipeline_db": 2,
    "source_pipeline_host": "127.0.0.1",
    "source_pipeline_port": 6379
}
EOF
)

for conf in ${!default_templates[@]} ; do
  if [ -e "$TEMPLATE_PATH/$conf" ] ; then
      template=$(< "$TEMPLATE_PATH/$conf")
  else
    template="${default_templates[$conf]}"
  fi
  export CONF_CONTENT=`fill_in_template "$template"`
  su intelmq -c "echo \"\$CONF_CONTENT\" >\"$etcdir/$conf\""
done

# necessary because of https://github.com/certtools/intelmq/issues/754

echo TODO: import contact database, e.g. follow the ripe import readme
echo TODO: as root: start dsmtp
echo TODO: as intelmq: copy shadowdsrv_botnet_droneTESTDATA.csv in /tmp/
