import sys
import os
import re
from os import path
import subprocess
import json
import requests
import bs4
import dateparser
import tempfile
from datetime import datetime, timedelta
from werkzeug.contrib.cache import FileSystemCache

from flask import Flask, request, render_template

app = Flask(__name__)
cache_dir = tempfile.TemporaryDirectory(prefix="ilswlol-")
cache = FileSystemCache(cache_dir.name)

def ist_lukas_schon_wach():
    confidence = 0

    # Check using steam profile
    steamprofile = requests.get("http://steamcommunity.com/id/Ahti333")
    soup = bs4.BeautifulSoup(steamprofile.text, "html.parser")

    online_offline_info = soup.find(class_='responsive_status_info')

    # Check whether user is online or offline right now
    if online_offline_info.find_all(text='Currently Online') or \
       online_offline_info.find_all(text=re.compile('Online using')) or \
       online_offline_info.find_all(text=re.compile('Currently In-Game')):
        # If he's online in steam now, we're pretty confident
        confidence += 70
    else:
        last_online = online_offline_info.find(class_='profile_in_game_name').string
        last_online_date = last_online.replace('Last Online ', '')
        date = dateparser.parse(last_online_date)
        delta = datetime.utcnow() - date

        # Check whether Lukas has been online recently and assign confidence
        if delta < timedelta(hours=1):
            confidence += 40
        elif delta < timedelta(hours=3):
            confidence += 30
        elif delta < timedelta(hours=7):
            confidence += 20

    # Check using telegram

    # For development purposes, figure out the path ourselves
    tg_path = None
    if os.environ.get('TG_PATH') is None:
        tg_path = path.join(path.dirname(sys.executable), "..", "..", "externals", "tg")
    else:
        tg_path = os.environ.get('TG_PATH')

    tg_cli_path = path.join(tg_path, "bin", "telegram-cli")
    tg_pubkey_path = path.join(tg_path, "tg-server.pub")

    tg_output = None
    # Retry a few times in case the token has expired
    attempt = 3
    success = False
    while attempt > 0 and not success:
        tg_output = subprocess.run([tg_cli_path, "-k", tg_pubkey_path,
                                    "-e", "contact_list", "--json", "-D", "-R"],
                                   stdout=subprocess.PIPE)
        if tg_output.returncode != 0:
            attempt -= 1
        else:
            success = True

    split_contacts = tg_output.stdout.splitlines()[0].decode("utf-8")
    parsed_contacts = json.loads(split_contacts)
    for contact in parsed_contacts:
        if 'username' in contact and contact['username'] == 'lukasovich':
            date = dateparser.parse(contact['when'])
            delta = datetime.utcnow() - date

            # Check whether Lukas has been online recently and assign confidence
            if delta < timedelta(minutes=5):
                confidence += 70
            if delta < timedelta(minutes=45):
                confidence += 50
            elif delta < timedelta(hours=1):
                confidence += 40
            elif delta < timedelta(hours=3):
                confidence += 30
            elif delta < timedelta(hours=7):
                confidence += 20

            break

    return confidence >= 50


@app.route("/")
def index():
    # We automatically enable raw output for curl users
    raw_output = True if request.args.get('raw') != "False" else False
    if request.headers.get('User-Agent', '').startswith("curl") and \
       not raw_output == False and request.args.get('raw') is not None:
        raw_output = True
    
    schon_wach = cache.get('ist_lukas_schon_wach')
    if schon_wach is None:
        schon_wach = ist_lukas_schon_wach()
        cache.set('ist_lukas_schon_wach', schon_wach, timeout=5 * 60)

    if schon_wach:
        if raw_output:
            return "JA"
        else:
            return render_template('index.html', schon_wach=True)
    else:
        if raw_output:
            return "NEIN"
        else:
            return render_template('index.html', schon_wach=False)

if __name__ == "__main__":
    app.run()
