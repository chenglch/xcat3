"""Utilities and helper functions for crypt password"""
import crypt
import random
import string

MD5_PREFIX = '$1$'
SHA256_PREFIX = '$5$'
SHA512_PREFIX = '$6$'
CRYPT_METHOD_PREFIX = (MD5_PREFIX, SHA256_PREFIX, SHA512_PREFIX)
CRYPT_DICT = {'md5': MD5_PREFIX, 'sha256': SHA256_PREFIX,
              'sha512': SHA512_PREFIX}
CRYPT_METHODS = ('md5', 'sha256', 'sha512')


def crypt_passwd(password, method=None, salt=None):
    # already encrypted
    if password[0:3] in CRYPT_METHOD_PREFIX:
        return password

    if salt is None:
        rand = random.SystemRandom()
        salt = ''.join([rand.choice(string.ascii_letters + string.digits)
                        for _ in range(8)])

    # if not set use sha256 by default
    prefix = CRYPT_DICT.get(method, SHA256_PREFIX)
    return crypt.crypt(password, prefix + salt)
