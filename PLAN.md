# Plano de Implementação — lambda-authorize

## Sumário das mudanças

| Área | Antes | Depois |
|---|---|---|
| Fonte de usuários | SSM Parameter Store / env var `USERS_LIST` | Aurora PostgreSQL (produção) / PostgreSQL 17.4 (local) |
| Hash de senha | MD5 (sem salt) | Argon2id com pepper via Secrets Manager (salt embutido no hash) |
| Endpoint principal | `POST /token` | `POST /login` |
| Chave pública | — | `GET /.well-known/jwks.json` (formato JWKS, requer Bearer token) |
| Pepper | Env var direta | AWS Secrets Manager |
| Certificados JWT | Arquivos em `certs/` montados no container | Gerados localmente, importados para o Secrets Manager |
| Roles de usuário | Inexistentes | Coluna `roles TEXT[]` na tabela `users`; incluída no JWT |
| Infraestrutura local | LocalStack 3 (SSM) | LocalStack 4.14.0 (Secrets Manager) + PostgreSQL 17.4 |
| Init do LocalStack | Container `amazon/aws-cli` dedicado | Script interno via `/etc/localstack/init/ready.d/` |
| Init do PostgreSQL | Container separado para migration | Script SQL em `/docker-entrypoint-initdb.d/` |
| Init do banco em produção | — | Manual (developer executa as migrations após provisionamento) |
| Deploy em nuvem | — | Terraform (AWS, região padrão `sa-east-1`) |
| CI/CD | — | GitHub Actions: `build` + `test` (todas as branches) + `deploy` (manual, só `main`) |
| Testes | — | Testes unitários com `pytest` |
| Scripts auxiliares | `scripts/generate-certs.sh` | Removido |

---

## Estrutura de arquivos resultante

```
lambda-authorize/
├── .github/
│   └── workflows/
│       ├── build.yml
│       ├── test.yml
│       └── deploy.yml
├── certs/
│   ├── private.pem          ← gerado localmente (OpenSSL), nunca commitado
│   └── public.pem           ← gerado localmente (OpenSSL), nunca commitado
├── migrations/
│   ├── 01_schema.sql        ← executado automaticamente pelo PostgreSQL container
│   └── 02_seed.sql          ← INSERT com hash pré-calculado
├── scripts/
│   └── localstack-init.sh   ← script montado em /etc/localstack/init/ready.d/
├── src/
│   ├── lambda_function.py
│   ├── db/
│   │   └── connection.py
│   ├── handlers/
│   │   ├── login_handler.py
│   │   └── jwks_handler.py     ← substitui public_key_handler; retorna JWKS + exige Bearer token
│   ├── middleware/
│   │   └── auth.py             ← valida Authorization: Bearer <jwt> antes de handlers protegidos
│   ├── repositories/
│   │   ├── user_repository.py
│   │   └── role_repository.py  ← consulta roles do usuário (buscados via user_repository)
│   └── services/
│       ├── password_service.py
│       ├── secrets_service.py
│       ├── jwks_service.py     ← extrai n, e da chave RSA pública para formato JWKS
│       └── token_service.py
├── tests/
│   └── unit/
│       ├── conftest.py
│       ├── test_login_handler.py
│       ├── test_jwks_handler.py
│       ├── test_password_service.py
│       ├── test_token_service.py
│       ├── test_user_repository.py
│       └── test_role_repository.py
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── modules/
│       ├── networking/
│       │   ├── main.tf
│       │   ├── variables.tf
│       │   └── outputs.tf
│       ├── rds/
│       │   ├── main.tf
│       │   ├── variables.tf
│       │   └── outputs.tf
│       ├── secrets/
│       │   ├── main.tf
│       │   ├── variables.tf
│       │   └── outputs.tf
│       └── lambda/
│           ├── main.tf
│           ├── variables.tf
│           └── outputs.tf
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

> `scripts/generate-certs.sh` removido. Os arquivos `certs/private.pem` e `certs/public.pem` são gerados pelo desenvolvedor via OpenSSL uma única vez e adicionados ao `.gitignore`. O script `scripts/localstack-init.sh` os lê e cria os secrets no LocalStack.

---

## Banco de Dados

### Migration: `migrations/01_schema.sql`

Montado em `/docker-entrypoint-initdb.d/01_schema.sql`. O PostgreSQL executa automaticamente todos os arquivos neste diretório na primeira inicialização do container, em ordem alfabética. Em produção (Aurora), o developer executa manualmente via `psql`.

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE users (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name          VARCHAR(255) NOT NULL,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT         NOT NULL,
    roles         TEXT[]       NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
```

