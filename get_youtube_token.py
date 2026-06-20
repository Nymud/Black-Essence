import os, pickle, webbrowser, hashlib, base64, secrets, json, urllib.parse, sys
import requests

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET = "client_secret.json"
TOKEN_PICKLE = "youtube_token.pickle"

with open(CLIENT_SECRET) as f:
    cfg = json.load(f)["installed"]

client_id = cfg["client_id"]
client_secret = cfg["client_secret"]
token_uri = cfg["token_uri"]
redirect_uri = "http://localhost:8080/"

def save_token(token):
    with open(TOKEN_PICKLE, "wb") as f:
        pickle.dump(token, f)
    return token

def exchange_code(code, code_verifier):
    r = requests.post(token_uri, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "code": code,
        "code_verifier": code_verifier,
    })
    if r.ok:
        return save_token(r.json())
    raise Exception(f"Token exchange failed: {r.text}")

# If redirect URL is passed as argument
if len(sys.argv) > 2 and sys.argv[1] == "--exchange":
    code = sys.argv[2]
    cv = sys.argv[3] if len(sys.argv) > 3 else ""
    token = exchange_code(code, cv)
    print(f"Token saved to: {os.path.abspath(TOKEN_PICKLE)}")
    print(f"YOUTUBE_TOKEN=pickle://{os.path.abspath(TOKEN_PICKLE)}")
    exit(0)

# First run: generate auth URL
code_verifier = secrets.token_urlsafe(96)
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).decode().rstrip("=")
state = secrets.token_urlsafe(32)
params = {
    "client_id": client_id,
    "redirect_uri": redirect_uri,
    "response_type": "code",
    "scope": " ".join(SCOPES),
    "access_type": "offline",
    "prompt": "consent",
    "state": state,
    "code_challenge": code_challenge,
    "code_challenge_method": "S256",
}
url = f"{cfg['auth_uri']}?{urllib.parse.urlencode(params)}"
print(url)
print(f"\nCODE_VERIFIER={code_verifier}")
print(f"STATE={state}")
