First test key material created with 

Package: gnupg2
Architecture: i386
Version: 2.0.25-99intevation2

libgcrypt 1.5.3

test1.intelmq@example.org
--------------------------

```
LANG=C GNUPGHOME=~/tmp/dot.gnupg gpg2 --full-gen-key
RSA (sign only)
Requested keysize is 4096 bits
Key does not expire at all
Real name: Test1 IntelMQ
Email address: test1.intelmq@example.org
Comment: no passphrase
```

```
LANG=C GNUPGHOME=~/tmp/dot.gnupg gpg2 --export-secret-key test1 >test1.gpg
LANG=C GNUPGHOME=~/tmp/dot.gnupg gpg2 --armor --export test1 >test1.pub
```