> O campo `salt` foi removido. O Argon2id embute o salt no próprio hash (formato PHC string: `$argon2id$v=19$m=65536,t=3,p=4$<salt_b64>$<hash_b64>`). Não é necessário armazená-lo separadamente.
>
> O campo `roles` armazena um array de strings PostgreSQL. Exemplos de roles possíveis: `'admin'`, `'read'`, `'write'`. Usuários sem role ficam com array vazio `'{}'`. O conteúdo do array é incluído diretamente no payload JWT.

### Seed: `migrations/02_seed.sql`

Também montado em `/docker-entrypoint-initdb.d/`. Executado logo após o schema.

Os hashes foram pré-calculados localmente com:
- **Pepper (dev)**: `dev-pepper-DO-NOT-USE-IN-PRODUCTION`
- **Algoritmo**: Argon2id (`time_cost=3, memory_cost=65536, parallelism=4`)

| Usuário | Email | Senha | Roles |
|---|---|---|---|
| William Cesar Santos | `william_cesar_santos@hotmail.com` | `lambda_123_AUTHORIZE` | `{admin}` |
| Ana Paula | `ana@example.com` | `user_An4_p4ssw0rd` | `{}` |
| Carlos Eduardo | `carlos@example.com` | `user_C4rl0s_p4ss` | `{}` |

> Em produção, recalcule todos os hashes com o pepper real antes de executar o seed.

```sql
INSERT INTO users (name, email, password_hash, roles) VALUES
(
    'William Cesar Santos',
    'william_cesar_santos@hotmail.com',
    '$argon2id$v=19$m=65536,t=3,p=4$oMI7dPuZD9JmemIhXLr1Qw$qfsUbmhrCysvix+/ycXcCqjjWVdpaD/R2Qayxil3CN4',
    '{admin}'
),
(
    'Ana Paula',
    'ana@example.com',
    '$argon2id$v=19$m=65536,t=3,p=4$1XiN0Gm0+b3MIVTHpCzOXg$qY+CJc3mhKHrsE+8yW+4ivEGZvjJyZ3/Ljj9Feb5YPw',
    '{}'
),
(
    'Carlos Eduardo',
    'carlos@example.com',
    '$argon2id$v=19$m=65536,t=3,p=4$jmlcdLHM9RST0ADLs+yMkA$F+i3PhNNvgxhp0CKGaIoCXDkQu2dyAy2fUP78gUwwaE',
    '{}'
);
```

> Este seed é válido apenas para o ambiente local. Em produção, o hash deve ser recalculado com o pepper real.

---

## Certificados JWT

### Estratégia: geração local + importação para o Secrets Manager

Os certificados RSA são gerados **uma única vez** pelo developer localmente via OpenSSL e armazenados em `certs/` (listado no `.gitignore`). Em nenhum momento os arquivos PEM são commitados no repositório.

#### Por que não usar KMS para gerar a chave?

| Serviço | Pode gerar par RSA? | Custo | Limitação |
|---|---|---|---|
| **ACM** (Certificate Manager) | Somente certificados TLS/SSL | Grátis (para ALB/CloudFront) | Não serve para JWT |
| **KMS** (Key Management Service) | Sim — par RSA 2048/3072/4096 | $1,00/chave/mês + $0,03/10k chamadas | **Chave privada não é exportável** — assina via `kms:Sign` |
| **Secrets Manager** | Não gera, apenas armazena | $0,40/secret/mês | Você gera localmente e armazena |

**Decisão**: gerar localmente via OpenSSL (sem custo) e importar os PEMs para o Secrets Manager (~$0,80/mês para chave privada + chave pública). KMS tornaria a implementação mais complexa (signing remoto) e adicionaria latência e custo por invocação.

#### Fluxo de geração e importação

```
openssl genrsa -out certs/private.pem 2048
openssl rsa -in certs/private.pem -pubout -out certs/public.pem
```

