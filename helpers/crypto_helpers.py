from extensions import fernet

def encrypt_string(value: str) -> str:
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")

def decrypt_string(value: str) -> str:
    return fernet.decrypt(value.encode("utf-8")).decode("utf-8")