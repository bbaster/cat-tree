#!/usr/bin/env python3

"""
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
"""

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
    # Check for Android
    if hasattr(sys, 'getandroidapilevel'):
        # Check for Termux
        if which('termux-setup-storage'):
            # Check for Termux API
            if which('termux-notification'):
                return "android-termux-api"
            else:
                return "android-termux-noapi"
        else:
            return "android"
    else:
        return "other"


def error(title: str, message: str = '', fatal: bool = True, notification: bool = True):
    if notification:
        notify(
            title=title,
            message=message,
            timeout=10
        )
    print("Error: ", title, f"{'\n' if message else ''}", message, file=sys.stderr, sep='')
    if fatal:
        exit(1)


def notify(title: str, message: str = '', timeout: int = 10):
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
            error(title="Error: Notifications unavailable!", fatal=False, notification=False)
    elif environment == 'android-termux-api':
        subprocess.run([
            "termux-notification", "--sound",
            "-t", title,
            "-c", message,
            "--button1", "Copy",
            "--button1-action", f"termux-clipboard-set {message}"
        ])
    else:
        print("Error: Notifications unavailable!", file=sys.stderr)


def inform(server_response: str, litterbox: bool = False):
    print("Debug: inform() function entered")

    if litterbox:
        service_name = 'Litterbox'
    else:
        service_name = 'Catbox'
    if re.search(r"^(https?://)?(files|litterbox)\.catbox\.moe/\w{6}(\.\w+)?$", server_response):
        print(server_response)
        notify(
            title=f"Successfully uploaded to {service_name}",
            message=server_response,
            timeout=10
        )
    else:
        error(
            title=f"Error: Upload to {service_name} unsuccessful",
            message=f"Server response: {server_response}",
            fatal=True
        )


def upload(filepath: str | Path, litterbox: bool = 0, expire_hours: int = 0) -> str:
    print("Debug: upload() function entered")

    if expire_hours not in {0, 1, 12, 24, 72}:
        error("Error: Invalid expiration time \"{expire_hours}\"")

    filepath = Path(filepath)

    if litterbox:
        url_root = "https://litterbox.catbox.moe"
    else:
        url_root = "https://catbox.moe"

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

    response_root = requests.get(url_root, headers=headers)
    cookie = response_root.headers['Set-Cookie']
    regex = re.search(r"PHPSESSID=([0-9a-z]+);", cookie)

    try:
        cookies = {'PHPSESSID': regex.group(1)}
    except AttributeError:
        error(f"Error: No PHPSESSID cookie found in {cookie}")

    form_boundary_id = ''
    for _ in range(32):
        form_boundary_id += random.choice(string.hexdigits[:16])
    form_boundary = "------geckoformboundary" + form_boundary_id

    headers.update({
        'Accept': 'application/json',
        'Referer': f'{url_root}',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': f'multipart/form-data; boundary={form_boundary[2:]}',
        'Origin': f'{url_root}',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
    })

    headers.pop('Sec-Fetch-User')
    headers.pop('Priority')

    try:
        with filepath.open('rb') as file:
            contents = file.read()
    except FileNotFoundError:
        error(f"Error: File \"{str(filepath)}\" not found", fatal=True)
    except IsADirectoryError:
        error(f"Error: \"{str(filepath)}\" is a directory", fatal=True)

    filename = filepath.parts[-1]

    if expire_hours:
        data = f'''
{form_boundary}
Content-Disposition: form-data; name="time"

{expire_hours}h
{form_boundary}
'''
    else:
        data = ''''''

    data += f'''{form_boundary}
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

    response_api = requests.post(f'{url_root}/{"resources/internals" if litterbox else "user"}/api.php',
                                 cookies=cookies, headers=headers, data=data)
    return response_api.text


def main():
    litterbox = input("Do you want to upload to Litterbox? (y/N): ")
    litterbox = True if litterbox.lower() in ('y', 'yes') else False
    if litterbox:
        expire_hours = input("Expiration time in hours: ")
        if expire_hours == '':
            expire_hours = 0
        try:
            expire_hours = int(expire_hours)
        except ValueError:
            error(f"Error: Invalid expiration time \"{expire_hours}\"")
    else:
        expire_hours = 0

    if expire_hours not in {0, 1, 12, 24, 48}:
        error(f"Error: Invalid expiration time \"{expire_hours}\"")

    if not sys.argv[1:]:
        filepath = Path(input("Input a file path: "))
        inform(upload(filepath=filepath, litterbox=litterbox, expire_hours=expire_hours), litterbox=litterbox)

    else:
        for filepath in sys.argv[1:]:
            inform(upload(filepath=filepath, litterbox=litterbox, expire_hours=expire_hours), litterbox=litterbox)


if __name__ == '__main__':
    # Non-interactive mode

    if sys.argv[1] == '--non-interactive':
        for filepath in sys.argv[2:]:
            inform(upload(filepath=filepath, litterbox=False, expire_hours=0), litterbox=False)
    else:
        main()
