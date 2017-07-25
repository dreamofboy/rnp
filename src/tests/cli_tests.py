#!/usr/bin/python

import sys
import distutils.spawn
import tempfile
import os
from os import path
import shutil
import subprocess
import re
from subprocess import Popen, PIPE
from cli_common import find_utility, run_proc, pswd_pipe, rnp_file_path

WORKDIR = ''
RNP = ''
RNPK = ''
GPG = ''
RNPDIR = ''
PASSWORD = 'password'
RMWORKDIR = False

RE_RSA_KEY = r'^' \
r'# off=0 ctb=c6 tag=6 hlen=3 plen=\d+ new-ctb\s+' \
r':public key packet:\s+' \
r'version 4, algo 1, created \d+, expires 0\s+' \
r'pkey\[0\]: \[(\d{4}) bits\]\s+' \
r'pkey\[1\]: \[17 bits\]\s+' \
r'keyid: ([0-9A-F]{16})\s+' \
r'# off=\d+ ctb=cd tag=13 hlen=\d+ plen=\d+ new-ctb\s+' \
r':user ID packet: "(.+)"\s+' \
r'# off=\d+ ctb=c2 tag=2 hlen=3 plen=\d+ new-ctb\s+' \
r':signature packet: algo 1, keyid \2\s+' \
r'version 4, created \d+, md5len 0, sigclass 0x13\s+' \
r'digest algo 8, begin of digest [0-9a-f]{2} [0-9a-f]{2}\s+' \
r'hashed subpkt 2 len 4 \(sig created \d{4}-\d{2}-\d{2}\)\s+' \
r'hashed subpkt 16 len 8 \(issuer key ID \2\)\s+' \
r'hashed subpkt 25 len 1 \(primary user ID\)\s+' \
r'data: \[\d{4} bits\]$'

RE_RSA_KEY_LIST = r'^\s*' \
r'1 key found\s+' \
r'signature  (\d{4})/RSA \(Encrypt or Sign\) ([0-9a-z]{16}) \d{4}-\d{2}-\d{2} \[\]\s+' \
r'Key fingerprint: ([0-9a-z]{40})\s+' \
r'uid\s+(.+)\s*$'

RE_MULTIPLE_KEY_LIST = r'(?s)^\s*(\d+) (?:key|keys) found.*$'
RE_MULTIPLE_KEY_5 = r'(?s)^\s*' \
r'5 keys found.*' \
r'.+uid\s+0@rnp-multiple' \
r'.+uid\s+1@rnp-multiple' \
r'.+uid\s+2@rnp-multiple' \
r'.+uid\s+3@rnp-multiple' \
r'.+uid\s+4@rnp-multiple.*$'

RE_GPG_SINGLE_RSA_KEY = r'(?s)^\s*' \
r'.+-+\s*' \
r'pub\s+rsa.+' \
r'\s+([0-9A-F]{40})\s*' \
r'uid\s+.+rsakey@gpg.*'

def setup():
    # Setting up directories.
    global RMWORKDIR, WORKDIR, RNPDIR, RNPK, GPG, GPGDIR
    WORKDIR = os.getcwd()
    if not '/tmp/' in WORKDIR:
        WORKDIR = tempfile.mkdtemp()
        RMWORKDIR = True

    print 'Running in ' + WORKDIR

    RNPDIR = path.join(WORKDIR, '.rnp')
    RNP = rnp_file_path('src/rnp/rnp')
    RNPK = rnp_file_path('src/rnpkeys/rnpkeys')
    os.mkdir(RNPDIR, 0700)

    GPGDIR = path.join(WORKDIR, '.gpg')
    GPG = find_utility('gpg')
    os.mkdir(GPGDIR, 0700)

    return

def check_packets(fname, regexp):
    ret, output, err = run_proc(GPG, ['--list-packets', fname])
    if ret != 0:
        print err
        return None
    else:
        result = re.match(regexp, output)
        if not result: print 'Wrong packets: \n' + output
        return result

def clear_keyrings():
    shutil.rmtree(RNPDIR)
    shutil.rmtree(GPGDIR)
    os.mkdir(RNPDIR, 0700)
    os.mkdir(GPGDIR, 0700)

    return

def raise_err(msg, log = None):
    if log: print log
    raise NameError(msg)

def rnpkey_generate_rsa(bits = None):
    # setup command line params
    if bits: 
        params = ['--numbits', str(bits)]
    else:
        params = []
        bits = 2048

    print 'rnpkey_generate_rsa {}'.format(bits)
    userid = str(bits) + '@rnptest'
    # open pipe for password
    pipe = pswd_pipe(PASSWORD) 
    params = params + ['--homedir', RNPDIR, '--pass-fd', str(pipe), '--userid', userid, '--generate-key']
    # run key generation
    ret, out, err = run_proc(RNPK, params)
    os.close(pipe)

    if ret != 0: raise_err('key generation failed', err)
    # check packets using the gpg
    match = check_packets(path.join(RNPDIR, 'pubring.gpg'), RE_RSA_KEY)
    if not match : raise_err('generated key check failed')
    keybits = int(match.group(1))
    if keybits > bits or keybits <= bits - 8 : raise_err('wrong key bits')
    keyid = match.group(2)
    if not match.group(3) == userid: raise_err('wrong user id')
    # list keys using the rnpkeys
    ret, out, err = run_proc(RNPK, ['--homedir', RNPDIR, '--list-keys'])
    if ret != 0: raise_err('key list failed', err)
    match = re.match(RE_RSA_KEY_LIST, out)
    # compare key ids
    if not match: raise_err('wrong key list output', out)
    if not match.group(3)[-16:] == match.group(2) or not match.group(2) == keyid.lower():
        raise_err('wrong key ids')
    if not match.group(1) == str(bits):
        raise_err('wrong key bits in list')
    # import key to the gnupg
    ret, out, err = run_proc(GPG, ['--batch', '--passphrase', PASSWORD, '--homedir', GPGDIR, '--import', path.join(RNPDIR, 'pubring.gpg'), path.join(RNPDIR, 'secring.gpg')])
    if ret != 0: raise_err('gpg key import failed', err)

    return

