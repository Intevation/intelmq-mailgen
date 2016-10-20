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

# intelmq mailgen setup
echo TODO

# intelmq overall setup
echo TODO
