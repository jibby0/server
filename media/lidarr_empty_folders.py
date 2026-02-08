# Lidarr has trouble moving Music without a pre-existing artist folder.
# 
# */1 * * * * /usr/bin/run-one /usr/bin/python3 /path/to/lidarr_empty_folders.py <lidarr IP>:8686 <API key> /path/to/Music/ 2>&1 | /usr/bin/logger -t lidarr_empty_folders
# Or run it in a k8s cronjob. See lidarr-empty-folders.yaml
# kubectl -n plex create configmap lidarr-empty-folders --from-file=lidarr_empty_folders.py

import requests
from requests.adapters import HTTPAdapter, Retry
import os
import sys
if len(sys.argv) != 4:
    print("One or more args are undefined")
    sys.exit(1)

lidarr_server, lidarr_api_key, music_folder = sys.argv[1:4]


retries = Retry(total=10,
                backoff_factor=1,
                status_forcelist=[ 500, 502, 503, 504 ])
s = requests.Session()
s.mount('http://', HTTPAdapter(max_retries=retries))
resp = s.get(
    f"{lidarr_server}/api/v1/artist",
    headers={"Authorization": f"Bearer {lidarr_api_key}"}
    )
artists = resp.json()

for artist in artists:
     artist_name = artist.get("artistName")
     artist_path = music_folder + artist_name
     if ('/' not in artist_name) and (not os.path.exists(artist_path)):
        print("Creating ", artist_path)
        os.mkdir(artist_path)