**Ambiente local (Docker Compose)**: o `scripts/localstack-init.sh` lê `certs/private.pem` e `certs/public.pem` do volume montado e cria os secrets via `awslocal secretsmanager create-secret`.

**Produção (Terraform)**: o developer passa os PEMs como variáveis sensíveis (`-var 'private_key_pem=$(cat certs/private.pem)'`). O módulo `secrets` cria os secrets no Secrets Manager real.

### Secrets criados no Secrets Manager

| Secret name | Conteúdo | Onde é usado |
|---|---|---|
| `/lambda-authorize/pepper` | String do pepper | `password_service.py` |
| `/lambda-authorize/private-key` | Conteúdo PEM da chave privada | `token_service.py` |
| `/lambda-authorize/public-key` | Conteúdo PEM da chave pública | `jwks_service.py` |
| `/lambda-authorize/db-password` | Senha do banco (gerada pelo Terraform) | `db/connection.py` |

---

## Lambda — módulos e responsabilidades

### `src/lambda_function.py`
Ponto de entrada. Apenas faz roteamento para os handlers.

| Rota | Handler |
|---|---|
| `POST /login` | `login_handler.handle()` |
| `GET /.well-known/jwks.json` | `auth_middleware.require_jwt()` → `jwks_handler.handle()` |

### `src/handlers/login_handler.py`
- Endpoint: `POST /login`
- Parse do body: `{ "email": "...", "password": "..." }`
- Delega validação para `password_service` e emissão do token para `token_service`
- Retorna `{ "token": "<jwt-rs256>" }` em caso de sucesso
- Token JWT inclui no payload: `{ sub, name, email, roles, iat, exp }`

### `src/handlers/jwks_handler.py`
- Endpoint: `GET /.well-known/jwks.json`
- **Requer autenticação**: exige `Authorization: Bearer <jwt>` válido (verificado pelo `auth_middleware`)
- Lê a chave pública PEM do Secrets Manager via `secrets_service`
- Delega conversão RSA→JWKS para `jwks_service`
- Retorna resposta no formato JWKS:
  ```json
  {
    "keys": [
      {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": "<JWKS_KID env var>",
        "n": "<modulus base64url>",
        "e": "<exponent base64url>"
      }
    ]
  }
  ```

> **Nota sobre autenticação do JWKS**: exigir um Bearer token para acessar o endpoint JWKS cria uma dependência de bootstrap — o consumidor precisa de um token antes de obter a chave pública. O fluxo esperado é: (1) o consumidor autentica via `POST /login`, (2) usa o token obtido para chamar `GET /.well-known/jwks.json`, (3) armazena em cache a chave pública para verificações futuras. Isso restringe o acesso ao JWKS apenas a usuários/serviços autenticados.

### `src/middleware/auth.py`
- Extrai o header `Authorization: Bearer <token>`
- Busca a chave pública do Secrets Manager (com cache em memória dentro da invocação)
- Verifica o JWT RS256 com `PyJWT`
- Retorna resposta `401 Unauthorized` se o token for inválido, expirado ou ausente
- Se válido, chama o handler seguinte com o evento original

### `src/repositories/user_repository.py`
- Consulta `SELECT id, name, email, password_hash FROM users WHERE email = %s`
- Retorna um `dataclass` ou `None`

### `src/services/password_service.py`
- `verify(password, stored_hash, pepper) -> bool`
- Usa `argon2-cffi`: `ph.verify(stored_hash, password + pepper)`

### `src/services/secrets_service.py`
- Funções: `get_pepper()`, `get_private_key()`, `get_public_key()`
- Busca cada secret do Secrets Manager via `boto3`
- Cache em memória por nome de secret (variável de módulo — válido pelo ciclo de vida do container Lambda)

### `src/services/token_service.py`
- `issue(user) -> str`
- Obtém chave privada via `secrets_service.get_private_key()`
- Emite JWT RS256 com payload `{ sub, name, email, roles, iat, exp }`
- O campo `kid` (Key ID) é incluído no header JWT usando o valor de `JWKS_KID`
- Expiração configurável via `JWT_EXPIRATION_HOURS` (padrão: `1`)

