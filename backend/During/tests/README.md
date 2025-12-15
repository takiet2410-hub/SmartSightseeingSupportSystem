# How to Execute Unittest Tests

### Prerequisites

Ensure you are in the **root directory** of the project (the folder containing `main.py` and the `tests/` folder).

### 1\. Run All Tests

To execute the entire test suite at once, run the following command from the terminal:

```bash
python -m unittest discover tests
```

### 2\. Run Specific Test Modules

You can run individual test files to check specific functionalities:

  * **Test Visual Search Logic:**

```bash
    python -m unittest tests/test_visual_search.py
```

  * **Test Authentication Logic:**

```bash
    python -m unittest tests/test_auth_deps.py
```

  * **Test History Management:**

```bash
    python -m unittest tests/test_detection_history.py
```

  * **Test History Detail & Summary:**

```bash
    python -m unittest tests/test_history_detail.py
```

  * **Test Main App Initialization:**

```bash
    python -m unittest tests/test_main.py
```

  * **Test Shared Resources (DB/Model Loading):**

```bash
    python -m unittest tests/test_shared_resources.py
```

### Understanding the Output

  * **✔ PASSED:** Indicates the specific test case ran successfully.
  * **OK:** At the end of the output, this means all tests in the suite passed.
  * **FAILED:** If any logic is broken, the console will show exactly which test failed and why.