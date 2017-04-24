# Introduction

"rnp" is a set of OpenPGP (RFC4880) tools that works on Linux, \*BSD and
macOS as a replacement of GnuPG. It is maintained by Ribose after being
forked from NetPGP, itself originally written for NetBSD.

"librnp" is the library used by rnp for all OpenPGP functions, useful
for developers to build against. Thanks to Allistair, it is a "real"
library, not a wrapper like GPGME of GnuPG.

NetPGP was originally written (and still maintained) by Allistair Crooks
of NetBSD.


# Usage


## Generating an RSA Private Key

Only RSA key supported right now.

``` sh
export keydir=/tmp
rnpkeys --generate-key --homedir=${keydir}
```

=>

``` sh
rnpkeys: generated keys in directory ${keydir}/6ed2d908150b82e7
```

In case you're curious, `6ed2d...` is the key fingerprint.


## Listing Keys

``` sh
export keyringdir=${keydir}/MYFINGERPRINT
rnpkeys --list-keys --homedir=${keyringdir}

```

=>

```
1 key found
...
```


## Signing a File


### Signing in binary format

``` sh
rnp --sign --homedir=${keyringdir} ${filename}
```

=>

Created `${filename}.gpg` which is an OpenPGP message that includes the
message together with the signature as a 'signed message'.

This type of file can be verified by:

* `rnp --verify --homedir=${keyringdir} ${filename}.gpg`
* `rnpv -k ${keyringdir}/pubring.gpg ${filename}.gpg`


### Signing in binary detatched format

``` sh
rnp --sign --detach --homedir=${keyringdir} ${filename}
```

=>

Created `${filename}.sig` which is an OpenPGP message in binary
format, that only contains the signature.

This type of file can be verified by:

* `rnp --verify --homedir=${keyringdir} ${filename}.sig`
* `rnpv -k ${keyringdir}/pubring.gpg ${filename}.sig`



### Signing in Armored (ASCII-Armored) format

``` sh
rnp --sign --armor --homedir=${keyringdir} ${filename}
```

=>

Created `${filename}.asc` which is an OpenPGP message in ASCII-armored
format, including the message together with the signature as a 'signed
message'.

This type of file can be verified by:

* `rnp --verify --homedir=${keyringdir} ${filename}.asc`

But this file (and its `--detach` cousin) cannot be verified by
`rnpv` yet.


### Other options

* `--clearsign` option will append a separate PGP Signaure to the end of
  the message (the new output)

* `--detach` option will append a separate PGP Signaure to the end of
  the message (the new output)


## Encrypt


``` sh
rnp --encrypt --homedir=${keyringdir} ${filename}
```

=>

Creates: `${filename}.gpg`


## Decrypt

``` sh
rnp --decrypt --homedir=${keyringdir} ${filename}.gpg
```

=>

Creates: `${filename}`



# Install

## Binaries installed

* `rnp`
* `rnpkeys`
* `rnpv`

## On macOS using Homebrew

``` sh
brew tap riboseinc/rnp
brew install rnp
```

## On RHEL and CentOS via YUM

``` sh
rpm --import https://github.com/riboseinc/yum/raw/master/ribose-packages.pub
curl -L https://github.com/riboseinc/yum/raw/master/ribose.repo > /etc/yum.repos.d/ribose.repo
yum install -y rnp
```

## On Debian

(WIP)


## Compiling from source

Clone this repo or download a release and expand it.

``` sh
./build.sh
make install
```


# Packaging

## Prerequisites

These steps require `docker` installed. It's not strictly necessary,
but just provides a consistent baseline for this guide to work.

Clone source:
```
# cd ~/src
git clone https://github.com/riboseinc/rnp
```

Start container (assuming you git cloned to `~/src/rnp`. Change
accordingly):

```
docker run -v ~/src/rnp:/usr/local/rnp -it centos:7 bash
```

## Install Dependencies


### Required packages

Set up build environment.

In the container:
```
/usr/local/rnp/packaging/redhat/extra/prepare_build.sh
```

### Botan

Botan 2.1 or higher is required.

Installed via `packaging/redhat/extra/build_rpm.sh`.

#### Development versions of Botan

Development branches may depend on unreleased Botan versions (i.e. when
adding support for new crypto algorithms), and should use following
instructions to install Botan instead.

Update `packaging/redhat/extra/build_rpm.sh` to run `install_botan_dev`
instead of `install_botan_stable` to use Botan's development version.


### Cmocka

CMocka 1.1 is required to build and run tests.

Installed via `packaging/redhat/extra/build_rpm.sh`.

## Compile and Install

In the container:

```
cd /usr/local/rnp
ACFLAGS=--with-botan=/usr/local ./build.sh
make install
```

## Running cmocka tests

In the container:

```
export LD_LIBRARY_PATH=/usr/lib:/usr/local/lib
rnp_tests
```

## Clean build artifacts

In the container:

```
cd /usr/local/rnp
./remove_artifacts.sh
```

Otherwise use `git clean`.


## Building RPMs

### Signing

If you're going to sign the RPM,

(In the container:)
```
# Import your packager private key.
gpg --import your-packager.key

# Edit your identities.
PACKAGER="${PACKAGER:-Your Packager <your@packager.com>}"
GPG_NAME="${GPG_NAME:-${PACKAGER}}"

cat <<MACROS >~/.rpmmacros
%_signature gpg
%_gpg_path $HOME/.gnupg
%_gpg_name ${GPG_NAME}
%_gpgbin /usr/bin/gpg
%packager ${PACKAGER}
%_topdir $HOME/rpmbuild
MACROS
```

But if you're just going to test the RPM build process without
GPG-signing,
(In the container:)
```
export SIGN=
```

### Building

Run the rpmbuild script.
(In the container:)
```
cd /usr/local/rnp
./remove_artifacts.sh
packaging/redhat/extra/build_rpm.sh
```

The you can copy out the RPMs from the container:
```
cp ~/rpmbuild/SRPMS/rnp*.rpm ~/rpmbuild/RPMS/x86_64/*.rpm /usr/local/rnp
```

