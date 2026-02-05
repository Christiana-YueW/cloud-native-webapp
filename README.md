
# webapp
Cloud Native Web Application for CSYE 6225

# A2 Integration Tests (Postman / Newman + GitHub Actions)

This repository includes Postman/Newman integration tests and a GitHub Actions workflow
that runs the tests automatically on **Pull Requests to `main`**.

---

## What’s included

- `postman_collection.json`  
  Postman collection for A2 integration tests.

- `postman_environment.template.json`  
  Postman environment **template only** (NO real credentials committed).

- `.github/workflows/newman.yml`  
  GitHub Actions workflow that:
  1. Starts a PostgreSQL service
  2. Starts the FastAPI application
  3. Runs Newman against the Postman collection

---

## CI behavior (TA-friendly)

✅ **CI runs automatically when a Pull Request is opened targeting `main`.**

✅ **All integration tests are executed *before merge*.  
The PR can only be merged after CI passes.**

### How to verify CI results

On the Pull Request page:
1. Click the **Checks** tab
2. Look for **Integration Tests (Postman/Newman)** → job: `newman`
3. A green ✅ indicates all integration tests passed

> Note:  
> The step **"Print API logs on failure"** is expected to appear as *skipped* when CI
> succeeds, because it only runs on failures (`if: failure()`).

---

## Secrets / Credentials (Zero-tolerance compliant)

⚠️ **No credentials, API keys, or passwords are committed to the repository.**

All test credentials are injected at runtime via **GitHub Actions Repository Secrets**:

- `TEST_USER_USERNAME`
- `TEST_USER_PASSWORD`
- `TEST_USER_NEW_PASSWORD`

The workflow dynamically populates the Postman environment file inside CI.
Only the environment **template** is committed.

This design complies with the course **zero-tolerance credential policy**.

---

## Local execution (optional)

Local execution is optional.  
**Grading is based on CI results from GitHub Actions on the Pull Request.**