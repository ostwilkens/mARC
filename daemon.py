#%%
import os
import sqlite3
import requests
import json

def fetch_whoami(db, cursor):
    cursor.execute("SELECT value FROM store WHERE key = 'access_token'")
    access_token = cursor.fetchone()[0]
    cursor.execute("SELECT value FROM store WHERE key = 'homeserver'")
    homeserver = cursor.fetchone()[0]

    url = f"{homeserver}_matrix/client/r0/account/whoami?access_token={access_token}"
    response = requests.get(url)
    data = json.loads(response.content)
    cursor.execute("INSERT OR REPLACE INTO store VALUES (?, ?)", ("my_user_id", data["user_id"]))


def fetch_rooms(db, cursor, since=None):
    cursor.execute("SELECT value FROM store WHERE key = 'access_token'")
    access_token = cursor.fetchone()[0]
    cursor.execute("SELECT value FROM store WHERE key = 'homeserver'")
    homeserver = cursor.fetchone()[0]

    url = f"{homeserver}_matrix/client/r0/sync?filter={{\"room\":{{\"timeline\":{{\"limit\":1}}}}}}&access_token={access_token}"

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


def fetch_events(db, cursor, since=None):
    cursor.execute("SELECT value FROM store WHERE key = 'access_token'")
    access_token = cursor.fetchone()[0]

    url = f"https://matrix.znurre.com/_matrix/client/r0/sync?timeout=30000&access_token={access_token}"

    if since is not None:
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
                if event["type"] == "m.room.message" and event["content"].get("msgtype") == "m.text":
                    body = event["content"]["body"]
                    sender = event["sender"]
                    sender_display_name = sender[1:].split(":")[0]
                    timestamp = event["origin_server_ts"]

                    # store message in db
                    cursor.execute("INSERT OR IGNORE INTO messages VALUES (?, ?, ?, ?, ?, ?)", (event["event_id"], room_id, sender, sender_display_name, timestamp, body))
                    db.commit()
                elif event["type"] == "m.reaction":
                    print(event)
                    sender = event["sender"] # @xinux:matrix.znurre.com
                    content = event["content"] # {"m.relates_to": {"event_id": "$event_id", "key": "👍", "rel_type": "m.annotation"}}
                    
                    if "m.relates_to" not in content:
                        print("WTF?")
                        print(event)
                        continue
                    
                    message_id = content["m.relates_to"]["event_id"]
                    key = content["m.relates_to"]["key"]

                    # store reaction in db
                    cursor.execute("INSERT OR IGNORE INTO reactions VALUES (?, ?, ?)", (message_id, key, sender))
                    db.commit()
                else:
                    print(f"Unknown event type: {event['type']}")
            
            # render room
            # render(next_batch, room_id)

    return next_batch




for db_filename in os.listdir('./db'):
    if not db_filename.endswith('.sqlite3'):
        continue

    db_path = os.path.join('./db', db_filename)
    db = sqlite3.connect(db_path)
    cursor = db.cursor()

    cursor.execute("CREATE TABLE IF NOT EXISTS messages (event_id text PRIMARY KEY, room_id text, sender text, sender_display_name text, timestamp integer, body text)")
    cursor.execute("CREATE TABLE IF NOT EXISTS rooms (room_id text PRIMARY KEY, display_name text NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS store (key text PRIMARY KEY, value text)")
    cursor.execute("CREATE TABLE IF NOT EXISTS members (room_id text, user_id text, displayname text, PRIMARY KEY (room_id, user_id))")
    cursor.execute("CREATE TABLE IF NOT EXISTS reactions (event_id text, key text, sender text)")
    db.commit()

    fetch_whoami(db, cursor)

    since = (cursor.execute("SELECT value FROM store WHERE key = 'next_batch'").fetchone() or (None,))[0]
    # since = None

    fetch_rooms(db, cursor, since)

    while True:
        since = fetch_events(db, cursor, since)
        break

    db.close()
