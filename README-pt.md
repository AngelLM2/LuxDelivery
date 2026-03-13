# Lux Delivery API

**API REST completa para gerenciamento de delivery - pedidos, clientes e administracao**

Python  
FastAPI  
PostgreSQL  
Redis  
Docker

**Documentacao Swagger ->** https://luxdelivery-production.up.railway.app/docs

# Sobre o Projeto

A **Lux Delivery API** e uma API REST construida com **FastAPI** que simula o backend completo de uma plataforma de delivery. O projeto foi desenvolvido para aprofundar conhecimentos em autenticacao segura, relacionamentos entre entidades, cache, rate limiting e containerizacao.

# Destaques tecnicos

- **Autenticacao JWT** com access token + refresh token rotativo (deteccao de reutilizacao)
- **2 roles** com permissoes distintas: `admin` e `customer`
- **Rate limiting global** com Redis (sliding window) - por IP e usuario autenticado
- **Rate limiting extra** nas rotas de auth (login/refresh/bootstrap)
- **Cache** com Redis nas rotas de produtos e categorias - reducao de queries ao banco
- **Rastreamento de pedidos** com historico completo de status e timestamps
- **Sistema de notificacoes** por evento (criacao, atualizacao de status)
- **Analytics** de pedidos por periodo para administradores
- **Deploy containerizado** com Docker multi-stage build e usuario nao-root

---

## Stack

| Tecnologia | Uso |
| **FastAPI** | Framework web assincrono |
| **PostgreSQL 16** | Banco de dados principal |
| **Redis 7** | Cache e rate limiting |
| **SQLAlchemy 2** | ORM async |
| **Alembic** | Migrations de banco |
| **Pydantic V2** | Validacao de dados |
| **python-jose** | Geracao e validacao de JWT |
| **Docker + Compose** | Containerizacao e orquestracao |

---

# Autenticacao

O sistema usa dois tokens JWT:

- **Access token** - curta duracao (30 min), enviado no header `Authorization: Bearer`
- **Refresh token** - longa duracao (7 dias), rotativo com deteccao de reutilizacao

Se um refresh token ja usado for apresentado novamente, a requisicao e rejeitada (401). O refresh token anterior e revogado na rotacao.

---

# Endpoints

# Auth
| Metodo | Rota | Descricao | Auth |
| `POST` | `/auth/register` | Cadastro de usuario | Publico |
| `POST` | `/auth/login` | Login - retorna token pair | Publico |
| `POST` | `/auth/token` | OAuth2 login (password grant) | Publico |
| `POST` | `/auth/refresh` | Renova tokens | Publico |
| `GET` | `/auth/me` | Dados do usuario autenticado | Autenticado |
| `POST` | `/auth/bootstrap-admin` | Cria o primeiro admin | Token especial |

# Usuarios
| Metodo | Rota | Descricao | Auth |
| `GET` | `/users/` | Lista todos os usuarios | Admin |
| `POST` | `/users/` | Cria usuario com role | Admin |
| `GET` | `/users/me` | Perfil do usuario atual | Autenticado |
| `PATCH` | `/users/me` | Atualiza nome, telefone ou senha | Autenticado |
| `PATCH` | `/users/{id}/deactivate` | Desativa usuario | Admin |

# Produtos
| Metodo | Rota | Descricao | Auth |
| `GET` | `/products/` | Lista produtos (paginacao por cursor) | Autenticado |
| `POST` | `/products/` | Cria produto | Admin |
| `PATCH` | `/products/{id}` | Atualiza produto | Admin |
| `DELETE` | `/products/{id}` | Remove produto | Admin |

# Categorias
| Metodo | Rota | Descricao | Auth |
| `GET` | `/categories/` | Lista categorias (cached) | Publico |
| `POST` | `/categories/post` | Cria categoria | Admin |
| `PATCH` | `/categories/patch/{id}` | Atualiza categoria | Admin |
| `DELETE` | `/categories/delete/{id}` | Remove categoria | Admin |

