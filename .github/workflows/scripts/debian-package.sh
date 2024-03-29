#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2023 Intevation GmbH
# SPDX-License-Identifier: AGPL-3.0-or-later
#

set -x
set -e

# install build dependencies
# gpg can't be a package dependency because of https://bugs.launchpad.net/ubuntu/+source/gpgme1.0/+bug/1977645
DEBIAN_FRONTEND="noninteractive" sudo -E apt-get update -qq
DEBIAN_FRONTEND="noninteractive" sudo -E apt-get install python3-gpg dpkg-dev lintian -y
DEBIAN_FRONTEND="noninteractive" sudo -E apt-get build-dep -y .

dpkg-buildpackage -us -uc -b
