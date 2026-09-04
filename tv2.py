import requests
import re
import json
import math
import time
from datetime import datetime, timedelta
import html
import csv
import os

cache_path = 'bydate'

headers = {
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'Pragma': 'no-cache',
    'Referer': 'https://tv.yandex.ru/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
    'X-TV-SK': None,
    'sec-ch-ua': '"Chromium";v="152", "Not?A_Brand";v="24", "Google Chrome";v="152"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

xml_lines = [
    '<?xml version="1.0" encoding="utf-8" ?>',
    '<!DOCTYPE tv SYSTEM "xmltv.dtd">',
    '<tv generator-info-name="TiviMateChannels">'
]
all_yandex_ids = []

session = requests.Session()


def step_1():
    session.cookies['yandex_gid'] = '213'
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    response = session.get('https://tv.yandex.ru/?grid=all')
    match = re.search(r'window\.__INITIAL_SK__\s*=\s*\{"key":"([^"]+)"', response.text)
    headers['X-TV-SK'] = match.group(1)


def step_2(date):
    session.cookies['yandex_gid'] = '213'
    params = {
        'page': '0',
        'date': date,
        'period': 'all-day',
        'offset': 0,
        'limit': '24',
    }
    session.headers = headers
    total_results = 520
    limit = 24
    total_pages = math.ceil(total_results / limit)
    all_channels = []
    for page in range(total_pages):
        print(f"requesting page {page} for {date}")
        params['offset'] = page * limit
        response = session.get('https://tv.yandex.ru/api/213/main/chunk', params=params)
        all_channels.extend(response.json()['schedules'])
        time.sleep(0.5)
    with open(f"{cache_path}/{date}.json", "w", encoding="utf-8") as f:
        json.dump(all_channels, f, ensure_ascii=False)
    return all_channels


def make_channels(tivimate_name, yandex_id):
    xml_lines.append(f'     <channel id="{yandex_id}">')
    xml_lines.append(f'         <display-name>{tivimate_name}</display-name>')
    xml_lines.append('      </channel>')


def read_mapping():
    with open('channels_mapping.csv', mode='r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=',')
        next(reader)

        seen_ids = set()

        for row in reader:
            tivimate_name = str(html.escape(row[0].strip()))
            yandex_id = str(row[1].strip())

            if yandex_id in seen_ids:
                continue
            seen_ids.add(yandex_id)
            all_yandex_ids.append(yandex_id)

            make_channels(tivimate_name, yandex_id)


def serv_json():
    # with open('channels_only_10.json', 'r', encoding='utf-8') as f:
    with open('channels.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def time_format(data_time):
    return datetime.fromisoformat(data_time).strftime('%Y%m%d%H%M%S %z')


def program_tags(event, ch_id):
    xml_lines.append(f'   <programme start="{time_format(event['start'])}" stop="{time_format(event['finish'])}"'
                     f' channel="{ch_id}">')
    xml_lines.append(f'       <title lang="ru">{str(html.escape(event['title']))}</title>')
    xml_lines.append(f'   </programme>')


def remove_old_dates():
    print("removing old dates ...")
    today = datetime.now().date()
    yesterday = str(today - timedelta(days=1))
    all_cache = os.listdir(cache_path)
    for ac in all_cache:
        if ac.replace('.json', '') < yesterday:
            os.remove(os.path.join(cache_path, ac))
            print(f"delete {ac}")
    print('-------------------')


def get_current_date():
    today = datetime.now().date()

    current_dates = {
        str(today - timedelta(days=1)),
        str(today),
        str(today + timedelta(days=1)),
        str(today + timedelta(days=2))
    }
    cached_dated_cleared = {f.replace('.json', '') for f in os.listdir(cache_path)}
    missing_dates = current_dates - cached_dated_cleared
    return missing_dates


remove_old_dates()
curr_date = get_current_date()

sk_key = step_1()

for cd in curr_date:
    step_2(cd)

read_mapping()

data = []
print("ganerate Tv Programm...")

# for date_chunk in sorted(os.listdir(cache_path)):
#     with open(os.path.join(cache_path, date_chunk), "r", encoding="utf-8") as f:
#         data.extend(json.load(f))
#
# for item in data:
#     channel_id = str(item['channel']['id'])
#     if channel_id not in all_yandex_ids:
#         continue
#     for event in item['events']:
#         program_tags(event, channel_id)

xml_lines.append(f'</tv>')
with open('zzzfinal.xml', 'w', encoding='utf-8') as f:
    f.write('\n'.join(xml_lines))
print("END")
