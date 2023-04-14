#%%
import simplematrixbotlib as botlib
import os
import time
from dotenv import load_dotenv
load_dotenv(".env")
MATRIX_SERVER_URL = os.getenv("MATRIX_SERVER_URL")
MATRIX_USERNAME = os.getenv("MATRIX_USERNAME")
MATRIX_PASSWORD = os.getenv("MATRIX_PASSWORD")

creds = botlib.Creds(MATRIX_SERVER_URL, MATRIX_USERNAME, MATRIX_PASSWORD)
bot = botlib.Bot(creds)

db = { "messages": {} }

open("www/room_list.html", "w").write(open("www/room_list.template.html", "r").read())


@bot.listener.on_startup
async def on_startup(room_id):
    room = bot.async_client.rooms[room_id]
    print(f"Startup: joined room {room_id}, user count: {len(room.users)}")

    if len(room.users) <= 1:
        return

    room.display_name
    file_name = room_id.replace("!", "_").replace(":", "_").replace(".", "-")
    room_link = f"<a target='_parent' href='/?room={file_name}'>{room.display_name}</a>"

    with open(f"www/room_list.html", "a") as f:
        f.write(f"{room_link}<br>")

    with open(f"www/rooms/{file_name}.html", "a+") as f:
        is_empty = f.tell() == 0
        if is_empty:
            f.write(open("www/room.template.html", "r").read())



@bot.listener.on_message_event
async def on_message_event(room, message):
    print("------------ on_message ------------")
    room_id = room.room_id # !rYxxSjtAOKXDifduyW:matrix.znurre.com
    # room_name = room.display_name
    sender = message.sender # '@xinux:matrix.znurre.com'
    body = message.body
    # event_id = message.source["event_id"] # '$lKT6skTe'
    # content = message.source["content"]
    # is_edit = "m.new_content" in content
    # new_content = content["m.new_content"] if is_edit else None
    # relates_to = content["m.relates_to"] if is_edit else None
    # msgtype = content["msgtype"] # 'm.text'

    sender_display_name = sender[1:].split(":")[0]
    unix_timestamp = message.source["origin_server_ts"]
    hhmm = time.strftime("%H:%M", time.localtime(unix_timestamp/1000))
    text = f"<span>[{hhmm}] &lt;{sender_display_name}&gt; {body}</span>"

    # clean up room_id so it can be used as a filename
    file_name = room_id.replace("!", "_").replace(":", "_").replace(".", "-")

    # append message to roomid.html
    open(f"www/rooms/{file_name}.html", "a").write(f"{text}<br>")


await bot.main()