### `src/services/jwks_service.py`
- `build_jwks(public_key_pem: str) -> dict`
- Usa a biblioteca `cryptography` para carregar a chave pública PEM
- Extrai os componentes RSA: módulo `n` e expoente público `e`
- Converte para base64url (sem padding) conforme RFC 7517
- Retorna o dict JWKS completo com `kty`, `use`, `alg`, `kid`, `n`, `e`

### `src/repositories/user_repository.py`
- `find_by_email(conn, email) -> dict | None`
- Retorna todos os campos do usuário incluindo `roles` (array PostgreSQL → lista Python)

### `src/repositories/role_repository.py`
- Módulo reservado para queries futuras relacionadas a roles
- Inicialmente pode conter apenas `list_roles_for_user(conn, user_id) -> list[str]`
- Na implementação atual, `roles` é retornado diretamente pelo `user_repository`

### `src/db/connection.py`
- Abre conexão `psycopg3` usando variáveis de ambiente:
  `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

---

## Variáveis de ambiente da Lambda

| Variável | Descrição | Local | Produção |
|---|---|---|---|
| `DB_HOST` | Host do PostgreSQL | `postgres` | endpoint do cluster Aurora |
| `DB_PORT` | Porta | `5432` | `5432` |
| `DB_NAME` | Nome do banco | `lambdaauth` | `lambdaauth` |
| `DB_USER` | Usuário do banco | `lambda` | gerenciado pelo Aurora |
| `DB_PASSWORD` | Senha do banco | `lambda` | injetada pelo Terraform |
| `AWS_ENDPOINT_URL` | Endpoint AWS | `http://localstack:4566` | não definida |
| `JWT_EXPIRATION_HOURS` | TTL do token | `1` | `1` |
| `PEPPER_SECRET_NAME` | Nome do secret do pepper | `/lambda-authorize/pepper` | `/lambda-authorize/pepper` |
| `PRIVATE_KEY_SECRET_NAME` | Nome do secret da chave privada | `/lambda-authorize/private-key` | `/lambda-authorize/private-key` |
| `PUBLIC_KEY_SECRET_NAME` | Nome do secret da chave pública | `/lambda-authorize/public-key` | `/lambda-authorize/public-key` |
| `JWKS_KID` | Key ID incluído no header JWT e no response JWKS | `dev-key-1` | ex: `prod-key-1` |
| `AWS_REGION` | Região | `sa-east-1` | `sa-east-1` |

---

## Dependências (`requirements.txt`)

```
PyJWT==2.9.0
psycopg[binary]==3.2.6
argon2-cffi==23.1.0
boto3==1.34.149
cryptography==43.0.3
```

> A biblioteca `cryptography` é necessária para carregar a chave pública PEM e extrair os componentes RSA (`n`, `e`) para o response JWKS. Nota: a imagem `public.ecr.aws/lambda/python:3.13` não inclui `cryptography` por padrão.

### Dependências de desenvolvimento/teste (`requirements-dev.txt`)

```
pytest==8.3.5
pytest-mock==3.14.0
```

---

## Testes unitários

### Estrutura: `tests/unit/`

| Arquivo | O que testa |
|---|---|
| `conftest.py` | Fixtures compartilhadas: `mock_user`, `mock_event`, chaves RSA de teste |
| `test_password_service.py` | Verificação de hash válido, hash inválido, senha incorreta |
| `test_token_service.py` | Emissão de JWT com claims corretos (incl. `roles`, `kid`), expiração |
| `test_login_handler.py` | Body malformado → 400; credenciais inválidas → 401; sucesso → 200 |
| `test_jwks_handler.py` | Token ausente → 401; token inválido → 401; token válido → 200 com JWKS correto |
| `test_user_repository.py` | Usuário encontrado, usuário não encontrado (mock da conexão psycopg) |
| `test_role_repository.py` | Lista de roles por usuário (mock da conexão psycopg) |

Todos os testes são unitários puros — sem banco real, sem AWS real. Conexão e Secrets Manager são substituídos por mocks via `pytest-mock`.

---

## Docker Compose — ambiente local

### Serviços e ordem de inicialização

```
localstack ──(init script interno)──► cria secrets automaticamente
postgres   ──(initdb.d/)──────────────► schema + seed executados automaticamente
     │                        │
     └────── ambos healthy ───┴──► lambda-authorize
```

