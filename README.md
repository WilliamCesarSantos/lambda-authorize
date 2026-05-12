# lambda-authorize

A Python AWS Lambda function that authenticates users and issues **RS256-signed JWT tokens**. Users are stored in AWS SSM Parameter Store (or an inline environment variable for quick local testing).

## Architecture

```
Client ──POST /token──► lambda_handler
                              │
                              ├─ Fetch users from SSM Parameter Store (or USERS_LIST env var)
                              ├─ Validate email + MD5(password)
                              └─ Sign JWT with RSA private key → { "token": "<rs256-jwt>" }

Client ──GET /public-key──► lambda_handler → { "publicKey": "<PEM>" }
                                                      ▲
                                            Other services use this
                                            key to verify issued tokens
```

## Prerequisites

| Tool | Version |
|---|---|
| Docker & Docker Compose | v2+ |
| OpenSSL | any modern version |

## Quick Start

### 1. Generate RSA certificates

```bash
chmod +x scripts/generate-certs.sh
./scripts/generate-certs.sh
```

Files created in `certs/`:

| File | Description |
|---|---|
| `private.pem` | RSA 2048-bit private key — used to **sign** JWTs. **Never commit.** |
| `public.pem` | RSA public key — share with other services to **verify** JWTs. |
| `certificate.pem` | Self-signed X.509 certificate — optional mTLS use. |

### 2. Configure users

Edit the `ssm-init` → `command` section in `docker-compose.yml` to set your user list.
Each entry must follow the format:

```json
{"name": "Full Name", "email": "user@example.com", "senha": "<md5-hash>"}
```

Generate an MD5 hash for a password:

```bash
echo -n "my_password" | md5sum
# or on macOS:
echo -n "my_password" | md5
```

### 3. Start the stack

```bash
docker compose up --build
```

Three services are started in order:

| Service | Description |
|---|---|
| `localstack` | Emulates AWS SSM Parameter Store on port 4566 |
| `ssm-init` | Seeds the user list into SSM (runs once, then exits) |
| `lambda-authorize` | Lambda runtime (AWS RIE) on port 9000 |

### 4. Test

**Authenticate and receive a JWT:**

```bash
curl -s -XPOST http://localhost:9000/2015-03-31/functions/function/invocations \
  -H "Content-Type: application/json" \
  -d '{"body": "{\"email\":\"admin@example.com\",\"password\":\"admin\"}"}'
```

Expected response:

```json
{"statusCode": 200, "headers": {...}, "body": "{\"token\": \"<rs256-jwt>\"}"}
```

**Retrieve the RSA public key:**

```bash
curl -s -XPOST http://localhost:9000/2015-03-31/functions/function/invocations \
  -H "Content-Type: application/json" \
  -d '{"httpMethod": "GET", "path": "/public-key"}'
```

## API Reference

### `POST /token`

Authenticates a user and issues a signed JWT.

**Request body:**

```json
{"email": "user@example.com", "password": "plain-text-password"}
```

**Response 200:**

```json
{"token": "<rs256-jwt>"}
```

**JWT payload:**

```json
{
  "name": "Admin",
  "email": "admin@example.com",
  "iat": 1715000000,
  "exp": 1715003600
}
```

**Error responses:**

| Status | Reason |
|---|---|
| 400 | Missing or malformed `email` / `password` |
| 401 | Credentials do not match any user |
| 500 | Failed to load users from SSM or private key not found |

---

### `GET /public-key`

Returns the RSA public key in PEM format so other services can verify JWTs.

**Response 200:**

```json
{"publicKey": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n"}
```

## Verifying a JWT in another service

**Using the local file (recommended for internal services):**

```python
import jwt

public_key = open("certs/public.pem", "rb").read()
payload = jwt.decode(token, public_key, algorithms=["RS256"])
print(payload["name"], payload["email"])
```

**Fetching the key dynamically from the Lambda endpoint:**

```python
import json
import requests
import jwt

# Fetch public key
resp = requests.post(
    "http://localhost:9000/2015-03-31/functions/function/invocations",
    json={"httpMethod": "GET", "path": "/public-key"},
)
public_key = json.loads(resp.json()["body"])["publicKey"]

# Verify token
payload = jwt.decode(token, public_key, algorithms=["RS256"])
print(payload["name"], payload["email"])
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `JWT_PRIVATE_KEY_PATH` | `/var/task/certs/private.pem` | Path to the RSA private key (PEM) |
| `JWT_PUBLIC_KEY_PATH` | `/var/task/certs/public.pem` | Path to the RSA public key (PEM) |
| `JWT_EXPIRATION_HOURS` | `1` | Token validity in hours |
| `USERS_LIST` | _(unset)_ | JSON user list — overrides SSM when set |
| `USERS_PARAM_NAME` | `/lambda-authorize/users` | SSM parameter name |
| `AWS_ENDPOINT_URL` | _(unset)_ | Custom AWS endpoint (e.g. `http://localstack:4566`) |
| `AWS_DEFAULT_REGION` | `us-east-1` | AWS region |

## GitHub Actions

The workflow at [.github/workflows/build-and-push.yml](.github/workflows/build-and-push.yml) builds a multi-platform image (`linux/amd64`, `linux/arm64`) and pushes it to Docker Hub on every merge to `main`. Pull requests only trigger the build step (no push).

**Required repository secrets:**

| Secret | How to obtain |
|---|---|
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `DOCKERHUB_TOKEN` | *hub.docker.com → Account Settings → Security → New Access Token* |

## Project Structure

```
lambda-authorize/
├── src/
│   └── lambda_function.py        # Lambda handler (RS256 JWT issuance)
├── certs/                        # RSA keys — git-ignored (generate with the script below)
│   ├── .gitkeep
│   ├── private.pem               # [generated] Sign tokens
│   ├── public.pem                # [generated] Verify tokens (share with other services)
│   └── certificate.pem           # [generated] Self-signed X.509 cert
├── scripts/
│   └── generate-certs.sh         # Key-pair generation helper
├── Dockerfile
├── docker-compose.yml            # LocalStack + ssm-init + lambda
├── requirements.txt
├── .env                          # Local dev config (git-ignored)
├── .env.example                  # Template for other environments
└── .github/
    └── workflows/
        └── build-and-push.yml    # CI/CD: build + push to Docker Hub
```

## Security Notes

- Passwords are stored as **MD5 hashes**. MD5 is not suitable for production — consider bcrypt or Argon2 for real-world deployments.
- The RSA **private key is never baked into the Docker image**; it is mounted as a read-only volume at runtime.
- In production, store the private key in **AWS Secrets Manager** and load it at cold start instead of mounting a file.
- The `certs/` directory is listed in both `.gitignore` and `.dockerignore`.
