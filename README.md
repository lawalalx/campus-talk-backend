# LagTALK Microblogging Platform - Backend

A production-ready, modular FastAPI backend for the LagTALK platform—a campus-focused microblogging and community platform. This backend provides comprehensive authentication, real-time notifications, media management, and observability features.

---

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Installation & Setup](#installation--setup)
- [Environment Configuration](#environment-configuration)
- [Running the Application](#running-the-application)
- [Database Management](#database-management)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Observability](#observability)
- [Development Workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## 🎯 Project Overview

**LagTALK** is a campus-based microblogging platform similar to X/Twitter but tailored for educational institutions. It enables:

- **Students** to create posts, share content, and engage with campus communities
- **Institutions** to manage official channels and communicate with students
- **Communities** for interest-based groups (clubs, departments, events)
- **Notifications** for real-time updates on interactions
- **Media management** with direct S3 uploads
- **Admin tools** for moderation and platform management

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|-----------|
| **Framework** | FastAPI (Python 3.11+) |
| **Database** | PostgreSQL 15 with Async SQLAlchemy |
| **ORM** | SQLModel |
| **Authentication** | JWT + Role-Based Access Control (RBAC) |
| **Media Storage** | MinIO (S3-compatible) |
| **Caching** | Redis |
| **Monitoring** | Prometheus + Grafana |
| **Containerization** | Docker & Docker Compose |
| **Task Queue** | Background tasks via FastAPI |
| **Email** | FastAPI-Mail + Resend |
| **AI/LLM** | LangChain (Groq, Tavily) |
| **Testing** | pytest + httpx |

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── routers/           # API endpoints (auth, users, posts, etc.)
│   │   └── deps.py            # Dependency injection
│   ├── core/
│   │   ├── auth.py            # Authentication & JWT logic
│   │   ├── config.py          # Settings & environment variables
│   │   ├── manager.py         # Application state manager
│   │   ├── middleware.py      # CORS and custom middleware
│   │   └── cloudinary.py      # Media service integration
│   ├── db/
│   │   ├── models.py          # SQLModel database models
│   │   ├── repositories/      # Repository pattern implementations
│   │   └── session.py         # Database session management
│   ├── schemas/               # Pydantic request/response schemas
│   ├── services/              # Business logic layer
│   ├── tasks/                 # Background tasks
│   ├── utils/                 # Utility functions (cache, helpers)
│   ├── chatbot/               # Chatbot/AI features
│   ├── errors.py              # Custom exception classes
│   └── main.py                # Application entry point
├── migrations/                # Alembic database migrations
├── tests/                     # pytest test suite
├── scripts/                   # Utility scripts (seeding, etc.)
├── seeds/                     # Database seed data
├── prometheus/                # Prometheus configuration
├── grafana/                   # Grafana dashboards & provisioning
├── docker-compose.yml         # Docker Compose configuration
├── Dockerfile                 # Docker build configuration
├── requirements.txt           # Python dependencies
├── pytest.ini                 # pytest configuration
├── alembic.ini                # Alembic configuration
├── .env.example               # Environment variables template
└── README.md                  # This file
```

### Key Modules

- **routers/**: Modular API endpoints organized by feature (auth, users, posts, channels, communities, etc.)
- **repositories/**: Data access layer implementing the repository pattern
- **services/**: Business logic for complex operations
- **schemas/**: Pydantic models for request validation and response serialization

---

## 📋 Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **PostgreSQL 15+** (if running locally without Docker)
- **Docker & Docker Compose** ([Download Docker Desktop](https://www.docker.com/products/docker-desktop))
- **Git**
- **A terminal/command prompt**

### Optional
- **Redis** (for caching, if not using Docker)
- **MinIO** (for local S3-compatible storage, if not using Docker)

---

## 🚀 Quick Start

### Option 1: Docker (Recommended for beginners)

```bash
# Clone the repository
git clone <repository-url>
cd campus-tok-app/backend

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up --build

# The API will be available at http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# Clone the repository
git clone <repository-url>
cd campus-tok-app/backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file and configure it
cp .env.example .env

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --port 8000
```

---

## 🔧 Installation & Setup

### Step 1: Clone the Repository

```bash
git clone <your-repository-url>
cd campus-tok-app/backend
```

### Step 2: Environment Configuration

See [Environment Configuration](#environment-configuration) section below.

### Step 3: Database Setup

#### Using Docker Compose:
```bash
docker-compose up -d postgres
```

#### Local PostgreSQL:
```bash
# Ensure PostgreSQL is running, then create the database
createdb lagtalk
```

### Step 4: Install Dependencies

#### Docker:
Dependencies are installed during the `docker-compose up --build` process.

#### Local:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## 🔐 Environment Configuration

### Setup Instructions

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Generate a secure SECRET_KEY:**
   ```bash
   # macOS/Linux:
   openssl rand -hex 32
   
   # Windows (PowerShell):
   [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes(32) | ForEach-Object { "{0:x2}" -f $_ } | Join-String
   ```

3. **Update `.env` with your values** (see below for descriptions)

### Environment Variables Reference

```env
# Application
PROJECT_NAME="LagTALK API"
API_V1_STR="/api/v1"
SECRET_KEY=<generate-new>           # Use openssl rand -hex 32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440    # 24 hours

# Database
POSTGRES_SERVER=localhost            # 'postgres' in Docker
POSTGRES_USER=lagtalk
POSTGRES_PASSWORD=lagtalk_password
POSTGRES_DB=lagtalk
DATABASE_URL=postgresql+asyncpg://lagtalk:lagtalk_password@localhost:5432/lagtalk

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# MinIO (S3)
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
S3_ENDPOINT_URL=http://minio:9000   # 'http://localhost:9000' locally
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET_NAME=lagtalk-media

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_URL=redis://redis:6379/0

# Grafana
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=grafana

# Cloudinary (optional, for media)
CLOUDINARY_CLOUD_NAME=<your-cloud-name>
CLOUDINARY_API_KEY=<your-api-key>
CLOUDINARY_API_SECRET=<your-api-secret>

# Email (Resend)
RESEND_API_KEY=<your-resend-key>
SENDER_EMAIL=noreply@lagtalk.com

# LLM/AI (optional)
GROQ_API_KEY=<your-groq-key>
TAVILY_API_KEY=<your-tavily-key>
```

### Environment-Specific Configurations

**Development (.env for local):**
```env
SECRET_KEY=your_dev_secret_here
POSTGRES_SERVER=localhost
S3_ENDPOINT_URL=http://localhost:9000
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
```

**Docker (.env for docker-compose):**
```env
POSTGRES_SERVER=postgres      # Service name in docker-compose
S3_ENDPOINT_URL=http://minio:9000
REDIS_HOST=redis
```

---

## ▶️ Running the Application

### Using Docker Compose (Recommended)

```bash
# Start all services (backend, database, MinIO, Redis, Prometheus, Grafana)
docker-compose up --build

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Rebuild a specific service
docker-compose up -d --build backend
```

### Local Development (Without Docker)

```bash
# Activate virtual environment
source venv/bin/activate  # Windows: venv\Scripts\activate

# Ensure PostgreSQL is running, then start the server
uvicorn app.main:app --reload --port 8000

# The API will be available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| **FastAPI Docs** | http://localhost:8000/docs | None |
| **FastAPI ReDoc** | http://localhost:8000/redoc | None |
| **MinIO Console** | http://localhost:9001 | minioadmin/minioadmin |
| **Prometheus** | http://localhost:9090 | None |
| **Grafana** | http://localhost:3000 | admin/grafana |
| **PostgreSQL** | localhost:5432 | lagtalk/lagtalk_password |
| **Redis** | localhost:6379 | None |

---

## 🗄️ Database Management

### Create Database (First Time)

```bash
# Docker automatically handles this
docker-compose up -d postgres

# Local PostgreSQL
createdb lagtalk
```

### Initialize Schema

The application automatically creates tables on startup via `create_tables()` in `app/db/session.py`.

### Migrations

We use **Alembic** for database schema versioning.

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations (upgrade)
alembic upgrade head

# Rollback to previous version
alembic downgrade -1

# View migration history
alembic history

# Current migration version
alembic current
```

### Seed Database

```bash
# Run seed script
python scripts/run_seeds.py

# Or manually execute seeds
cd scripts && python run_seeds.py
```

### Reset Database (Development Only)

```bash
# Drop all tables and recreate them
# WARNING: This deletes all data!
docker-compose down -v
docker-compose up --build
```

---

## 📚 API Documentation

### Interactive API Docs

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key API Endpoints

All endpoints are prefixed with `/api/v1`:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/register` | POST | User registration |
| `/auth/login` | POST | User login (returns JWT token) |
| `/auth/token/refresh` | POST | Refresh access token |
| `/users/{user_id}` | GET | Get user profile |
| `/users/{user_id}` | PUT | Update user profile |
| `/posts` | GET | List posts (with pagination) |
| `/posts` | POST | Create a new post |
| `/posts/{post_id}` | GET | Get post details |
| `/posts/{post_id}` | DELETE | Delete post (author only) |
| `/posts/{post_id}/comments` | GET | List comments on post |
| `/posts/{post_id}/comments` | POST | Create comment |
| `/channels` | GET | List channels |
| `/channels` | POST | Create channel |
| `/communities` | GET | List communities |
| `/notifications` | GET | Get user notifications |
| `/admin/*` | * | Admin endpoints (admin-only) |

### Authentication

Most endpoints require JWT authentication. Include the token in the `Authorization` header:

```bash
curl -H "Authorization: Bearer <your_token>" http://localhost:8000/api/v1/users/me
```

### Response Format

All responses follow a consistent format:

```json
{
  "data": { /* response data */ },
  "success": true,
  "message": "Operation successful"
}
```

---

## ✅ Testing

### Run All Tests

```bash
# Using pytest directly
pytest

# With verbose output
pytest -v

# Run specific test file
pytest tests/api/test_auth.py

# Run with coverage
pytest --cov=app --cov-report=html
```

### Test Structure

```
tests/
├── api/                  # Endpoint tests
├── conftest.py          # Shared fixtures and configuration
└── test_rag_import.py   # Additional tests
```

### Example Test

```python
# tests/api/test_auth.py
async def test_register(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "secure_password",
            "full_name": "Test User"
        }
    )
    assert response.status_code == 201
```

### Fixtures

Common test fixtures are defined in `tests/conftest.py`:
- `client`: Test HTTP client
- `db_session`: Database session for tests
- `test_user`: Pre-created test user

---

## 📊 Observability

### Prometheus

Metrics are automatically collected by the `prometheus-fastapi-instrumentator` library.

**Access**: http://localhost:9090

**Key Metrics**:
- Request count and latency
- Error rates
- Database query performance
- Custom application metrics

**Basic Queries**:
```promql
# Average request latency
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Request rate
rate(http_requests_total[5m])
```

### Grafana

Dashboards visualize Prometheus metrics.

**Access**: http://localhost:3000  
**Default Credentials**: admin/grafana

**Pre-configured Dashboards**:
- FastAPI Metrics
- Database Performance
- Error Tracking
- System Resources

**Setup**:
1. Log in to Grafana
2. Add Prometheus as a data source (if not already added)
3. Import dashboards from `grafana/provisioning/dashboards/`

---

## 🔨 Development Workflow

### Local Development Setup

1. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your local values
   ```

4. **Start PostgreSQL** (if not using Docker):
   ```bash
   # macOS: brew services start postgresql
   # Linux: sudo systemctl start postgresql
   # Windows: Use PostgreSQL installer to start service
   ```

5. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

6. **Start the development server**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Code Organization Best Practices

- **Routers**: Define API endpoints in `app/api/routers/`
- **Services**: Implement business logic in `app/services/`
- **Repositories**: Data access layer in `app/db/repositories/`
- **Schemas**: Request/response models in `app/schemas/`
- **Models**: Database models in `app/db/models.py`

### Adding a New Feature

1. Create repository methods (if needed) in `app/db/repositories/`
2. Implement service logic in `app/services/`
3. Create Pydantic schemas in `app/schemas/`
4. Define API endpoints in `app/api/routers/`
5. Write tests in `tests/api/`
6. Create migration (if database changes): `alembic revision --autogenerate -m "feature"`

### Code Style

- Use **type hints** for all functions
- Follow **PEP 8** style guide
- Use **async/await** for I/O operations
- Include docstrings for complex functions
- Keep functions small and focused

---

## 🐛 Troubleshooting

### Docker Compose Issues

**Problem**: Container won't start
```bash
# Check logs
docker-compose logs backend

# Rebuild
docker-compose down -v
docker-compose up --build
```

**Problem**: Port already in use
```bash
# Change port in docker-compose.yml or kill existing process
# Windows: netstat -ano | findstr :8000
# macOS/Linux: lsof -i :8000
```

### Database Connection Issues

**Problem**: "Connection refused" for PostgreSQL
```bash
# Ensure service is running
docker-compose ps

# Check if service is healthy
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

**Problem**: Migration errors
```bash
# Reset migrations (development only!)
alembic stamp base
alembic upgrade head
```

### Authentication Issues

**Problem**: "Invalid token" errors
```bash
# Generate a new SECRET_KEY
openssl rand -hex 32

# Update .env and restart
docker-compose restart backend
```

### Redis Connection Issues

**Problem**: Redis connection refused
```bash
# Start Redis service
docker-compose up -d redis

# Verify connection
redis-cli ping
```

### Missing Environment Variables

**Problem**: `KeyError` or `AttributeError` on startup
```bash
# Verify .env exists
ls -la .env

# Check for missing required variables
cp .env.example .env.check
# Compare with your .env file
```

---

## 🤝 Contributing

### Before You Start

1. Create a new branch for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Follow the code organization patterns (see [Development Workflow](#development-workflow))

3. Add tests for new functionality

4. Ensure tests pass:
   ```bash
   pytest
   ```

### Commit Guidelines

- Use clear, descriptive commit messages
- Reference issue numbers when applicable
- Example: `feat: add user follow feature (#123)`

### Pull Request Process

1. Update `CHANGELOG.md` if applicable
2. Ensure all tests pass
3. Update documentation if needed
4. Request review from team members

---

## 📞 Getting Help

- **Documentation**: See API docs at http://localhost:8000/docs
- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions
- **Slack**: Join the development channel

---

## 📄 License

[Your License Here]

---

## 📝 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Async Guide](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic Migrations](https://alembic.sqlalchemy.org/)
- [JWT Authentication](https://jwt.io/)
- [Docker Compose Guide](https://docs.docker.com/compose/)

---

**Happy coding! 🚀**

Click on "Buckets" and create a new bucket named lagtalk-media (or whatever you set S3_BUCKET_NAME to).

4. Database Migrations with Alembic
To run database migrations, you need to execute the alembic command inside the running backend container.

Generate a new migration (after changing models.py):

Bash

docker-compose exec backend alembic revision --autogenerate -m "Your migration message"
Apply migrations:

Bash

docker-compose exec backend alembic upgrade head
Running Tests
To run the test suite:

Bash

docker-compose exec backend pytest
Grafana Setup
The included docker-compose.yml automatically provisions Grafana.

Navigate to http://localhost:3000.

Login with the credentials from your .env file (GF_SECURITY_ADMIN_USER/GF_SECURITY_ADMIN_PASSWORD).

The Prometheus data source and the "LagTALK API Performance" dashboard will be pre-configured and available.

The dashboard visualizes:

Requests per second by endpoint.

95th percentile request latency.

Distribution of HTTP status codes