A inicialização do LocalStack e do PostgreSQL acontece internamente em cada container, sem containers auxiliares adicionais.

### Versões de imagens

| Serviço | Imagem |
|---|---|
| `localstack` | `localstack/localstack:4.14.0` |
| `postgres` | `postgres:17.4` |
| `lambda-authorize` | build local |

### `localstack` — init script interno

O LocalStack suporta scripts de inicialização via volume montado em `/etc/localstack/init/ready.d/`. Quando o container estiver pronto (`healthy`), o script é executado automaticamente — sem container auxiliar `aws-cli`.

**`scripts/localstack-init.sh`** — montado como `/etc/localstack/init/ready.d/01_init.sh`:

```bash
awslocal secretsmanager create-secret \
  --name /lambda-authorize/pepper \
  --secret-string "dev-pepper-DO-NOT-USE-IN-PRODUCTION"

awslocal secretsmanager create-secret \
  --name /lambda-authorize/private-key \
  --secret-string "$(cat /certs/private.pem)"

awslocal secretsmanager create-secret \
  --name /lambda-authorize/public-key \
  --secret-string "$(cat /certs/public.pem)"

awslocal secretsmanager create-secret \
  --name /lambda-authorize/db-password \
  --secret-string "lambda"
```

O diretório `certs/` é montado no container LocalStack somente para leitura.

### `postgres` — init automático via `initdb.d/`

Os arquivos de migration são montados em `/docker-entrypoint-initdb.d/`:
- `migrations/01_schema.sql` → cria a tabela `users` (com coluna `roles TEXT[]`)
- `migrations/02_seed.sql` → insere 3 usuários com hashes pré-calculados

O PostgreSQL executa esses scripts automaticamente na primeira vez que o volume de dados é criado, sem necessidade de container separado.

### `localstack` — serviços habilitados

```yaml
SERVICES: secretsmanager
```

PostgreSQL roda como container nativo (não emulado pelo LocalStack), o que garante máxima fidelidade sem dependência de licença Pro.

---

## Terraform — infraestrutura AWS

### Região padrão: `sa-east-1` (São Paulo)

### Módulos

#### `modules/networking`
- VPC com CIDR `/16`
- 2 subnets privadas (Lambda + Aurora) em AZs distintas (`sa-east-1a`, `sa-east-1b`)
- **VPC Endpoint** para `secretsmanager` (evita NAT Gateway para acesso ao SM — economia de ~$45/mês)
- Security groups: `sg-lambda`, `sg-aurora`

> NAT Gateway removido. A Lambda acessa o Secrets Manager via VPC Endpoint (interface endpoint, ~$9/mês) e o Aurora dentro da própria VPC. Não há necessidade de acesso à internet.

#### `modules/secrets`
Quatro secrets no Secrets Manager:
1. `/lambda-authorize/db-password` — gerado pelo Terraform via `random_password`
2. `/lambda-authorize/pepper` — fornecido como variável sensível (`var.pepper`)
3. `/lambda-authorize/private-key` — fornecido como variável sensível (`var.private_key_pem`)
4. `/lambda-authorize/public-key` — fornecido como variável sensível (`var.public_key_pem`)

#### `modules/rds`
Provisiona um cluster **Aurora PostgreSQL** (compatível com PostgreSQL 16):

- Engine: `aurora-postgresql`, versão `16.x` (latest disponível na região)
- Tipo: cluster Aurora com 1 instância writer (`db.t3.medium` — menor classe suportada pelo Aurora)
- Multi-AZ: não habilitado por padrão (apenas 1 instância writer)
- Subnet group nas subnets privadas (mínimo 2 AZs exigido pelo Aurora)
- Security group que permite entrada apenas de `sg-lambda` na porta 5432
- Credenciais do master user lidas do módulo `secrets`
- **Inicialização manual**: o Terraform provisiona apenas o cluster. O developer executa `01_schema.sql` e `02_seed.sql` manualmente via `psql` após o provisionamento (ver seção "Como fazer o deploy")
- **Parâmetros IAM auth**: desabilitado — autenticação via senha (gerenciada pelo Secrets Manager)