# Pedidos
| Metodo | Rota | Descricao | Auth |
| `POST` | `/orders/` | Cria pedido | Customer/Admin |
| `GET` | `/orders/` | Lista pedidos do usuario | Autenticado |
| `GET` | `/orders/{id}` | Detalhes do pedido | Autenticado |
| `PATCH` | `/orders/{id}/status` | Atualiza status (admin total, customer cancela) | Autenticado |
| `GET` | `/orders/{id}/tracking` | Historico de rastreamento | Autenticado |

# Notificacoes
| Metodo | Rota | Descricao | Auth |
| `GET` | `/notifications/` | Lista notificacoes do usuario | Autenticado |
| `PATCH` | `/notifications/{id}/read` | Marca como lida | Autenticado |

# Analytics
| Metodo | Rota | Descricao | Auth |
| `GET` | `/analytics/orders-progress` | Metricas de pedidos por periodo | Admin |

# Fluxo de Status do Pedido

CREATED -> CONFIRMED -> PREPARING -> OUT_FOR_DELIVERY -> DELIVERED
    v           v           v               v
 CANCELED    CANCELED    CANCELED        CANCELED

Cada transicao gera um evento de rastreamento e uma notificacao para o cliente.

# Arquitetura

app/
|-- auth/           # JWT, dependencias, rate limiting
|-- models/         # Models SQLAlchemy (User, Order, Product...)
|-- repositories/   # Camada de acesso ao banco
|-- services/       # Regras de negocio
|-- routers/        # Endpoints FastAPI
|-- schemas/        # Schemas Pydantic (input/output)
|-- core/           # Redis client, cache service
|-- config.py       # Settings via pydantic-settings
|-- database.py     # Engine e sessao async
`-- main.py         # App FastAPI, lifespan, routers

# Rodando com Docker

**Pre-requisitos:** Docker e Docker Compose instalados.

```bash
# 1. Clone o repositorio
git clone https://github.com/seu-usuario/lux-delivery.git
cd lux-delivery

# 2. Configure as variaveis de ambiente
cp .env.example .env
# Edite o .env com suas configuracoes

# 3. Suba os servicos
docker compose up --build -d

# 4. Rode as migrations
docker compose run --rm migrate

# 5. Acesse
# API:     http://localhost:8000
# Swagger: http://localhost:8000/docs
```

# Rodando Localmente (sem Docker)

```bash
# 1. Crie o ambiente virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 2. Instale as dependencias
pip install -r requirements.txt

# 3. Configure o .env
cp .env.example .env

# 4. Rode as migrations
alembic upgrade head

# 5. Inicie a API
uvicorn app.main:app --reload
```

> PostgreSQL e Redis precisam estar rodando localmente.

# Variaveis de Ambiente

Crie um `.env` baseado no `.env.example`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/lux_delivery
REDIS_URL=redis://:password@localhost:6379/0

POSTGRES_USER=user
POSTGRES_PASSWORD=strong_password
POSTGRES_DB=lux_delivery
REDIS_PASSWORD=strong_redis_password

SECRET_KEY=sua_chave_secreta_jwt
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

BOOTSTRAP_ADMIN_TOKEN=token_para_criar_primeiro_admin
AUTH_RATE_LIMIT_MAX_ATTEMPTS=10
AUTH_RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_MAX_PER_IP=120
RATE_LIMIT_MAX_PER_USER=300

PRODUCTS_MAX_PAGE_SIZE=100
ANALYTICS_MAX_RANGE_DAYS=93
```

---

# Seguranca

- Usuario nao-root no container Docker
- Multi-stage build (imagem final sem ferramentas de build)
- Redis protegido com senha
- Banco e Redis sem portas expostas ao host em producao
- Rate limiting global (IP + usuario) via Redis + limiter extra nas rotas de auth
- Refresh tokens com rotacao e deteccao de reutilizacao
- Senhas com bcrypt + validacao de forca (maiuscula, minuscula, numero, especial)
- Secrets via variaveis de ambiente - nunca em codigo ou imagem
- Lock de bootstrap admin valida PostgreSQL via AsyncSession.bind antes do advisory lock

# Licenca

Distribuido sob a licenca MIT. Veja [LICENSE](LICENSE) para mais informacoes.
