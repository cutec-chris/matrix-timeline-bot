from init import *
import functools,re,urllib.request,os,mimetypes,aiofiles,urllib.parse,os.path
servers = []
loop = None
lastsend = None
async def save_servers():
    global servers
    with open('data.json', 'w') as f:
        json.dump(servers,f, skipkeys=True)
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
        await save_servers()
        await bot.api.send_text_message(room.room_id, 'ok')
    elif match.is_not_from_this_bot():
        for server in servers:
            if server['room'] == room.room_id:
                pass
async def post_html_entry(room,html_body,sender,files=[]):
    furls = []
    for url in files:
        file = '/tmp/'+os.path.basename((urllib.parse.urlparse(url).path))
        urllib.request.urlretrieve(url, file)
        mimetype = mimetypes.guess_type(file)
        async with aiofiles.open(file, 'rb') as tmpf:
            resp, maybe_keys = await bot.api.async_client.upload(tmpf,content_type=mimetype[0])
            print(resp,maybe_keys)
        if url in html_body:
            html_body.replace(url,resp.content_uri)
        else:
            html_body += '<img href="%s"></img>' % resp.content_uri
        #info = { 'h': img.height, 'w': img.width, 'mimetype': mimetype}
        #return resp.get('content_uri'), info
    await bot.api.async_client.room_send(room_id=room,
                                          message_type="m.room.message",
                                          content={
                                              "msgtype": "m.text",#or m.notice seems to be shown more transparent
                                              "body": re.sub('<[^<]+?>', '', html_body),
                                              "format": "org.matrix.custom.html",
                                              "formatted_body": sender+'<br>'+html_body})
async def check_server(server):
    global lastsend,servers
    def update_server_var():
        for server_r in servers:
            if server_r['room'] == server['room']\
            and server_r['feed'] == server['feed']:
                server_r = server
    LastError = None
    if 'LastId' in server:
        LastId = server['LastId']
    else:
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
                    while True:
                        tl = Mastodon.timeline(min_id=LastId)
                        for toot in reversed(tl):
                            sender = '<img src=\"%s\"></img><a href=\"%s\">%s</a><font size="-1"> %s</font>&nbsp;<a href=\"%s\" style="display: none">toot</a>' % (toot['account']['avatar'],toot['account']['url'],toot['account']['display_name'],toot['account']['acct'],toot['url'])
                            if toot['reblog']:
                                toot = toot['reblog']
                                sender += ' RT from <img src=\"%s\"></img><a href=\"%s\">%s</a><font size="-1"> %s</font>&nbsp;<a href=\"%s\" style="display: none">toot</a>' % (toot['account']['avatar'],toot['account']['url'],toot['account']['display_name'],toot['account']['acct'],toot['url'])
                            if toot['in_reply_to_id']:
                                events = await get_room_events(bot.api.async_client,server['room'])
                            files = []
                            for media in toot['media_attachments']:
                                files.append(media['url'])
                            await post_html_entry(server['room'],toot['content'],sender,files)
                            LastId = toot['id']
                            server['LastId'] = LastId
                            #update_server_var()
                            #await save_servers()
                        await asyncio.sleep(60)
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
                rss/atom feeds only the url (and username and passwort when auth is needed)
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