> Aurora não suporta `db.t3.micro`. A menor instância disponível é `db.t3.medium` (~$56/mês). Para custo mínimo em produção com tráfego baixo, considere **Aurora Serverless v2** com `min_capacity=0.5, max_capacity=1.0` ACUs (~$43/mês quando ocioso, mas sem cold start severo).

#### `modules/lambda`
- Função Lambda (ZIP: `src/` + dependências — sem arquivos de cert)
- IAM role com políticas:
  - `AWSLambdaVPCAccessExecutionRole`
  - `secretsmanager:GetSecretValue` nos 4 secrets acima
- VPC config: subnets privadas, `sg-lambda`
- Variáveis de ambiente injetadas via `environment { variables = { ... } }`

### `variables.tf`

| Variável | Tipo | Default | Descrição |
|---|---|---|---|
| `aws_region` | `string` | `sa-east-1` | Região AWS |
| `environment` | `string` | — | Ex: `production`, `staging` |
| `pepper` | `string` (sensitive) | — | Pepper para hash de senhas |
| `private_key_pem` | `string` (sensitive) | — | PEM da chave privada RSA |
| `public_key_pem` | `string` (sensitive) | — | PEM da chave pública RSA |
| `jwks_kid` | `string` | `prod-key-1` | Key ID do JWKS |
| `aurora_min_capacity` | `number` | `0.5` | ACUs mínimos (Serverless v2) |
| `aurora_max_capacity` | `number` | `1.0` | ACUs máximos (Serverless v2) |
| `lambda_zip_path` | `string` | — | Caminho para o ZIP da Lambda |

---

## GitHub Actions — workflows

### `.github/workflows/build.yml` — todas as branches

**Trigger**: `push` e `pull_request` em qualquer branch

**Steps:**
1. `actions/checkout@v4`
2. `actions/setup-python@v5` (Python 3.13)
3. `pip install -r requirements.txt`
4. Empacotar Lambda: `pip install -r requirements.txt -t package/ && zip -r lambda.zip src/ package/`
5. Upload do artefato ZIP (`actions/upload-artifact@v4`)

---

### `.github/workflows/test.yml` — todas as branches

**Trigger**: `push` e `pull_request` em qualquer branch

**Steps:**
1. `actions/checkout@v4`
2. `actions/setup-python@v5` (Python 3.13)
3. `pip install -r requirements.txt -r requirements-dev.txt`
4. `pytest tests/unit/ -v --tb=short`

---

### `.github/workflows/deploy.yml` — apenas branch `main`, acionamento manual

**Trigger**: `workflow_dispatch` (manual) — disponível somente quando a branch alvo é `main`

```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Ambiente de deploy'
        required: true
        default: 'production'
        type: choice
        options: [production, staging]
      aws_region:
        description: 'Região AWS'
        required: true
        default: 'sa-east-1'
```

**Proteção de branch**: configurar no GitHub que `workflow_dispatch` só pode ser acionado na branch `main`.

**Secrets necessários no repositório GitHub:**

| Secret | Descrição |
|---|---|
| `AWS_ACCESS_KEY_ID` | Credencial IAM para deploy |
| `AWS_SECRET_ACCESS_KEY` | Credencial IAM para deploy |
| `TF_VAR_PEPPER` | Valor do pepper de produção |
| `TF_VAR_PRIVATE_KEY_PEM` | PEM da chave privada RSA |
| `TF_VAR_PUBLIC_KEY_PEM` | PEM da chave pública RSA |
| `TF_VAR_JWKS_KID` | Key ID do JWKS para produção |

**Steps:**
1. `actions/checkout@v4`
2. `actions/setup-python@v5`
3. `hashicorp/setup-terraform@v3`
4. Download do artefato ZIP gerado pelo workflow `build` (via `actions/download-artifact@v4`)
5. `aws-actions/configure-aws-credentials@v4`
6. `terraform init` (backend S3)
7. `terraform plan` — salvo como artefato
8. `terraform apply -auto-approve`

---

## Estimativa de custos AWS — `sa-east-1`

Cenário: **2 requisições/dia em média** (~60 req/mês)

### Opção A — Aurora Serverless v2 (recomendado)

