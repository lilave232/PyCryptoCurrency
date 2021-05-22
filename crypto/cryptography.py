from tinyec import registry
import hashlib
from ecdsa import SigningKey, VerifyingKey, SECP256k1
import os
curve = registry.get_curve('brainpoolP256r1')
import uuid


def hash_block(block):
    sha3_key = hashlib.sha3_256()
    sha3_key.update(block)
    return sha3_key.digest()

def hash_pub_key(pub_key):
    #Convert the x & y components to bytes of length 32
    try:
        x_component = int.to_bytes(pub_key.x, 32, 'big')
        y_component = int.to_bytes(pub_key.y, 32, 'big')
        #Create a SHA3_256 class
        sha3_key = hashlib.sha3_256()
        #Update the hash object with x_component
        sha3_key.update(x_component)
        #Concatenate the y_component with x_component in the hash object
        sha3_key.update(y_component)
        #Derive the key
        secret_key = sha3_key.digest()
        return secret_key
    except:
        raise Exception("Unable to Hash Key")

def sign_msg(msg,privateKey):
    signature = privateKey.sign(msg)
    return signature.hex()

def pub_key_from_string(pubKey):
    return VerifyingKey.from_string(bytes.fromhex(pubKey),curve = SECP256k1)

def priv_key_from_string(privKey):
    return SigningKey.from_string(bytes.fromhex(privKey),curve = SECP256k1)

def verify_msg(signature,string,publicKey):
    vk = publicKey
    assert vk.verify(signature, string)

def test_verify(sk):
    signature = sk.sign(b"message")
    vk = sk.verifying_key
    print("TESTING")
    assert vk.verify(signature, b"message")


def read_key(file):
    with open(file) as f:
        sk = SigningKey.from_pem(f.read())
    vk = sk.verifying_key
    sha3_key = hashlib.sha3_256()
    sha3_key.update(vk.to_string())
    hash = sha3_key.digest()
    return hash,sk

def hash_v_key(pubKey):
    sha3_key = hashlib.sha3_256()
    sha3_key.update(pubKey.to_string())
    hash = sha3_key.digest()
    return hash

def create_key_no_file():
    sk = SigningKey.generate(curve = SECP256k1)
    vk = sk.verifying_key
    sha3_key = hashlib.sha3_256()
    sha3_key.update(vk.to_string())
    hash = sha3_key.digest()
    return hash,sk

def create_key(dir):
    #Generating Alice's private 
    if (os.path.isdir(dir) == False):
        os.mkdir(dir)
    sk = SigningKey.generate(curve = SECP256k1)
    vk = sk.verifying_key
    sha3_key = hashlib.sha3_256()
    sha3_key.update(vk.to_string())
    hash = sha3_key.digest()
    with open(os.path.join(dir,uuid.uuid4().hex), "wb") as f:
        f.write(sk.to_pem())
    return hash,sk

