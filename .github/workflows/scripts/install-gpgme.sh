#!/bin/bash

set -e

wget https://www.gnupg.org/ftp/gcrypt/gpgme/gpgme-${GPGME_VERSION}.tar.bz2
tar -xjf gpgme-${GPGME_VERSION}.tar.bz2
pushd gpgme-${GPGME_VERSION}
./autogen.sh
./configure --disable-silent-rules --disable-static --disable-fd-passing --disable-gpgconf-test --disable-gpg-test --disable-gpgsm-test --disable-g13-test --enable-languages="python"
make
sudo make install
# activate the gpgme python lib
#mv /usr/local/lib/python3.7/site-packages/*gpg* /opt/hostedtoolcache/Python/3.7.16/x64/lib/python3.7/site-packages/
