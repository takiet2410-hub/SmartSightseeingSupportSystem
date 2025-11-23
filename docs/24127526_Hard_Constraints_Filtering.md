# Work Breakdown: Hard Constraints Filtering (Module "Before")

## 📝 Problem Context

In the overall **"Filter-then-Rank"** architecture of the "Smart Sightseeing Support System" project, the first and most critical stage is **Hard Filtering**. This task is responsible for narrowing down a large database of thousands of locations to a small, relevant list of candidates by eliminating all options that do not meet the user's **mandatory** requirements. This stage ensures that the more computationally expensive steps later on only operate on a validated dataset, optimizing speed and accuracy.

---

## 🛠️ Tools, APIs & Libraries

To perform this task, we will use the following technologies:

* **Primary Language:** Python.
* **Data Processing Library:** **Pandas** will be used to load and perform filtering operations on location data stored as a CSV file.
* **API Framework:** **Flask** will be used to build the API endpoint, receiving filter requests from the client and returning results.

---

## 🎯 Problem Definition, I/O & Goals

### Problem Definition

Build an efficient filtering module using **Flask**, employing algorithms to process hard constraints provided by the user. This module must filter a location database and return a list of potential candidates **without** the intervention of a large language model (LLM) at this stage.

### Inputs & Outputs

* **📥 Inputs (User Provided):**
    * **Location (`location_province`):** A string specifying the province/city the user wants to explore (e.g., `"Lam Dong"`).
    * **Budget (`budget_range`):** A tuple `(min, max)` representing the budget range (e.g., `(5000000, 10000000)`).
    * **Companion (`companion_type`):** An identifier string (e.g., `"Couple"`, `"Family"`).
    * **Desired Timeframe (`season`):** A string from four available options: `"Spring"`, `"Summer"`, `"Autumn"`, `"Winter"`.
* **📤 Outputs (Expected):**
    * **Candidate List (`candidate_ids`):** A list containing the IDs of all locations that passed the filter. This list will be the input for the Soft Ranking stage.

### Goals

* **Primary Goal:** Complete the implementation of the hard filtering algorithm logic and integrate it into a Flask API.
* **Quantitative Goal:** The algorithm, after running, must return a candidate list of a reasonable size (approximately **20-30 locations**) to ensure the subsequent ranking stage has enough options without being overloaded.

---

## 🧩 Decomposition

We will break down the problem into smaller sub-problems for easier management and implementation.

### Sub-problem 2.1.1: Data Modeling & Access

* **Task:** Define the structure and write a function to load data from the database into memory.
* **Implementation Steps:**
    1.  **Design Database (`destinations.csv`):** Ensure the CSV file has the necessary columns: `landmark_id`, `LocationName`, `Province`, `Price_Min`, `Price_Max`, `Suitable_Companion`, `Suitable_Season`.
    2.  **Write Data Loading Function:** Build a Python function using Pandas (`pd.read_csv`) to load the CSV file into a DataFrame, ready for querying. This function needs to handle error cases such as file not found.

### Sub-problem 2.1.2: Implement Filtering Logic

* **Task:** Write code for individual filter functions corresponding to each hard constraint.
* **Implementation Steps:**
    1.  **`Location` Filter Function:** Write a function that takes `location_province` as input and filters the DataFrame to keep only locations where the `Province` column exactly matches the input.
    2.  **`Budget` Filter Function:** Write a filter function based on price range intersection logic: `(Dest.Price_Min <= User.Budget_Max) AND (Dest.Price_Max >= User.Budget_Min)`.
    3.  **`Companion` Filter Function:** Write a filter function based on substring checking. The function will keep rows where the `Suitable_Companion` column contains the `companion_type` string from the user.
    4.  **`Season` Filter Function:** Similar to `Companion`, write a filter function that keeps rows where the `Suitable_Season` column contains the `season` string selected by the user.

### Sub-problem 2.1.3: Flask API Integration

* **Task:** Combine the filter functions into a pipeline and create an API endpoint using Flask.
* **Implementation Steps:**
    1.  **Build Main Pipeline:** Write a `filter_pipeline` function that receives all user inputs, then sequentially applies the filter functions from Sub-problem 2.1.2 to the DataFrame.
    2.  **Create Flask Endpoint:** Build a `POST /filter` route in Flask. This route will receive a JSON request from the client (containing `location`, `budget`, `companion`, `season`), call the `filter_pipeline` function, and return a JSON response containing the `candidate_ids` list.

---

## 📈 Success Metrics

To evaluate the successful completion of this task, we will rely on the following metrics:

* **Correctness:** The percentage of returned results that 100% comply with hard constraints (e.g., Test case: Requesting "Summer" must not return locations only suitable for "Winter").
* **Performance:** The execution time of the entire filtering pipeline (including Flask API response time) must be under **100 milliseconds** on a dataset of 1000 locations.
* **Relevance of Output:** The size of the output candidate list is within the desired range (20-30 locations) with standard filters. This demonstrates a good balance between the database and filtering logic.