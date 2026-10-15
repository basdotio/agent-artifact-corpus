from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import base64

AES_KEY = "ZDBmMTNiZGI3MDRhMWVhMWE3MTcwNjJiNTk0NzY0ODg"


def _fix_base64_padding(b64_string):
    return b64_string + "=" * (-len(b64_string) % 4)


def aes_ecb_decrypt(ciphertext_base64):
    ciphertext_base64 = _fix_base64_padding(ciphertext_base64)
    key_base64 = _fix_base64_padding(AES_KEY)
    ciphertext = base64.b64decode(ciphertext_base64)
    key = base64.b64decode(key_base64)
    cipher = AES.new(key, AES.MODE_ECB)
    decrypted_data = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return decrypted_data.decode("utf-8")
