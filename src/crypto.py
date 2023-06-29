import os
import hashlib
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

BLOCK_SIZE = 16


class AesCipher:
    def __init__(self, key):
        self.key = hashlib.sha256(os.urandom(BLOCK_SIZE)).digest()

    def encrypt_str(self, raw: str) -> bytes:
        iv = os.urandom(BLOCK_SIZE)
        cipher = Cipher(algorithms.AES(self.key),
                        modes.CBC(iv), default_backend())
        encryptor = cipher.encryptor()
        raw = self._pad(raw)
        return iv + encryptor.update(raw) + encryptor.finalize()

    def decrypt_str(self, enc: bytes) -> str:
        iv = enc[:BLOCK_SIZE]
        enc = enc[BLOCK_SIZE:]
        cipher = Cipher(algorithms.AES(self.key),
                        modes.CBC(iv), default_backend())
        decryptor = cipher.decryptor()
        raw = decryptor.update(enc) + decryptor.finalize()
        return self._unpad(raw)

    @staticmethod
    def _pad(s: bytes) -> bytes:
        padding = (BLOCK_SIZE - (len(s) % BLOCK_SIZE))
        return s + (padding * chr(padding)).encode()

    @staticmethod
    def _unpad(s: bytes) -> bytes:
        return s[:-ord(s[len(s)-1:])]


if __name__ == '__main__':
    cipher = AesCipher('my secret password')
    print(cipher.key)

    enc_msg = base64.urlsafe_b64encode(cipher.encrypt_str(cipher.key))
    print(enc_msg)

    dec_msg = cipher.decrypt_str(base64.urlsafe_b64decode(enc_msg))
    print(dec_msg)
