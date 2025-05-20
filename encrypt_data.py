from cryptography.fernet import Fernet
import base64
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def generate_key(password: str, salt: bytes = None) -> tuple:
    """Gera uma chave de criptografia a partir de uma senha."""
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt

def encrypt_file(input_file: str, output_file: str, password: str):
    """Criptografa um arquivo usando uma senha."""
    # Gerar chave a partir da senha
    key, salt = generate_key(password)
    f = Fernet(key)
    
    # Ler e criptografar o arquivo
    with open(input_file, 'rb') as file:
        data = file.read()
    encrypted_data = f.encrypt(data)
    
    # Salvar o arquivo criptografado junto com o salt
    with open(output_file, 'wb') as file:
        file.write(salt)
        file.write(encrypted_data)
    
    print(f"Arquivo criptografado salvo como: {output_file}")
    print("IMPORTANTE: Guarde a senha em um lugar seguro!")

if __name__ == "__main__":
    input_file = "volume_ajustado.pkl"
    output_file = "volume_ajustado.encrypted"
    password = input("Digite uma senha para criptografar o arquivo: ")
    
    encrypt_file(input_file, output_file, password) 