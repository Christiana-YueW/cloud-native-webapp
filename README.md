# CSYE 6225 - Cloud Native Web Application

**Student:** Yue Wu  
**Organization:** yuewu-cloud  
**Semester:** Spring 2026

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Node.js 18+ (for Newman)
- Git with SSH configured

## Technology Stack

- **Framework:** FastAPI 0.128.0
- **Database:** PostgreSQL with SQLAlchemy ORM
- **Authentication:** HTTP Basic Auth with BCrypt
- **Testing:** Postman/Newman

## Build Instructions

### 1. Clone Repository

```bash
git clone git@github.com:YOUR_USERNAME/webapp.git
cd webapp
```

### 2. Set Up Python Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Database

```bash
# Create database
createdb webapp_db

# Create .env file
echo 'DATABASE_URL=postgresql://YOUR_USERNAME@localhost:5432/webapp_db' > .env
```

Replace `YOUR_USERNAME` with your PostgreSQL username.

### 4. Run Application

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Application will be available at: http://127.0.0.1:8000

API Documentation: http://127.0.0.1:8000/docs

## API Endpoints

- `GET /healthz` - Health check
- `POST /v1/user` - Create user
- `GET /v1/user/self` - Get user info (requires auth)
- `PUT /v1/user/self` - Update user info (requires auth)

## Testing

### Install Newman

```bash
npm install -g newman
```

### Run Integration Tests Locally

**Start the application:**

```bash
# Terminal 1: Start application
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Run tests with Newman:**

```bash
# Terminal 2: Clean database and run tests
psql webapp_db -c "DELETE FROM users;"

newman run postman_collection.json \
  --env-var "test_user_username=test@example.com" \
  --env-var "test_user_password=TestPassword123!" \
  --env-var "test_user_new_password=NewPassword123!"
```

**Expected output:**

```
┌─────────────────────┬──────────┬─────────┐
│                     │ executed │  failed │
├─────────────────────┼──────────┼─────────┤
│          iterations │        1 │       0 │
│            requests │       19 │       0 │
│          assertions │       55 │       0 │
└─────────────────────┴──────────┴─────────┘
```

### CI/CD Testing

**GitHub Actions uses GitHub Secrets for test credentials.**

**Required Secrets** (configured in repository settings):

- `TEST_USER_USERNAME` - Test email for user creation
- `TEST_USER_PASSWORD` - Initial test password
- `TEST_USER_NEW_PASSWORD` - Password for update tests

**To configure secrets:**

1. Go to: `Settings` → `Secrets and variables` → `Actions`
2. Click `New repository secret`
3. Add each secret with appropriate values

**Workflow reference:** `.github/workflows/ci.yml` uses these secrets:

```yaml
env:
  TEST_USER_USERNAME: ${{ secrets.TEST_USER_USERNAME }}
  TEST_USER_PASSWORD: ${{ secrets.TEST_USER_PASSWORD }}
  TEST_USER_NEW_PASSWORD: ${{ secrets.TEST_USER_NEW_PASSWORD }}
```

### Test Coverage

- **19 API requests**
- **55 assertions**
- **Coverage:** Health Check (4), Create User (6), Get User (3), Update User (6)

## CI/CD

### GitHub Actions

Automated tests run on every pull request to `main` branch.

**Workflow:** `.github/workflows/ci.yml`

### Branch Protection

The `main` branch requires:
- Pull request before merging
- All CI tests to pass
- Branch to be up to date

## Project Structure

```
webapp/
├── app/                  # Application code
│   ├── main.py          # FastAPI app and routes
│   ├── models.py        # Database models
│   ├── schemas.py       # Pydantic schemas
│   ├── database.py      # Database config
│   └── auth.py          # Authentication
├── .github/workflows/   # CI/CD configuration
├── postman_collection.json           # Tests
├── postman_environment.template.json # Template
├── requirements.txt     # Dependencies
└── .env                 # Local config (not committed)
```

## Environment Configuration

### Development (.env file)

```env
DATABASE_URL=postgresql://username@localhost:5432/webapp_db
```

### Testing (environment variables)

- `test_user_username` - Test email
- `test_user_password` - Test password
- `test_user_new_password` - Updated password for tests

## Notes

- **SSH Required:** Repository must be cloned via SSH (`git@github.com:`)
- **No Credentials in Git:** `.env` and `postman_environment.json` are excluded via `.gitignore`# verify full pipeline
