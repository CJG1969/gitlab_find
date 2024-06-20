# GitLab Project Search Script

This script searches for a specific phrase in the `master` branch of all projects within a GitLab group, including its subgroups, and outputs the results to a CSV file.

## Features
- Fetches all projects from a GitLab group and its subgroups.
- Searches for a specified phrase in the `master` branch of each project.
- Outputs project data and search results to CSV files.
- Robust error handling and retry mechanisms for network requests.

## Prerequisites
- Python 3.6 or later
- `requests` library
- `tenacity` library
- `tqdm` library
- `python-gitlab` library

## Installation
1. Clone the repository or download the script.
2. Install the required Python libraries:
    ```sh
    pip install requests tenacity tqdm python-gitlab
    ```

## Usage
1. Save the script to a file, e.g., `gitlab_find.py`.
2. Run the script from the command line:
    ```sh
    python3 gitlab_find.py <your_gitlab_private_token> <group_path> <search_phrase>
    ```
    Replace `<your_gitlab_private_token>` with your actual GitLab private token, `<group_path>` with the path of the GitLab group you want to search in, and `<search_phrase>` with the phrase you want to search for.

3. Optional arguments:
    - `--output`: Specifies the output CSV file for search results (default: `gitlab_search_results.csv`).
    - `--projects_json_file`: Specifies the file to store the list of projects in JSON format (default: `projects.json`).
    - `--projects_csv_file`: Specifies the file to store the list of projects in CSV format (default: `projects.csv`).

    Example:
    ```sh
    python3 gitlab_find.py <your_gitlab_private_token> <group_path> <search_phrase> --output=custom_output.csv --projects_json_file=custom_projects.json --projects_csv_file=custom_projects.csv
    ```

## Explanation
- **Fetching Projects:** The script fetches all projects from the specified GitLab group and its subgroups using the GitLab API and stores the data in a JSON file.
- **Converting JSON to CSV:** The project data is converted from JSON to a CSV file for easier manipulation and readability.
- **Searching Projects:** The script connects to GitLab using the `python-gitlab` library and searches for the specified phrase in the `master` branch of each project.
- **Output:** The search results are collected and written to an output CSV file, including the project name, branch name, file name, snippet of the matching content, and the status of the search.

## Example Output
The `gitlab_search_results.csv` file will contain:

| Project     | Branch | File         | Snippet          | Status                   |
|-------------|--------|--------------|------------------|--------------------------|
| ProjectA    | master | README.md    | Example snippet  | Found                    |
| ProjectB    | master |              |                  | Not Found                |
| ProjectC    | master |              |                  | Master branch not found  |
