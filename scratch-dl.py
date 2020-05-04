import requests
import argparse
import shutil
import os
import re
import json

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36"}

def download_file(url, dest):
    r = requests.get(url, headers=headers)
    with open(dest, 'wb') as f:
        f.write(r.content)

def download_asset(filename, project_id):
    """Download asset"""
    download_file(f"https://assets.scratch.mit.edu/internalapi/asset/{filename}/get/", f"{project_id}/{filename}")

def download_asset_c(filename, counter, project_id):
    """Download asset with a counter"""
    download_file(f"https://assets.scratch.mit.edu/internalapi/asset/{filename}/get/", f"{project_id}/{counter}.{filename.split('.')[-1]}")

def download_project_and_metadata(project_id):
    #skip existing
    if (os.path.isfile(f"{project_id}.sb") or os.path.isfile(f"{project_id}.sb2") or os.path.isfile(f"{project_id}.sb3")) and os.path.isfile(f"{project_id}.json"):
        print(f"Skipping {project_id} (already downloaded)")
        return
    try:
        download_metadata(project_id)
        download_project(project_id)
    except:
        print(f"Error downloading {project_id}")
        with open("error.log", "a") as f:
            f.write(f"Error downloading {project_id}\n")

def download_metadata(project_id):
    project_id = str(int(project_id))
    print(f"Downloading metadata for project {project_id}")
    download_file(f"https://api.scratch.mit.edu/projects/{project_id}",f"{project_id}.json")
    download_file(f"https://cdn2.scratch.mit.edu/get_image/project/{project_id}_100000x100000.png",f"{project_id}.png")

def download_project(project_id):
    # Verify the project id is a number so we don't end up corrupting the entire archive
    #TODO: improve this line
    project_id = str(int(project_id))
    print(f"Downloading project {project_id}")
    r = requests.get(f"https://projects.scratch.mit.edu/{project_id}", headers=headers)
    version = 0
    if r.content[:9] == b'ScratchV0':
        version = 1
        with open(f"{project_id}.sb", 'wb') as f:
            f.write(r.content)
        return {"success": True, "version": version}
    if not os.path.exists(project_id):
        os.mkdir(project_id)
    with open(f"{project_id}/project.json", 'wb') as f:
        f.write(r.content)
    project_json = json.loads(r.content)
    if "info" in project_json:
        # sb2 project
        version = 2
        counter = 0
        # Fix project json
        if "penLayerMD5" in project_json:
            if len("penLayerMD5") > 0:
                project_json["penLayerID"] = counter
                download_asset_c(project_json["penLayerMD5"], counter, project_id)
                counter += 1
        if "sounds" in project_json:
            for sound in project_json["sounds"]:
                sound["soundID"] = counter
                download_asset_c(sound["md5"], counter, project_id)
                counter += 1
        if "costumes" in project_json:
            for costume in project_json["costumes"]:
                costume["baseLayerID"] = counter
                download_asset_c(costume["baseLayerMD5"], counter, project_id)
                counter += 1
        for child in project_json["children"]:
            if "penLayerMD5" in child:
                if len("penLayerMD5") > 0:
                    child["penLayerID"] = counter
                    download_asset_c(child["penLayerMD5"], counter, project_id)
                    counter += 1
            if "sounds" in child:
                for sound in child["sounds"]:
                    sound["soundID"] = counter
                    download_asset_c(sound["md5"], counter, project_id)
                    counter += 1
            if "costumes" in child:
                for costume in child["costumes"]:
                    costume["baseLayerID"] = counter
                    download_asset_c(costume["baseLayerMD5"], counter, project_id)
                    counter += 1
        # Backup original json
        os.rename(f"{project_id}/project.json",f"{project_id}/original.json")
        with open(f"{project_id}/project.json", 'w') as f:
            json.dump(project_json,f)
    else:
        # sb3 project
        version = 3
        for target in project_json["targets"]:
            for k in ["costumes","sounds"]:
                if k in target:
                    for item in target[k]:
                        download_asset(item["md5ext"], project_id)
    shutil.make_archive(f"{project_id}", 'zip', project_id)
    os.rename(f"{project_id}.zip",f"{project_id}.sb{str(version)}")
    shutil.rmtree(project_id)
    return {"success": True, "version": version}

def download_user(username):
    print(f"Downloading user {username}")
    if not os.path.exists(username):
        os.mkdir(username)
    os.chdir(username)
    r = requests.get(f"https://api.scratch.mit.edu/users/{username}", headers=headers)
    with open(f"userinfo.json", 'wb') as f:
        f.write(r.content)
    userid = json.loads(r.content)["id"]
    download_file(f"https://cdn2.scratch.mit.edu/get_image/user/{userid}_100000x100000.png","avatar.png")

    projectids = []
    offset = 0
    while True:
        print(f"Downloading {username}'s projects (page {offset+1})")
        r = requests.get(f"https://api.scratch.mit.edu/users/{username}/projects?limit=20&offset={offset*20}", headers=headers)
        with open(f"projects_{offset}.json", 'wb') as f:
            f.write(r.content)
        projects = json.loads(r.content)
        if len(projects) == 0:
            break
        for project in projects:
            projectids.append(project["id"])
        offset += 1
    for project in projectids:
        download_project_and_metadata(project)
    os.chdir("..")


parser = argparse.ArgumentParser()
parser.add_argument("url", help="url")
#TODO: Add option to download metadata separately
#parser.add_argument("-p", "--path", help="Sven Co-op install path")
args = parser.parse_args()

url_search = re.search('scratch.mit.edu/users/(.*)(/|$)', args.url, re.IGNORECASE)
if url_search:
    username = url_search.group(1)
    download_user(username)
url_search = re.search('scratch.mit.edu/projects/([0-9]*)', args.url, re.IGNORECASE)
if url_search:
    project_id = url_search.group(1)
    download_project_and_metadata(project_id)
