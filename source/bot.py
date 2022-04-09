from init import *
servers = []
loop = None
lastsend = None
@bot.listener.on_message_event
async def tell(room, message):
    global servers,lastsend
    match = botlib.MessageMatch(room, message, bot, prefix)
    if match.is_not_from_this_bot() and match.prefix()\
    and match.command("follow"):
        server = {
            'room': room.room_id,
            'feed': match.args()[1],
            'username': None,
            'password': None
        }
        if len(match.args())>3:
            server['password'] = match.args()[3]
        if len(match.args())>2:
            server['username'] = match.args()[2]
        servers.append(server)
        loop.create_task(check_server(server))
        with open('data.json', 'w') as f:
            json.dump(servers,f, skipkeys=True)
        await bot.api.send_text_message(room.room_id, 'ok')
    elif match.is_not_from_this_bot():
        for server in servers:
            if server['room'] == room.room_id and '_client' in server:
                break
        if server['room'] != room.room_id: return
async def check_server(server):
    global lastsend,servers
    def update_server_var():
        for server_r in servers:
            if server_r['room'] == server['room']\
            and server_r['url'] == server['url']:
                server_r = server
    while True:
        try:
        except BaseException as e:
            pass
        await asyncio.sleep(5)
@bot.listener.on_startup
async def startup(room):
    global loop,servers
    loop = asyncio.get_running_loop()
    try:
        with open('data.json', 'r') as f:
            servers = json.load(f)
    except: pass
    for server in servers:
        if server['room'] == room:
            loop.create_task(check_server(server))
@bot.listener.on_message_event
async def bot_help(room, message):
    bot_help_message = f"""
    Help Message:
        prefix: {prefix}
        commands:
            follow:
                command: follow mastodon/twitter/feed [username] [password]
                description: follow feed or timeline in this room
            help:
                command: help, ?, h
                description: display help command
                """
    match = botlib.MessageMatch(room, message, bot, prefix)
    if match.is_not_from_this_bot() and match.prefix() and (
       match.command("help") 
    or match.command("?") 
    or match.command("h")):
        await bot.api.send_text_message(room.room_id, bot_help_message)
bot.run()