| Serviço | Detalhamento | Custo/mês |
|---|---|---|
| **Lambda** | 60 req/mês, ~500ms, 256MB → dentro do free tier (1M req + 400k GB-s) | **$0,00** |
| **Aurora Serverless v2** | 0,5 ACU min, 20GB storage — $0,12/ACU-h × ~360h ativo + $0,14/ACU-h idle | **~$25–35** |
| **Secrets Manager** | 4 secrets × $0,40 + chamadas da API (desprezível) | **~$1,60** |
| **VPC Endpoint (SM)** | Interface endpoint: ~$0,013/h × 720h + dados | **~$9,50** |
| **CloudWatch Logs** | Logs da Lambda, volume mínimo | **~$0,05** |
| **Total estimado** | | **~$36–46/mês** |

### Opção B — Aurora Serverless v2 com `min_capacity=0` (pausa completa)

> Aurora Serverless v2 suporta `min_capacity=0` a partir de agosto 2024, permitindo pausa após inatividade configurável.

| Serviço | Detalhamento | Custo/mês |
|---|---|---|
| **Aurora Serverless v2** | Pausado quase todo o tempo (2 req/dia): ~0 ACU-h + 20GB storage $0,11/GB | **~$3–5** |
| Demais (Lambda, SM, VPC Endpoint, Logs) | Igual acima | **~$11,15** |
| **Total estimado** | | **~$14–16/mês** |

> Cold start da Aurora ao acordar de pausa completa: **15–60 segundos**. Aceitável para tráfego de artigo/demo.

**Recomendação**: usar Aurora Serverless v2 com `min_capacity=0` e `seconds_until_auto_pause=300` para minimizar custo enquanto mantendo escalabilidade zero-to-many.

---

## Discussão: Aurora Serverless v1 vs v2 vs Provisioned

| Opção | PostgreSQL | Min custo | Cold start | Status |
|---|---|---|---|---|
| **Aurora Serverless v1** | PostgreSQL 11 apenas | ~$2/mês (só storage quando pausado) | 15–30s | Descontinuado para novos clusters |
| **Aurora Serverless v2** | PostgreSQL 13–16 | ~$3/mês (com `min_capacity=0`) | 15–60s (pausa) / 0 (≥0,5 ACU) | Ativo — **opção escolhida** |
| **Aurora Provisioned** | PostgreSQL 13–16 | ~$56/mês (`db.t3.medium`, sempre ligado) | Nenhum | Ativo |
| **RDS PostgreSQL** | 13–17 | ~$12–18/mês | 1–2 min (stop/start) | Ativo |

---

## Notas de segurança

- O pepper e as chaves RSA **nunca** são commitados no repositório. Em produção, são passados como GitHub secrets (`TF_VAR_PEPPER`, `TF_VAR_PRIVATE_KEY_PEM`, `TF_VAR_PUBLIC_KEY_PEM`).
- As credenciais AWS para deploy existem apenas como GitHub secrets.
- O banco Aurora fica em subnet privada, sem acesso público.
- A Lambda acessa o Aurora via VPC (sem tráfego pela internet) e o Secrets Manager via VPC Endpoint.
- Argon2id é o algoritmo recomendado pela OWASP para hashing de senhas (resistente a ataques de GPU e side-channel).
- O salt está embutido no hash Argon2id — não precisa de coluna separada.
- Os certificados não são incluídos no pacote ZIP da Lambda — são lidos do Secrets Manager em runtime.
- O endpoint `GET /.well-known/jwks.json` exige Bearer token válido — apenas usuários autenticados podem obter a chave pública.

---

## Como fazer o deploy

### Pré-requisitos

- [ ] AWS CLI configurado com credenciais de deploy (`aws sts get-caller-identity` retorna sem erro)
- [ ] Terraform >= 1.6 instalado (`terraform version`)
- [ ] Python 3.13 instalado (`python3 --version`)
- [ ] OpenSSL instalado (`openssl version`)
- [ ] Bucket S3 criado para o backend Terraform (ex: `lambda-authorize-tfstate-<account-id>`)

---

### Passo 1 — Gerar os certificados RSA

```bash
mkdir -p certs
openssl genrsa -out certs/private.pem 2048
openssl rsa -in certs/private.pem -pubout -out certs/public.pem
```

Adicione `certs/` ao `.gitignore` (se ainda não estiver lá):