def rnpkey_generate_multiple():
    print 'rnpkey_generate_multiple'
    
    # Generate 5 keys with different user ids
    for i in range(0, 5):
        # generate the next key
        pipe = pswd_pipe(PASSWORD)
        userid = str(i) + '@rnp-multiple'
        ret, out, err = run_proc(RNPK, ['--numbits', '2048', '--homedir', RNPDIR, '--pass-fd', str(pipe), '--userid', userid, '--generate-key'])
        os.close(pipe)
        if ret != 0: raise_err('key generation failed', err)
        # list keys using the rnpkeys, checking whether it reports correct key number
        ret, out, err = run_proc(RNPK, ['--homedir', RNPDIR, '--list-keys'])
        if ret != 0: raise_err('key list failed', err)
        match = re.match(RE_MULTIPLE_KEY_LIST, out)
        if not match: raise_err('wrong key list output', out)
        if not match.group(1) == str(i + 1):
            raise_err('wrong key count')

    # Checking the 5 keys output
    ret, out, err = run_proc(RNPK, ['--homedir', RNPDIR, '--list-keys'])
    if ret != 0: raise_err('key list failed', err)
    match = re.match(RE_MULTIPLE_KEY_5, out)
    if not match: raise_err('wrong key list output', out)

    return

def rnpkey_import_from_gpg():
    print 'rnpkey_import_from_gpg'
    # Generate key in GnuPG
    ret, out, err = run_proc(GPG, ['--batch', '--homedir', GPGDIR, '--passphrase', '', '--quick-generate-key', 'rsakey@gpg', 'rsa'])
    if ret != 0: raise_err('gpg key generation failed', err)
    # Getting fingerprint of the generated key
    ret, out, err = run_proc(GPG, ['--batch', '--homedir', GPGDIR, '--list-keys'])
    match = re.match(RE_GPG_SINGLE_RSA_KEY, out)
    if not match: raise_err('wrong gpg key list output', out)
    keyfp = match.group(1)
    # Exporting generated public key
    ret, out, err = run_proc(GPG, ['--batch', '--homedir', GPGDIR, '--armour', '--export', keyfp])
    if ret != 0: raise_err('gpg : public key export failed', err)
    pubpath = path.join(RNPDIR, keyfp + '-pub.asc')
    with open(pubpath, 'w+') as f:
        f.write(out)
    # Export generated secret key
    ret, out, err = run_proc(GPG, ['--batch', '--homedir', GPGDIR, '--armour', '--export-secret-key', keyfp])
    if ret != 0: raise_err('gpg : secret key export failed', err)
    secpath = path.join(RNPDIR, keyfp + '-sec.asc')
    with open(secpath, 'w+') as f:
        f.write(out)
    # Import public key
    ret, out, err = run_proc(RNPK, ['--homedir', RNPDIR, '--import-key', pubpath])
    if ret != 0: raise_err('rnp : public key import failed', err)

    # Import secret key
    ret, out, err = run_proc(RNPK, ['--homedir', RNPDIR, '--import-key', secpath])
    if ret != 0: raise_err('rnp : secret key import failed', err)

    return

def rnpkey_export_to_gpg():

    return

def run_rnpkeys_tests():
    # 1. Generate default RSA key
    rnpkey_generate_rsa()
    clear_keyrings()
    # 2. Generate 4096-bit RSA key
    rnpkey_generate_rsa(4096)
    clear_keyrings()
    # 3. Generate multiple RSA keys and check if they are all available
    rnpkey_generate_multiple()
    clear_keyrings()
    # 4. Generate key with GnuPG and import it to rnp
    rnpkey_import_from_gpg()
    # 5. Generate key with RNP and export it and then import to GnuPG
    rnpkey_export_to_gpg()

    return

def run_rnp_tests():
    
    return

def run_tests():
    if not len(sys.argv) == 2:
        print "Wrong usage. Run cli_tests [rnp | rnpkeys]"
        sys.exit(1)

    if sys.argv[1] == 'rnp':
        run_rnp_tests()
    elif sys.argv[1] == 'rnpkeys':
        run_rnpkeys_tests()
    else:
        print "Wrong parameter {}".format(sys.argv[1])
        sys.exit(1)

    return

def cleanup():
    if RMWORKDIR:
        shutil.rmtree(WORKDIR)
    else:
        shutil.rmtree(RNPDIR)
        shutil.rmtree(GPGDIR)

    return

if __name__ == '__main__':
    setup()
    run_tests()
    cleanup()