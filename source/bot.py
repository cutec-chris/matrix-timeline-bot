from lib2to3.pytree import Base
from init import *
import functools,re,urllib.request,os,mimetypes,aiofiles,urllib.parse,os.path,bs4,feedparser
lastsend = None
class Server(Config):
    def __init__(self, room, **kwargs) -> None:
        self.avatars = []
        super().__init__(room, **kwargs)
@bot.listener.on_message_event
async def tell(room, message):
    global servers,lastsend
    match = botlib.MessageMatch(room, message, bot, prefix)
    if match.is_not_from_this_bot() and match.prefix()\
    and match.command("follow"):
        server = Server({
            'room': room.room_id,
            'feed': match.args()[1],
            'username': None,
            'password': None
        })
        if len(match.args())>3:
            server.password = match.args()[3]
        if len(match.args())>2:
            server.username = match.args()[2]
        if len(match.args())>4:
            server.apikey = match.args()[4]
        if len(match.args())>5:
            server.clientid = match.args()[5]
        servers.append(server)
        await save_servers()
        await bot.api.send_text_message(room.room_id, 'ok')
        loop.create_task(check_server(server))
    elif match.is_not_from_this_bot() and match.prefix()\
    and match.command("list"):
        txt = '###list:\n'
        for server in servers:
            if server.room == room.room_id:
                txt += '* '+server.feed+' '+str(server.username).replace('None','')+'\n'
        await bot.api.send_markdown_message(room.room_id, txt)
    elif match.is_not_from_this_bot() and match.prefix()\
    and match.command("unfollow"):
        for server in servers:
            if server.room == room.room_id:
                if server.feed == match.args()[1]:
                    servers.remove(server)
                    await bot.api.send_text_message(room.room_id, 'ok')
                    break
    elif match.is_not_from_this_bot():
        for server in servers:
            if server.room == room.room_id:
                pass
def extract_id(post):
    res = None
    if 'alt="tootid@' in str(post):
        res = post[post.find('alt="tootid@')+12:]
        res = res[:res.find('"')]
        try:
            res = int(res)
        except:
            res = None
    if 'alt="feedid@' in str(post):
        res = post[post.find('alt="feedid@')+12:]
        res = res[:res.find('"')]
    return res
@bot.listener.on_reaction_event
async def react(room, message, key):
    msg_id = message.source['content']['m.relates_to']['event_id']
    events = await get_room_events(bot.api.async_client,room.room_id,50)
    toot_id = None
    for event in events:
        if event.event_id == msg_id:
            if hasattr(event,'formatted_body'):
                toot_id = extract_id(event.formatted_body)
            break
    if toot_id:
        if key == '👍️'\
        or key == '⭐️':
            server._client.status_favourite(toot_id)
async def post_html_entry(server,html_body,sender,files=[],replyto=None):
    global servers
    #search for avatar 
    bs = bs4.BeautifulSoup(sender,features="lxml")
    for img in bs.findAll('img'):
        found = False
        for servera in servers:
            if not hasattr(server,'avatars'):
                server.avatars = []
            for avatar in servera.avatars:
                if avatar['src'] == img['src']:
                    found = True
                    img['src'] = avatar['dest']
        if not found: #and upload it if not found
            try:
                url = img['src']
                file = '/tmp/'+os.path.basename((urllib.parse.urlparse(url).path))
                urllib.request.urlretrieve(url, file)
                mimetype = mimetypes.guess_type(file)
                async with aiofiles.open(file, 'rb') as tmpf:
                    resp, maybe_keys = await bot.api.async_client.upload(tmpf,content_type=mimetype[0])
                navatar = {'src': img['src'],'dest': resp.content_uri}
                server.avatars.append(navatar)
                img['src'] = resp.content_uri
            except BaseException as e:
                logging.warning('failed to download avatar:'+str(e))
    sender = str(bs)
    furls = []
    for url in files:
        file = '/tmp/'+os.path.basename((urllib.parse.urlparse(url).path))
        urllib.request.urlretrieve(url, file)
        mimetype = mimetypes.guess_type(file)
        async with aiofiles.open(file, 'rb') as tmpf:
            resp, maybe_keys = await bot.api.async_client.upload(tmpf,content_type=mimetype[0])
        if url in html_body:
            html_body = html_body.replace(url,resp.content_uri)
        else:
            html_body += '<img src=\"%s\" alt="%s"></img>' % (resp.content_uri,os.path.basename((urllib.parse.urlparse(url).path)))
        #info = { 'h': img.height, 'w': img.width, 'mimetype': mimetype}
        #return resp.get('content_uri'), info
    mcontent={
        "msgtype": "m.text",#or m.notice seems to be shown more transparent
        "body": re.sub('<[^<]+?>', '', html_body),
        "format": "org.matrix.custom.html",
        "formatted_body": sender+'<br>'+html_body
        }
    if replyto:
        mcontent['m.relates_to'] = {
            "m.in_reply_to": {
                "event_id": replyto.event_id
            }
        }
    await bot.api.async_client.room_send(room_id=server.room,
                                          message_type="m.room.message",
                                          content=mcontent)
