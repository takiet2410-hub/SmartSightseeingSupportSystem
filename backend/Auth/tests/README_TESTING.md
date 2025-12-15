
-----

### File Name: `README_TESTING.md`

# Unit Testing Documentation - Auth Module

This document provides instructions on how to set up, run, and evaluate the unit tests for the Authentication Module. The testing suite uses **pytest** and focuses on achieving high code coverage for critical components including Authentication Routers, Configuration, and Email Utilities.

## 🛠 Prerequisites

Ensure you have Python installed and the project dependencies set up. The testing suite requires the following specific libraries:

* `pytest`: The testing framework.
* `pytest-cov`: For generating code coverage reports.
* `pytest-asyncio`: For testing asynchronous FastAPI endpoints.
* `httpx`: For mocking requests in TestClient.
* `requests`: For mocking external API calls (e.g., Brevo, Facebook).

### Install Testing Dependencies
You can install them via pip:

```bash
pip install pytest pytest-cov pytest-asyncio httpx requests
````

-----

## 🚀 Running the Tests

To run the entire test suite, execute the following command in the project root directory:

```bash
pytest -v
```

  * `-v`: Verbose mode (shows each test case name and status).

### Running Specific Test Files

If you want to isolate the tests for a specific module:

  * **Auth Routes:** `pytest tests/test_auth_routes.py`
  * **Email Utils:** `pytest tests/test_email_utils.py`
  * **Configuration:** `pytest tests/test_config.py`

-----

## 📊 Checking Code Coverage

We strive for high test coverage to ensure system stability. Follow these steps to generate a coverage report.

### 1\. Generate Report

Run the following command to test the `routers` and `core` directories:

```bash
pytest --cov=routers --cov=core tests/ --cov-report=term-missing
```

This will output a summary in the terminal showing the percentage covered and lines missing.

### 2\. Generate HTML Report (Visual)

For a detailed visual representation of which lines are covered:

```bash
pytest --cov=routers --cov=core tests/ --cov-report=html
```

After running this, open the file `htmlcov/index.html` in your browser to inspect the coverage in detail.

-----

## 🧪 Test Scope & Strategy

The unit tests are designed to cover both **success paths** and **failure scenarios** (edge cases). We utilize `unittest.mock` to isolate the system from external dependencies (Database, Google/Facebook APIs, Email Services).

### 1\. Authentication Router (`routers/auth.py`)

  * **Registration:**
      * Successful user creation.
      * Handling duplicate usernames or emails.
      * Handling email sending failures during registration.
  * **Login (Local):**
      * Successful login (JWT generation).
      * Incorrect password or non-existent user.
      * Inactive account checks.
  * **OAuth2 (Google & Facebook):**
      * Mocking external token verification.
      * Creating new users vs. logging in existing users via OAuth.
      * Handling invalid tokens or API errors from providers.
  * **Password Management:**
      * Forgot Password flow (Sending reset link).
      * Reset Password flow (Token validation, expiration checks, password matching).
  * **Email Verification:**
      * Token validation and account activation.

### 2\. Email Utilities (`core/email_utils.py`)

  * **Mocking External API:** We mock `requests.post` to simulate Brevo (SMTP) responses without sending real emails.
  * **Scenarios Covered:**
      * Success (HTTP 201).
      * API Errors (HTTP 400/500).
      * Network Exceptions.
  * **Content Verification:** Ensuring the correct links and tokens are generated in the email body.

### 3\. System Configuration (`core/config.py`)

  * **Environment Validation:** Tests verify that the application raises correct errors (`ValueError`) or warnings if critical environment variables (e.g., `MONGO_URI`, `SECRET_KEY`) are missing.
  * **Reloading Strategy:** Uses `importlib.reload` to test configuration loading behavior dynamically.

-----

## 📂 Project Structure for Testing

```text
.
├── core/
│   ├── config.py           # Config logic
│   └── email_utils.py      # Email sending logic
├── routers/
│   └── auth.py             # Auth endpoints
├── tests/
│   ├── conftest.py         # Pytest fixtures (Client setup, Config reload)
│   ├── test_auth_routes.py # Tests for Register, Login, Reset Pass, OAuth
│   ├── test_config.py      # Tests for environment variables
│   └── test_email_utils.py # Tests for Brevo email sending
└── README_TESTING.md       # This file
```

-----

## 📝 Note on Mocking

To ensure tests are fast and reliable:

1.  **No Real Database:** `user_collection` is mocked. No data is written to MongoDB during tests.
2.  **No Real Emails:** The Brevo API is mocked. No actual emails are sent.
3.  **No Real OAuth Calls:** Google and Facebook verification functions are mocked to return predefined user data.

<!-- end list -->
