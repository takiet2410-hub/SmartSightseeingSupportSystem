# Project: [Smart Sightseeing Support System]

## 1. Team Members

| No. | Full Name           | Student ID | Primary Role   | Email                        |
| :-- | :------------------ | :--------- | :------------- | :--------------------------- |
| 1   | Trần Anh Kiệt       | `24127287` | Project Leader | takiet2410@clc.fitus.edu.vn  |
| 2   | La Anh Hào          | `24127361` | Module After   | lahao2434@clc.fitus.edu.vn   |
| 3   | Trần Đức Quý        | `24127526` | Module Before  | tdquy2421@clc.fitus.edu.vn   |
| 4   | Nguyễn Tiến Phát    | `24127098` | Module During  | ntphat2417@clc.fitus.edu.vn  |
| 5   | Phan Đình Minh Quân | `24127517` | Module After   | pdmquan2429@clc.fitus.edu.vn |
| 6   | Lưu Minh Quân       | `24127223` | Module During  | lmquan2429@clc.fitus.edu.vn  |
| 7   | Nguyễn Quốc Dương   | `24127349` | Module Before  | nqduong2416@clc.fitus.edu.vn |

---

## 2. Task Assignments & Branches

This section outlines the tasks for each member and their corresponding Git branch.

**Branch Naming Convention:** `[StudentID]_[Brief_Task_Name]`
**Main Development Branch:** `develop`
**Production Branch:** `main`

### Phase 1: Decomposition Problems

| Feature / Task                                                                                                          | Assigned To         | Student ID | Branch Name                            | Status        |
| :---------------------------------------------------------------------------------------------------------------------- | :------------------ | :--------- | :------------------------------------- | :------------ |
| **Analysis**                                                                                                            |                     |            |                                        |               |
| Design Database Schema                                                                                                  | Trần Anh Kiệt       | `24127287` | `24127287_Database_Schema`             | [In Progress] |
| **Module Before**                                                                                                       |                     |            |                                        |               |
| Design algorithm (content-based filtering, constraint application, scoring).                                            | Trần Đức Quý        | `24127526` | `24127526_Design_Algorithm`            | [In Progress] |
| Implement preference matching and scoring (tag overlap, term frequency inverse document frequency + cosine similarity). | Nguyễn Quốc Dương   | `24127349` | `24127349_Abstract_Interest_Processor` | [In Progress] |
| Implement ranking and output formatting (Top-N result generation).                                                      | Trần Anh Kiệt       | `24127287` | `24127287_Ranking_Output`              | [Not Started] |
| **Module During**                                                                                                       |                     |            |                                        |               |
| Design filename-to-landmark mapping and mock GPS filtering logic.                                                       | Nguyễn Tiến Phát    | `24127098` | `24127098_Image_Handling`              | [In Progress] |
| CV API Integration                                                                                                      | Lưu Minh Quân       | `24127223` | `24127223_CV_Integration`              | [In Progress] |
| Implement information retrieval for matched landmarks.                                                                  | Trần Anh Kiệt       | `24127287` | `24127287_Info_Retrieval`              | [In Progress] |
| **Module After**                                                                                                        |                     |            |                                        |               |
| Design Metadata Extractor                                                                                               | Phan Đình Minh Quân | `24127517` | `24127517_Metadata_Extractor`          | [In Progress] |
| Design Filtering, Clustering and Curation Logic                                                                         | La Anh Hào          | `24127361` | `24127361_Image_Handling_Logic`        | [In Progress] |
| Album Generation                                                                                                        | Trần Anh Kiệt       | `24127287` | `24127287_Album_Generation`            | [In Progress] |

---

## 3. Git Workflow

1.  Always pull the latest code from the `develop` branch before starting your work:
    * `git checkout develop`
    * `git pull origin develop`
    * `git checkout [Your_Branch_Name]`
    * `git merge develop` (Resolve conflicts if any)

2.  Work on your personal feature branch (e.g., `24127517_Metadata_Extractor`).

3.  After completing your task, `add`, `commit`, and `push` your branch to the remote repository:
    * `git push -u origin 24127517_Metadata_Extractor`

4.  Create a **Pull Request (PR)** from your branch into the `develop` branch.

5.  Tag other members to review your code. At least **[2]** approval is required before merging.

6.  **DO NOT** push directly to `main` or `develop`.