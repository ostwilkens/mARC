#%%
import os
import time
import requests
import json
import sqlite3
import chevron
from dotenv import load_dotenv

load_dotenv(".env")
MATRIX_SERVER_URL = os.getenv("MATRIX_SERVER_URL")
MATRIX_ACCESS_TOKEN = os.getenv("MATRIX_ACCESS_TOKEN")


template = open("template.html", "r").read()
db = sqlite3.connect("db.sqlite")
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS messages (event_id text PRIMARY KEY, room_id text, sender text, sender_display_name text, timestamp integer, body text)")
cursor.execute("CREATE TABLE IF NOT EXISTS rooms (room_id text PRIMARY KEY, display_name text NULL)")
cursor.execute("CREATE TABLE IF NOT EXISTS store (key text PRIMARY KEY, value text)")
cursor.execute("CREATE TABLE IF NOT EXISTS members (room_id text, user_id text, displayname text, PRIMARY KEY (room_id, user_id))")
db.commit()


def render(timestamp, only_room_id=None):
    my_user_id = cursor.execute("SELECT value FROM store WHERE key = 'my_user_id'").fetchone()[0]

    cursor.execute("SELECT DISTINCT rooms.room_id, rooms.display_name, first_room_member_displayname, member_count FROM rooms LEFT JOIN (SELECT room_id, displayname AS first_room_member_displayname FROM members WHERE user_id != ? GROUP BY room_id) AS hehu ON rooms.room_id = hehu.room_id LEFT JOIN (SELECT room_id, COUNT(*) AS member_count FROM members GROUP BY room_id) AS hehu2 ON rooms.room_id = hehu2.room_id ORDER BY rooms.display_name ASC",
                   (my_user_id,))
    rooms = [{ 
        "room_id": x[0], 
        "filename": x[0].replace("!", "_").replace(":", "_").replace(".", "-"),
        "display_name": x[1] or x[2] or x[0],
        "member_count": x[3]
    } for x in cursor.fetchall()]

    for room in rooms:
        if only_room_id and room["room_id"] != only_room_id:
            continue

        cursor.execute("SELECT sender, sender_display_name, timestamp, body FROM messages WHERE room_id = ? ORDER BY timestamp ASC", (room["room_id"],))
        messages = [{
            "sender": x[0], 
            "sender_display_name": x[1], 
            "timestamp": x[2],
            "body": x[3],
            "hhmm": time.strftime("%H:%M", time.localtime(x[2]/1000)),
        } for x in cursor.fetchall()]

        data = {
            "rooms": rooms,
            "messages": messages,
            "room_id": room["room_id"],
            "room_display_name": room["display_name"],
            "access_token": MATRIX_ACCESS_TOKEN,
            "build_batch_ts": timestamp
        }

        html = chevron.render(template, data)
        open(f"www/{room['filename']}.html", "w").write(html)


def fetch_whoami():
    url = f"https://matrix.znurre.com/_matrix/client/r0/account/whoami?access_token={MATRIX_ACCESS_TOKEN}"
    response = requests.get(url)
    data = json.loads(response.content)
    cursor.execute("INSERT OR REPLACE INTO store VALUES (?, ?)", ("my_user_id", data["user_id"]))


def fetch_rooms(since=None):
    url = f"https://matrix.znurre.com/_matrix/client/r0/sync?filter={{\"room\":{{\"timeline\":{{\"limit\":1}}}}}}&access_token={MATRIX_ACCESS_TOKEN}"

    if since:
        url += f"&since={since}"

    response = requests.get(url)
    data = json.loads(response.content)

    if "account_data" in data:
        for event in data["account_data"]["events"]:
            if event["type"] == "m.direct":
                content = event["content"]
                for user_id, room_ids in content.items():
                    for room_id in room_ids:
                        # add user as member to room
                        cursor.execute("INSERT OR IGNORE INTO members VALUES (?, ?, NULL)", (room_id, user_id))

    if "rooms" in data:
        for room_id, room in data["rooms"]["join"].items():
            
            cursor.execute("INSERT OR IGNORE INTO rooms VALUES (?, NULL)", (room_id,))

            for event in room["state"]["events"]:

                if event["type"] == "m.room.member":
                    content = event["content"]

                    if content["membership"] == "join":
                        displayname = content.get("displayname") or event["sender"][1:].split(":")[0]
                        cursor.execute("INSERT OR IGNORE INTO members VALUES (?, ?, ?)", (room_id, event["sender"], displayname))
                        
                        # update displayname of member
                        cursor.execute("UPDATE members SET displayname = ? WHERE user_id = ?", (displayname, event["sender"]))

                    elif content["membership"] == "leave":
                        cursor.execute("DELETE FROM members WHERE room_id = ? AND user_id = ?", (room_id, event["sender"]))

                if event["type"] == "m.room.name":
                    room_name = event["content"]["name"]

                    # update name
                    cursor.execute("UPDATE rooms SET display_name = ? WHERE room_id = ?", (room_name, room_id))
                    
    db.commit()


def fetch_events(since=None):
    url = f"https://matrix.znurre.com/_matrix/client/r0/sync?timeout=30000&access_token={MATRIX_ACCESS_TOKEN}"

    if since:
        url += f"&since={since}"

    response = requests.get(url)
    data = json.loads(response.content)

    next_batch = data["next_batch"]
    cursor.execute("INSERT OR REPLACE INTO store VALUES (?, ?)", ("next_batch", next_batch))
    db.commit()
    
    if data.get("rooms") and data["rooms"].get("join"):
        for room_id, room in data["rooms"]["join"].items():

            for event in room["state"]["events"]:
                if event["type"] == "m.room.name":
                    room_name = event["content"]["name"]

                    # store room in db
                    cursor.execute("INSERT OR IGNORE INTO rooms VALUES (?, ?)", (room_id, room_name))
                    db.commit()
            
            for event in room["timeline"]["events"]:
                if event["type"] == "m.room.message" and event["content"]["msgtype"] == "m.text":
                    body = event["content"]["body"]
                    sender = event["sender"]
                    sender_display_name = sender[1:].split(":")[0]
                    timestamp = event["origin_server_ts"]

                    # store message in db
                    cursor.execute("INSERT OR IGNORE INTO messages VALUES (?, ?, ?, ?, ?, ?)", (event["event_id"], room_id, sender, sender_display_name, timestamp, body))
                    db.commit()
            
            # render room
            render(next_batch, room_id)

    return next_batch


fetch_whoami()

since = (cursor.execute("SELECT value FROM store WHERE key = 'next_batch'").fetchone() or (None,))[0]

fetch_rooms(since)

while True:
    since = fetch_events(since)

db.close()