async def check_server(server):
    global lastsend,servers
    LastError = None
    if hasattr(server,'LastId'):
        LastId = server.LastId
    else:
        LastId = None
    if hasattr(server,'ConvLastId'):
        ConvLastId = server.ConvLastId
    else:
        ConvLastId = None
    while True:
        try:
            users = bot.api.async_client.rooms[server.room].users
            if len(users)==1:
                return False
        except: pass
        try:
            if hasattr(server,'apikey'): #at time we only support mastodon with api key
                try:
                    import mastodon
                    Mastodon = mastodon.Mastodon(
                        access_token=server.apikey,
                        api_base_url = server.feed
                    )
                except BaseException as e:
                    Mastodon = None #no mastodon instance ?
                if Mastodon:
                    try:
                        events = await get_room_events(bot.api.async_client,server.room,500)
                    except BaseException as e:
                        events = []
                    for event in events:
                        if hasattr(event,'formatted_body'):
                            nLastId = extract_id(event.formatted_body)
                            if nLastId:
                                LastId = nLastId
                                break
                    server._client = Mastodon
                    replyto = None
                    while True:
                        tl = Mastodon.timeline(min_id=LastId)
                        for toot in reversed(tl):
                            sender = '<img src=\"%s\" width="32" height="32"></img><a href=\"%s\">%s</a><font size="-1"> %s</font>&nbsp;<a href=\"%s\" alt="tootid@%s" style="display: none">🌐</a>' % (toot['account']['avatar'],toot['account']['url'],toot['account']['display_name'],toot['account']['acct'],toot['url'],toot['id'])
                            LastId = toot['id']
                            if toot['reblog']:
                                toot = toot['reblog']
                                sender += ' RT from <img src=\"%s\" width="32" height="32"></img><a href=\"%s\">%s</a><font size="-1"> %s</font>&nbsp;<a href=\"%s\" alt="tootid@%s" style="display: none">toot</a>' % (toot['account']['avatar'],toot['account']['url'],toot['account']['display_name'],toot['account']['acct'],toot['url'],toot['id'])
                            replyto = None
                            if toot['in_reply_to_id']:
                                events = await get_room_events(bot.api.async_client,server.room,100)
                                for event in events:
                                    if hasattr(event,'formatted_body'):
                                        if str(extract_id(event.formatted_body)) == str(toot['in_reply_to_id']):
                                            replyto = event
                            files = []
                            for media in toot['media_attachments']:
                                files.append(media['url'])
                            await post_html_entry(server,toot['content'],sender,files,replyto=replyto)
                            server.LastId = LastId
                            await save_servers()
                        if not '@' in server.feed:
                            tl = Mastodon.notifications(min_id=ConvLastId)
                            for toot in reversed(tl):
                                if toot['type'] == 'mention':
                                    sender = '<img src=\"%s\" width="32" height="32"></img><a href=\"%s\">%s</a><font size="-1"> %s</font>&nbsp;<a href=\"%s\" alt="tootid@%s" style="display: none">🌐</a>' % (toot['account']['avatar'],toot['account']['url'],toot['account']['display_name'],toot['account']['acct'],toot['status']['url'],toot['status']['id'])
                                    ConvLastId = toot['id']
                                    replyto = None
                                    if toot['status']['in_reply_to_id']:
                                        events = await get_room_events(bot.api.async_client,server.room,100)
                                        for event in events:
                                            if hasattr(event,'formatted_body'):
                                                if str(extract_id(event.formatted_body)) == str(toot['status']['in_reply_to_id']):
                                                    replyto = event
                                    files = []
                                    for media in toot['status']['media_attachments']:
                                        files.append(media['url'])
                                    #await post_html_entry(server,toot['status']['content'],sender,files,replyto=replyto)
                                    #server.ConvLastId = ConvLastId
                                elif toot['type'] == 'favourite':
                                    if toot['status']['in_reply_to_id']:
                                        events = await get_room_events(bot.api.async_client,server.room,100)
                                        for event in events:
                                            if hasattr(event,'formatted_body'):
                                                if str(extract_id(event.formatted_body)) == str(toot['status']['in_reply_to_id']):
                                                    replyto = event
                                    if replyto:
                                        mcontent={}
                                        mcontent['m.relates_to'] = {
                                            "m.annotation": {
                                                "event_id": replyto.event_id,
                                                "key": '⭐️'
                                            }
                                        }
                                        await bot.api.async_client.room_send(room_id=server.room,
                                                                            message_type="m.reaction",
                                                                            content=mcontent)
                                    server.ConvLastId = ConvLastId
                        await asyncio.sleep(60)
            else: #rss or atom feeds
                LastId = None
                if hasattr(server,'LastId'):
                    LastId = server.LastId
                while True:
                    try:
                        events = await get_room_events(bot.api.async_client,server.room,500)
                    except BaseException as e:
                        events = []
                    fetched = feedparser.parse(server.feed, agent="matrix-timeline-bot", etag=LastId)
                    for entry in reversed(fetched.entries):
                        dt = entry.updated_parsed
                        if not 'image' in fetched['feed']:
                            fetched['feed']['image'] = {'href':''}
                        sender = '<img src=\"%s\" width="32" height="32"></img><a href=\"%s\">%s</a><font size="-1"> %s</font>&nbsp;<a href=\"%s\" alt="feedid@%s" style="display: none">🌐</a>' % (fetched['feed']['image']['href'],fetched['feed']['link'],fetched['feed']['title'],'',entry['link'],entry['id'])
                        found = False
                        for event in events:
                            if hasattr(event,'formatted_body'):
                                if str(extract_id(event.formatted_body)) == str(entry['link'])\
                                or str(extract_id(event.formatted_body)) == str(entry['id']):
                                    found = True
                        if not found:
                            if entry.get('content'):
                                content = entry.content[0]['value']
                            elif entry.get('summary_detail'):
                                content = entry.summary_detail['value']
                            bs = bs4.BeautifulSoup(content,features="lxml")
                            files = []
                            #add first image to post
                            for img in bs.findAll('img'):
                                files.append(img['src'])
                                break
                            if not entry.title in content:
                                content = ('<strong><a href=\"%s\">%s</a></strong><br><br>' % (entry.link,entry.title)+content)
                            await post_html_entry(server,content,sender,files)
                    if 'etag' in fetched:
                        LastId = fetched['etag']
                    server.LastId = LastId
                    await save_servers()
                    await asyncio.sleep(60*5)
        except BaseException as e:
            err = str(e)
            if 'HTTPSConnectionPool' in err:
                err = 'Connection lost'
            if err != LastError:
                LastError = err
                await bot.api.send_text_message(server.room,str(e))
                await asyncio.sleep(5*60)
        await asyncio.sleep(3*60)
try:
    with open('data.json', 'r') as f:
        nservers = json.load(f)
        for server in nservers:
            servers.append(Server(server))
except BaseException as e: 
    logging.error('Failed to read data.json:'+str(e))
    exit(1)
@bot.listener.on_startup
async def startup(room):
    global loop,servers
    loop = asyncio.get_running_loop()
    for server in servers:
        if server.room == room:
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
            list:
                list all feeds in this room
            unfollow:
                command: unfollow feed_url
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
