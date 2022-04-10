from init import *
import functools,markdownify
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
        if len(match.args())>4:
            server['apikey'] = match.args()[4]
        if len(match.args())>5:
            server['clientid'] = match.args()[5]
        servers.append(server)
        loop.create_task(check_server(server))
        with open('data.json', 'w') as f:
            json.dump(servers,f, skipkeys=True)
        await bot.api.send_text_message(room.room_id, 'ok')
    elif match.is_not_from_this_bot():
        for server in servers:
            if server['room'] == room.room_id:
                pass
async def post_entry(room,body,html_body,sender):
    await bot.api.async_client.room_send(room_id=room,
                                          message_type="m.room.message",
                                          content={
                                              "msgtype": "m.text",
                                              "body": body,
                                              "format": "org.matrix.custom.html",
                                              "formatted_body": sender+'<br>'+html_body})
async def check_server(server):
    global lastsend,servers
    def update_server_var():
        for server_r in servers:
            if server_r['room'] == server['room']\
            and server_r['url'] == server['url']:
                server_r = server
    LastError = None
    LastId = None
    while True:
        try:
            if 'apikey' in server: #at time we only support mastodon with api key
                try:
                    import mastodon
                    Mastodon = mastodon.Mastodon(
                        access_token=server['apikey'],
                        api_base_url = server['feed']
                    )
                except BaseException as e:
                    Mastodon = None #no mastodon instance ?
                if Mastodon:
                    #events = await get_room_events(bot.api.async_client,server['room'])
                    tl = Mastodon.timeline(min_id=LastId)
                    if len(tl)>0:
                        LastId =  tl[0]['id']
                    for toot in tl:
                        sender = '<img src=\"%s\"></img><a href=\"%s\">%s</a><font size="-1"> %s</font>' % (toot['account']['avatar'],toot['account']['url'],toot['account']['display_name'],toot['account']['acct'])
                        if toot['reblog']:
                            sender = toot['account']
                            toot = toot['reblog']
                        await post_entry(server['room'],toot['card']['description'],toot['content'],sender)
                        break
        except BaseException as e:
            if str(e) != LastError:
                LastError = str(e)
                await bot.api.send_text_message(server['room'],str(e))
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
                command: follow feed_url [username] [password] [api key]
                description: follow feed or timeline in this room
                mastodon needs all fields filled
                rss/atom feeds only the url (and username and apsswort when auth is needed)
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