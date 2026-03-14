# Lux Delivery API

**Full-featured REST API for delivery management - orders, customers and administration**

Python  
FastAPI  
PostgreSQL  
Redis  
Docker

**Swagger Documentation ->** https://luxdelivery-production.up.railway.app/docs

# About the Project

The **Lux Delivery API** is a REST API built with **FastAPI** that simulates the complete backend of a delivery platform. The project was developed to deepen knowledge of secure authentication, entity relationships, caching, rate limiting and containerization.

# Technical Highlights

- **JWT authentication** with access token + rotating refresh token (reuse detection)
- **2 roles** with distinct permissions: `admin` and `customer`
- **Global rate limiting** with Redis (sliding window) - per IP and authenticated user
- **Extra auth rate limiting** on login/refresh/bootstrap routes
- **Redis cache** on product and category routes - reduces database queries
- **Order tracking** with full status history and timestamps
- **Notification system** per event (creation, status updates)
- **Order analytics** by period for administrators
- **Containerized deployment** with Docker multi-stage build and non-root user

---

## Stack

| Technology | Purpose |
| **FastAPI** | Async web framework |
| **PostgreSQL 16** | Main database |
| **Redis 7** | Cache and rate limiting |
| **SQLAlchemy 2** | Async ORM |
| **Alembic** | Database migrations |
| **Pydantic V2** | Data validation |
| **python-jose** | JWT generation and validation |
| **Docker + Compose** | Containerization and orchestration |

---

# Authentication

The system uses two JWT tokens:

- **Access token** - short-lived (30 min), sent via `Authorization: Bearer` header
- **Refresh token** - long-lived (7 days), rotated on every refresh with reuse detection

If a previously used refresh token is presented again, the request is rejected (401). The previous refresh token is revoked on rotation.

---

# Endpoints

# Auth
| Method | Route | Description | Auth |
| `POST` | `/auth/register` | Register new user | Public |
| `POST` | `/auth/login` | Login - returns token pair | Public |
| `POST` | `/auth/token` | OAuth2 login (password grant) | Public |
| `POST` | `/auth/refresh` | Rotate tokens | Public |
| `GET` | `/auth/me` | Authenticated user data | Authenticated |
| `POST` | `/auth/bootstrap-admin` | Create first admin | Bootstrap token |

# Users
| Method | Route | Description | Auth |
| `GET` | `/users/` | List all users | Admin |
| `POST` | `/users/` | Create user with role | Admin |
| `GET` | `/users/me` | Current user profile | Authenticated |
| `PATCH` | `/users/me` | Update name, phone or password | Authenticated |
| `PATCH` | `/users/{id}/deactivate` | Deactivate user | Admin |

# Products
| Method | Route | Description | Auth |
| `GET` | `/products/` | List products (cursor pagination) | Authenticated |
| `POST` | `/products/` | Create product | Admin |
| `PATCH` | `/products/{id}` | Update product | Admin |
| `DELETE` | `/products/{id}` | Delete product | Admin |

# Categories
| Method | Route | Description | Auth |
| `GET` | `/categories/` | List categories (cached) | Public |
| `POST` | `/categories/post` | Create category | Admin |
| `PATCH` | `/categories/patch/{id}` | Update category | Admin |
| `DELETE` | `/categories/delete/{id}` | Delete category | Admin |

# Orders
| Method | Route | Description | Auth |
| `POST` | `/orders/` | Create order | Customer/Admin |
| `GET` | `/orders/` | List user orders | Authenticated |
| `GET` | `/orders/{id}` | Order details | Authenticated |
| `PATCH` | `/orders/{id}/status` | Update order status (admin full, customer cancel) | Authenticated |
| `GET` | `/orders/{id}/tracking` | Tracking history | Authenticated |

# Notifications
| Method | Route | Description | Auth |
| `GET` | `/notifications/` | List user notifications | Authenticated |
| `PATCH` | `/notifications/{id}/read` | Mark as read | Authenticated |

# Analytics
| Method | Route | Description | Auth |
| `GET` | `/analytics/orders-progress` | Order metrics by period | Admin |

# Order Status Flow

CREATED -> CONFIRMED -> PREPARING -> OUT_FOR_DELIVERY -> DELIVERED
    v           v           v               v
 CANCELED    CANCELED    CANCELED        CANCELED

Each transition generates a tracking event and a notification for the customer.

# Architecture

app/
|-- auth/           # JWT, dependencies, rate limiting
|-- models/         # SQLAlchemy models (User, Order, Product...)
|-- repositories/   # Database access layer
|-- services/       # Business logic
|-- routers/        # FastAPI endpoints
|-- schemas/        # Pydantic schemas (input/output)
|-- core/           # Redis client, cache service
|-- config.py       # Settings via pydantic-settings
|-- database.py     # Async engine and session
`-- main.py         # FastAPI app, lifespan, routers

# Running with Docker

**Requirements:** Docker and Docker Compose installed.

```bash
# 1. Clone the repository
git clone https://github.com/your-username/lux-delivery.git
cd lux-delivery

# 2. Set up environment variables
cp .env.example .env
# Edit .env with your settings

# 3. Start all services
docker compose up --build -d

# 4. Run migrations
docker compose run --rm migrate

# 5. Access
# API:     http://localhost:8000
# Swagger: http://localhost:8000/docs
```

# Running Locally (without Docker)

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env

# 4. Run migrations
alembic upgrade head

# 5. Start the API
uvicorn app.main:app --reload
```

> PostgreSQL and Redis must be running locally.

# Environment Variables

Create a `.env` file based on `.env.example`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/lux_delivery
REDIS_URL=redis://:password@localhost:6379/0

POSTGRES_USER=user
POSTGRES_PASSWORD=strong_password
POSTGRES_DB=lux_delivery
REDIS_PASSWORD=strong_redis_password

SECRET_KEY=your_jwt_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

BOOTSTRAP_ADMIN_TOKEN=token_to_create_first_admin
AUTH_RATE_LIMIT_MAX_ATTEMPTS=10
AUTH_RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_MAX_PER_IP=120
RATE_LIMIT_MAX_PER_USER=300

PRODUCTS_MAX_PAGE_SIZE=100
ANALYTICS_MAX_RANGE_DAYS=93
```

---

# Security

- Non-root user inside Docker container
- Multi-stage build (final image has no build tools)
- Redis protected with password
- Database and Redis ports not exposed to host in production
- Global rate limiting (IP + user) via Redis + extra limiter on auth routes
- Refresh token rotation with reuse detection
- Passwords hashed with bcrypt + strength validation (uppercase, lowercase, number, special char)
- Secrets via environment variables - never in code or image
- Bootstrap admin lock checks PostgreSQL via AsyncSession.bind before advisory lock

# License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
