import requests
import os
from datetime import datetime
import urllib3
import zipfile
import io
import json
from blackduck.HubRestApi import HubInstance


CONCLUSION = os.environ["INPUT_CONCLUSION"]
GITHUB_API_KEY = os.environ["INPUT_GITHUB_API_KEY"]

SPLUNK_API_KEY = os.environ["INPUT_SPLUNK_API_KEY"]
SPLUNK_INDEX = os.environ["INPUT_SPLUNK_INDEX"]
SPLUNK_SOURCE =  os.environ["INPUT_SPLUNK_SOURCE"]
SPLUNK_URL = os.environ["INPUT_SPLUNK_URL"]

BLACKDUCK_API_KEY = os.environ["INPUT_BLACKDUCK_API_KEY"]
BLACKDUCK_URL = os.environ["INPUT_BLACKDUCK_URL"]
BLACKDUCK_PROJECT_NAME = os.environ["INPUT_BLACKDUCK_PROJECT_NAME"]

GITHUB_REPOSITORY = os.environ["GITHUB_REPOSITORY"]
GITHUB_RUN_ID = os.environ["GITHUB_RUN_ID"]
GITHUB_API_URL = os.environ["GITHUB_API_URL"]

#JUNIT_REPORT = os.environ["INPUT_JUNIT_REPORT"]

header = {"Accept": "application/vnd.github.groot-preview+json",
    "Authorization": f"token {GITHUB_API_KEY}"}

def get_timestamp(date_time, template='%Y-%m-%dT%H:%M:%SZ'):
    timestamp = datetime.strptime(date_time, template).timestamp()
    return timestamp

def collect_build_data():
    print("Collecting Build Data ... ")
 
    run_data = requests.get(f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/actions/runs/{GITHUB_RUN_ID}", headers=header).json()
    build_status = CONCLUSION
    branch = run_data["head_branch"]
    head_sha = run_data["head_sha"]
    build_timestamp = get_timestamp(run_data["updated_at"])

    pulls = requests.get(f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/commits/{head_sha}/pulls", headers=header).json()
    if pulls != []:
        # Commit made by pull request
        pr_number = pulls[-1]["number"]
        commits = requests.get(f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/pulls/{pr_number}/commits", headers=header).json()
    else:
        # Single commit, make it a list to be iterated in sam was as for pulls
        commits = [requests.get(f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/commits/{head_sha}", headers=header).json()]

    commits_list = []
    for commit in commits:
        data = {
            "comment": commit["commit"]["message"],
            "timestamp": get_timestamp(commit["commit"]["author"]["date"]),
            "authorName": commit["commit"]["author"]["name"]
        }
        commits_list.append(data)
    
    build_data = {
        "jobName": GITHUB_REPOSITORY.split("/")[-1], # Optional but recommended
        "result": build_status.upper() if build_status else "UNKNOWN",  # Mandatory : SUCCESS | FAILURE | UNSTABLE (DF)
        "branch": branch,   # Mandatory : dev | test | master | etc. (LTFC)
        "changeSets": commits_list,
        "customParameters": {}
    }
    build_data = process_reports(build_data)
    post_to_splunk(build_data, build_timestamp)
    

def process_reports(build_data):
    
    allartifactresponse = requests.get(f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/actions/artifacts", headers=header)
    allartifactresponseJson = allartifactresponse.json()
    #print(allartifactresponseJson)
 
    if allartifactresponseJson['total_count'] > 0:
        for i in allartifactresponseJson['artifacts']:
            id = i['id']
            #download artifats
            downloadartifact = requests.get(f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/actions/artifacts/{id}/zip", headers=header)
            downloadfromurl = requests.get(downloadartifact.url)
            z = zipfile.ZipFile(io.BytesIO(downloadfromurl.content))
            z.extractall()

            #delete artifacts
            #requests.delete(f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/actions/artifacts/{id}", headers=header)

        polarisJson = process_polaris_report('polaris-output.txt' , build_data)
        codecoverageJson = process_code_coverage('coverage-summary.json',polarisJson)
        blackduckJson = process_blackduck_report(codecoverageJson)
        return blackduckJson

    
def process_polaris_report(file_name , reportJson):
    with open(file_name , 'r+') as fobj:
        contents = fobj.read()
    linenum = contents.find('Job issue summary\n')
    jsondata = eval(contents[linenum+len('Job issue summary\n'):])
    reportJson['customParameters']['polarisReport'] = jsondata
    return reportJson


def process_code_coverage(file_name, coverageJson):
    with open(file_name,'r') as f:
        data = json.load(f)
    codecov = data['total']
    coverageJson['customParameters']['codeCoverage'] = codecov
    return coverageJson


def process_blackduck_report(reportJson):
    
    riskUrl = ''
    hub = HubInstance(BLACKDUCK_URL, api_token=BLACKDUCK_API_KEY, insecure=True)

    #'docker_web_app'
    projects = hub.get_project_by_name(BLACKDUCK_PROJECT_NAME)
    projectVersions = hub.get_project_versions(project=projects)

    for item in projectVersions['items'][0]['_meta']['links']:
        if item['rel'] == 'riskProfile':
            riskUrl = item['href']

    riskData = hub.execute_get(url=riskUrl)
    vulnerableData = riskData.json()['categories']['VULNERABILITY']
    reportJson['customParameters']['blackduckReport'] = vulnerableData
    return reportJson

    
def post_to_splunk(json_data, timestamp):

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    header = {
        "Authorization": f"Splunk {SPLUNK_API_KEY}",
        "Content-Type": "application/json;charset=UTF-8"
    }

    payload = {
        "time": str(timestamp),
        "index": SPLUNK_INDEX,
        "source": SPLUNK_SOURCE,
        "sourcetype": "_json",
        "event": json_data
    }

    print(payload)
    result = requests.post(SPLUNK_URL, headers=header, json=payload, verify=False)
    print("Calling Splunk")
    print(result.text)

if __name__ == "__main__":
    collect_build_data()
