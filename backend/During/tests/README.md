# How to Execute Unittest Tests

### Prerequisites

Ensure you are in the **root directory** of the project (the folder containing `main.py` and the `tests/` folder).

### 1\. Prerequisites

Ensure you have the coverage library installed:

```bash
pip install coverage
```

### 2\. Run All Tests & Collect Coverage Data

To execute the entire test suite and record code coverage, run:

```bash
coverage run -m unittest discover tests
```

### 3\. View Coverage Report (Terminal)

To see a summary table in your terminal (including which lines are missing test coverage), run:

```bash
coverage report -m
```

### 4\. Generate Visual Report (HTML)

For a detailed, color-coded visual representation of your code coverage:

1.  Generate the HTML files:
    ```bash
    coverage html
    ```
2.  Open the file `htmlcov/index.html` in your web browser.

### 5\. Run Specific Test Modules

You can also run coverage on individual test files:

  * **Test Visual Search Logic:**

    ```bash
    coverage run -m unittest tests/test_visual_search.py
    ```

  * **Test Authentication Logic:**

    ```bash
    coverage run -m unittest tests/test_auth_deps.py
    ```

  * **Test History Management:**

    ```bash
    coverage run -m unittest tests/test_detection_history.py
    ```

  * **Test History Detail & Summary:**

    ```bash
    coverage run -m unittest tests/test_history_detail.py
    ```

  * **Test Main App Initialization:**

    ```bash
    coverage run -m unittest tests/test_main.py
    ```

  * **Test Shared Resources (DB/Model Loading):**

    ```bash
    coverage run -m unittest tests/test_shared_resources.py
    ```

### Understanding the Output

  * **Stmts:** The total number of executable statements in the file.
  * **Miss:** The number of statements not executed during the test.
  * **Cover:** The percentage of code covered by tests.
  * **Missing:** The specific line numbers that were **not** executed (useful for identifying gaps in testing).
  * **✔ PASSED:** Indicates the specific test case ran successfully.