#%%
import simplematrixbotlib as botlib
import os
from dotenv import load_dotenv
load_dotenv(".env")
MATRIX_SERVER_URL = os.getenv("MATRIX_SERVER_URL")
MATRIX_USERNAME = os.getenv("MATRIX_USERNAME")
MATRIX_PASSWORD = os.getenv("MATRIX_PASSWORD")

creds = botlib.Creds(MATRIX_SERVER_URL, MATRIX_USERNAME, MATRIX_PASSWORD)
bot = botlib.Bot(creds)

db = { "messages": {} }

@bot.listener.on_startup
async def on_startup(arg):
    room_id = arg
    print(f"Startup: joined room {room_id}")


@bot.listener.on_message_event
async def on_message_event(room, message):
    print("------------ on_message ------------")
    room_id = room.room_id # !rYxxSjtAOKXDifduyW:matrix.znurre.com
    room_name = room.display_name
    sender = message.sender # '@xinux:matrix.znurre.com'
    body = message.body
    # event_id = message.source["event_id"] # '$lKT6skTe'
    # content = message.source["content"]
    # is_edit = "m.new_content" in content
    # new_content = content["m.new_content"] if is_edit else None
    # relates_to = content["m.relates_to"] if is_edit else None
    # msgtype = content["msgtype"] # 'm.text'

    sender_display_name = sender[1:].split(":")[0]
    text = f"{sender_display_name}: {body}"

    # clean up room_id so it can be used as a filename
    file_name = room_id.replace("!", "_").replace(":", "_").replace(".", "-")

    # append message to roomid.html
    open(f"www/{file_name}.html", "a").write(f"{text}<br>")


await bot.main()
