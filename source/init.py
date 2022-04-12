import simplematrixbotlib as botlib,yaml,json,asyncio,nio
with open('config.yml', 'r') as file:
    config = yaml.safe_load(file)
try: 
    prefix = config['server']['prefix']
except:
    prefix = config['server']['user']
creds = botlib.Creds(config['server']['url'], config['server']['user'], config['server']['password'])
bot = botlib.Bot(creds)
def is_valid_event(event):
    events = (nio.RoomMessageFormatted, nio.RedactedEvent)
    events += (nio.RoomMessageMedia, nio.RoomEncryptedMedia)
    return isinstance(event, events)
async def fetch_room_events(
    client,
    start_token: str,
    room,
    direction,
) -> list:
    events = []
    while True:
        response = await client.room_messages(
            room.room_id, start_token, limit=1000, direction=direction
        )
        if len(response.chunk) == 0:
            break
        events.extend(event for event in response.chunk if is_valid_event(event))
        start_token = response.end
    return events
async def get_room_events(client, room):
    sync_resp = await client.sync(
        full_state=True, sync_filter={"room": {"timeline": {"limit": 1}}}
    )
    start_token = sync_resp.rooms.join[room].timeline.prev_batch
    # Generally, it should only be necessary to fetch back events but,
    # sometimes depending on the sync, front events need to be fetched
    # as well.
    events = await fetch_room_events(client,start_token,bot.api.async_client.rooms[room],nio.MessageDirection.back)
    return events
