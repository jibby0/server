# */1 * * * * /usr/bin/run-one /usr/bin/python3 /path/to/lidarr_empty_folders.py <lidarr IP>:8686 <API key> /path/to/Music/ 2>&1 | /usr/bin/logger -t lidarr_empty_folders

import requests
import os
import sys
if len(sys.argv) != 4:
    print("One or more args are undefined")
    sys.exit(1)

lidarr_server, lidarr_api_key, music_folder = sys.argv[1:4]

resp = requests.get(
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
