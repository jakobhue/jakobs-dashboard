#!/usr/bin/env python3
"""Baut Jakobs Dashboard: template.html + data.json -> index.html (AES-verschluesselt).

Aufruf: python3 build.py <passwort>
Benoetigt: pip install cryptography
"""
import base64, json, os, sys

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    if len(sys.argv) < 2:
        sys.exit("Aufruf: build.py <passwort>")
    password = sys.argv[1]

    template = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    data = json.load(open(os.path.join(HERE, "data.json"), encoding="utf-8"))

    stand = data.pop("stand", "unbekannt")
    plain = template.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    plain = plain.replace("__STAND__", stand)

    # GitHub-Token fuer Abhaken/Erstellen: kommt aus dem Secret GH_DISPATCH_TOKEN
    # und landet NUR in der AES-verschluesselten Seite, nie im Klartext-Repo.
    gh_token = os.environ.get("GH_DISPATCH_TOKEN", "").strip()
    plain = plain.replace("__GHTOKEN__", json.dumps(gh_token)[1:-1])
    print("Token eingebaut:", "ja" if gh_token else "nein (Panel-Fallback)")

    salt, iv = os.urandom(16), os.urandom(12)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600000)
    key = kdf.derive(password.encode())
    ct = AESGCM(key).encrypt(iv, plain.encode("utf-8"), None)
    payload = json.dumps({
        "salt": base64.b64encode(salt).decode(),
        "iv": base64.b64encode(iv).decode(),
        "ct": base64.b64encode(ct).decode(),
    })

    loader = open(os.path.join(HERE, "loader.html"), encoding="utf-8").read()
    out = loader.replace("__PAYLOAD__", payload)
    open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(out)
    print("index.html gebaut,", len(out), "bytes, Stand:", stand)

if __name__ == "__main__":
    main()