```
certs/
```

---

### Passo 2 — (Opcional) Testar localmente com Docker Compose

```bash
docker compose up --build
```

O Docker Compose irá:
1. Subir o LocalStack (secrets criados automaticamente pelo init script)
2. Subir o PostgreSQL (schema + seed executados automaticamente)
3. Subir a Lambda após ambos estarem saudáveis

Testar o login:
```bash
curl -X POST http://localhost:8080/2015-03-31/functions/function/invocations \
  -H 'Content-Type: application/json' \
  -d '{"rawPath": "/login", "requestContext": {"http": {"method": "POST"}}, "body": "{\"email\": \"william_cesar_santos@hotmail.com\", \"password\": \"lambda_123_AUTHORIZE\"}"}'
```

---

### Passo 3 — Empacotar a Lambda

```bash
pip install -r requirements.txt -t package/
cd package && zip -r ../lambda.zip . && cd ..
zip -r lambda.zip src/
```

---

### Passo 4 — Inicializar o Terraform

```bash
cd terraform

terraform init \
  -backend-config="bucket=lambda-authorize-tfstate-<account-id>" \
  -backend-config="key=lambda-authorize/terraform.tfstate" \
  -backend-config="region=sa-east-1"
```

---

### Passo 5 — Aplicar a infraestrutura

```bash
terraform apply \
  -var 'environment=production' \
  -var 'pepper=<SEU_PEPPER_PRODUCAO>' \
  -var "private_key_pem=$(cat ../certs/private.pem)" \
  -var "public_key_pem=$(cat ../certs/public.pem)" \
  -var 'jwks_kid=prod-key-1' \
  -var "lambda_zip_path=$(pwd)/../lambda.zip"
```

> **Nunca coloque o pepper ou os PEMs no código-fonte ou no histórico do shell.** Em produção, use GitHub secrets ou um vault.

O Terraform irá criar:
- VPC, subnets, security groups, VPC Endpoint
- 4 secrets no Secrets Manager
- Cluster Aurora Serverless v2
- Função Lambda com IAM role e env vars

---

### Passo 6 — Inicializar o banco de dados (Aurora — manual)

Após o `terraform apply`, obtenha o endpoint do cluster Aurora:

```bash
terraform output aurora_cluster_endpoint
```

Conecte via `psql` de dentro da VPC (ou via AWS Systems Manager Session Manager + bastion, ou temporariamente via IP público com security group ajustado):

```bash
psql -h <aurora-endpoint> -U lambda -d lambdaauth \
  -f ../migrations/01_schema.sql \
  -f ../migrations/02_seed.sql
```

> **Importante**: o seed contém hashes calculados com o pepper de desenvolvimento. Para produção, recalcule os hashes com o pepper real antes de executar `02_seed.sql`.

Gerar o hash de produção para cada usuário:

```python
from argon2 import PasswordHasher
ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)
pepper = "<SEU_PEPPER_PRODUCAO>"
print(ph.hash("lambda_123_AUTHORIZE" + pepper))
```

---

### Passo 7 — Configurar secrets do GitHub (para CI/CD)

No repositório GitHub → Settings → Secrets and variables → Actions:

| Secret | Valor |
|---|---|
| `AWS_ACCESS_KEY_ID` | Access key do IAM user de deploy |
| `AWS_SECRET_ACCESS_KEY` | Secret key do IAM user de deploy |
| `TF_VAR_PEPPER` | Pepper de produção |
| `TF_VAR_PRIVATE_KEY_PEM` | Conteúdo de `certs/private.pem` |
| `TF_VAR_PUBLIC_KEY_PEM` | Conteúdo de `certs/public.pem` |
| `TF_VAR_JWKS_KID` | Ex: `prod-key-1` |

---

### Passo 8 — Deploy via GitHub Actions (após setup inicial)

1. Acesse a aba **Actions** no repositório GitHub
2. Selecione o workflow **Deploy to AWS**
3. Clique em **Run workflow**
4. Selecione a branch `main`, escolha o ambiente (`production`) e confirme

O workflow irá:
- Baixar o artefato ZIP do último build bem-sucedido
- Executar `terraform plan` e `terraform apply` com os secrets injetados automaticamente
