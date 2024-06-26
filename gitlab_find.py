import csv
import gitlab
import logging
import argparse
import requests
import json
import datetime
from tqdm import tqdm
from tenacity import retry, wait_exponential, stop_after_attempt, before_sleep_log
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup logging
logging.basicConfig(filename='gitlab_script.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Generic function to write to CSV file
def write_to_csv(filename, data, mode='w'):
    with open(filename, mode, newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(data)

# Function to fetch all projects using requests and write to JSON file with pagination
@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10), before_sleep=before_sleep_log(logging, logging.WARNING))
def fetch_projects(token, group_path, projects_json_file):
    page = 1
    all_projects = []
    with tqdm(desc="Getting List of Repos", unit="page") as pbar:
        while True:
            url = f"https://gitlab.com/api/v4/groups/{group_path}/projects?include_subgroups=true&per_page=100&page={page}"
            headers = {"PRIVATE-TOKEN": token}
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logging.error(f"Failed to fetch projects: {e}")
                raise
            projects = response.json()
            if not projects:
                break
            all_projects.extend(projects)
            page += 1
            pbar.update(1)
    with open(projects_json_file, 'w') as file:
        json.dump(all_projects, file)

# Function to convert projects JSON to CSV
def convert_projects_json_to_csv(projects_json_file, projects_csv_file):
    with open(projects_json_file, 'r') as json_file:
        projects = json.load(json_file)
    project_data = [['Project ID', 'Project Name']]  # Adding headers here
    project_data += [[project['id'], project['name']] for project in projects]
    write_to_csv(projects_csv_file, project_data, mode='w')

# Function to read projects from CSV file
def read_projects_from_csv(projects_file):
    projects = []
    with open(projects_file, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            projects.append({'id': row['Project ID'], 'name': row['Project Name']})
    return projects

# Function to get a project with retries
@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10), before_sleep=before_sleep_log(logging, logging.WARNING))
def get_project(gl, project_id):
    return gl.projects.get(project_id)

# Function to get a branch with retries
@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10), before_sleep=before_sleep_log(logging, logging.WARNING))
def get_branch(project, branch_name='master'):
    return project.branches.get(branch_name)

# Function to search blobs with retries
@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10), before_sleep=before_sleep_log(logging, logging.WARNING))
def search_blobs(project, term, ref):
    return project.search('blobs', term, ref=ref, get_all=True)

def process_project(project, search_phrase, gl):
    results = []
    try:
        # Get the full project object
        project_obj = get_project(gl, project['id'])
    except Exception as e:
        logging.error(f"Failed to get project {project['id']}: {e}")
        return results

    project_found = False

    # Check the master branch in the project
    try:
        branch = get_branch(project_obj)
        # Search for the term in the master branch
        search_results = search_blobs(project_obj, search_phrase, ref=branch.name)
        # If any results are found, process and store the output
        if search_results:
            project_found = True
            for result in search_results:
                filename = result['filename']
                snippet = result['data'].strip()
                # Collect data for results
                results.append([project['name'], branch.name, filename, snippet, 'Found'])

        # Log project even if no results are found
        if not project_found:
            results.append([project['name'], branch.name, '', '', 'Not Found'])

    except gitlab.exceptions.GitlabGetError:
        logging.warning(f"Master branch not found in project '{project['name']}'")
        results.append([project['name'], 'master', '', '', 'Master branch not found'])
    except Exception as e:
        logging.error(f"Error processing project {project['name']}: {e}")
    
    return results

def main(token, group_path, search_phrase, output_file, projects_json_file, projects_csv_file):
    # Add timestamp to file names
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = f"{output_file.rsplit('.', 1)[0]}.{timestamp}.{output_file.rsplit('.', 1)[1]}"
    projects_json_file = f"{projects_json_file.rsplit('.', 1)[0]}.{timestamp}.{projects_json_file.rsplit('.', 1)[1]}"
    projects_csv_file = f"{projects_csv_file.rsplit('.', 1)[0]}.{timestamp}.{projects_csv_file.rsplit('.', 1)[1]}"

    # Initialize the CSV file with headers
    write_to_csv(output_file, [['Project', 'Branch', 'File', 'Snippet', 'Status']])

    # Fetch projects and write to JSON
    try:
        fetch_projects(token, group_path, projects_json_file)
    except Exception as e:
        logging.error(f"Failed to fetch projects list: {e}")
        return

    # Convert projects JSON to CSV
    convert_projects_json_to_csv(projects_json_file, projects_csv_file)
    
    # Read projects from CSV file
    projects = read_projects_from_csv(projects_csv_file)

    # Connect to GitLab
    gl = gitlab.Gitlab('https://gitlab.com', private_token=token)

    # Use ThreadPoolExecutor to process projects concurrently
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_project, project, search_phrase, gl): project for project in projects}
        with tqdm(total=len(futures), desc=f"Search Repos for '{search_phrase}'", unit="project") as pbar:
            for future in as_completed(futures):
                project_results = future.result()
                results.extend(project_results)
                pbar.update(1)
    
    write_to_csv(output_file, results, mode='a')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Search for a term in GitLab projects.")
    parser.add_argument('token', type=str, help='GitLab private token')
    parser.add_argument('group_path', type=str, help='Path of the GitLab group to search in')
    parser.add_argument('search_phrase', type=str, help='Phrase to search for in the projects')
    parser.add_argument('--output', type=str, default='gitlab_search_results.csv', help='Output CSV file name')
    parser.add_argument('--projects_json_file', type=str, default='projects.json', help='File to store the list of projects in JSON format')
    parser.add_argument('--projects_csv_file', type=str, default='projects.csv', help='File to store the list of projects in CSV format')

    args = parser.parse_args()
    main(args.token, args.group_path, args.search_phrase, args.output, args.projects_json_file, args.projects_csv_file)
