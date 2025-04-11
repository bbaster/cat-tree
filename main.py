#!/usr/bin/env python3

'''
Copyright (C) 2025 bbaster

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''

import requests
import re
import string
import random
import sys
import os
import subprocess
import importlib.util
import platform

from pathlib import Path
from dotenv import load_dotenv
from plyer import notification
from shutil import which


load_dotenv()
userhash = os.getenv("USERHASH")


def check_environment() -> str:
    #Check for Android
    if hasattr(sys, 'getandroidapilevel'):
        #Check for Termux
        if which('termux-setup-storage'):
            #Check for Termux API
            if which('termux-notification'):
                return "android-termux-api"
            else:
                return "android-termux-noapi"
        else:
            return "android"
    else:
        return "other"


def notify(title: str, message: str, timeout: int = 10):
    environment = check_environment()
    if environment in {'android', 'other'}:
        try:
            if environment == 'android' and not importlib.util.find_spec('jnius'):
                raise ModuleNotFoundError
            notification.notify(
                title=title,
                message=message,
                timeout=timeout
            )
        except (NotImplementedError, ModuleNotFoundError):
            print("Error: Notifications unavailable!", file=sys.stderr)
    elif environment == 'android-termux-api':
        proc = subprocess.run([
                "termux-notification", "--sound",
                "-t", title,
                "-c", message,
                "--button1", "Copy",
                "--button1-action", f"termux-clipboard-set {message}"
            ])
    else:
        print("Error: Notifications unavailable!", file=sys.stderr)


def inform(server_response: str):
    if re.search(r"^(https?://)?files.catbox.moe/\w{6}(\.\w+)?$", server_response):
        print(server_response)
        notify(
                title="Successfully uploaded to Catbox",
                message=server_response,
                timeout=10
              )
    else:
        print("Error: Upload to Catbox unsuccessful", file=sys.stderr)
        print(f"Server response: {server_response}", file=sys.stderr)
        notify(
                title="Error: Upload to Catbox unsuccessful",
            message=f"Server response: {server_response}",
            timeout=10
        )
        exit(1)


def upload(filepath: str) -> string:

    filepath = Path(filepath)
    
    headers = {
        'User-Agent': f'cat-tree/1.0 (Python {platform.python_version()}; {platform.system()} {platform.release()}) +https://github.com/bbaster/cat-tree',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en',
        'DNT': '1',
        'Sec-GPC': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1', 
        'Priority': 'u=0, i',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }
    
    response_root = requests.get('https://catbox.moe/', headers=headers)
    cookie = response_root.headers['Set-Cookie']
    regex = re.search(r"^PHPSESSID=([0-9a-f]{32}); path=/$", cookie)
    cookies = {'PHPSESSID': regex.group(1)}

    form_boundary_id = ''
    for _ in range(32):
        form_boundary_id += random.choice(string.hexdigits[:16])
    form_boundary = "------geckoformboundary" + form_boundary_id
    
    
    headers.update({
        'Accept': 'application/json',
        'Referer': 'https://catbox.moe/',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': f'multipart/form-data; boundary={form_boundary[2:]}',
        'Origin': 'https://catbox.moe',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
    })

    headers.pop('Sec-Fetch-User')
    headers.pop('Priority')
    
    
    with filepath.open('rb') as file:
        contents = file.read()

    filename = filepath.parts[-1]

    data = f'''{form_boundary}
Content-Disposition: form-data; name="reqtype"

fileupload
{form_boundary}
'''

    if userhash:
        data += f'''Content-Disposition: form-data; name="userhash"

{userhash}
{form_boundary}
'''

    data += f'''Content-Disposition: form-data; name="fileToUpload"; filename="{filename}"
Content-Type: application/octet-stream           

'''

    data = data.encode("utf-8") + contents + f"\n{form_boundary}\n".encode("utf-8")

    response_api = requests.post('https://catbox.moe/user/api.php', cookies=cookies, headers=headers, data=data)
    return response_api.text


if not sys.argv[1:]:
    filepath = Path(input("Input a file path: "))
    inform(upload(filepath))

else:
    for filepath in sys.argv[1:]:
        inform(upload(filepath))
