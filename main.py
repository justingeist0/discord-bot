import os
from discord import Intents
from discord.ext import tasks
from discord.ext import commands
from discord.ext.commands import Context
from discord.utils import get

TOKEN: str = os.getenv("DISCORD_BOT_TOKEN")

COMMAND_PREFIX = '!'
INTENTS = Intents.default()
INTENTS.members = True
BOT = commands.Bot(command_prefix='!', intents=INTENTS)

WL_COMMAND = 'wl'
RESERVE_COMMAND = 'reserve'
INTEREST_COMMAND = 'interest'
MY_CASH_APPS_COMMAND = 'mycashapps'
PING_COMMAND = 'ping'
HELP_COMMAND = 'pighelp'
CLEAR_COMMAND = 'clear'
TOGGLE_AUTO_POST_COMMAND = 'toggle'
RANK_REQUEST_COMMAND = 'rolerequest'
NO_AUTO_POST_USER_ID = set()
ACTIVE_GAMES_CHANNEL = 'active-games'
CASH_APPS_CHANNEL = 'cashapp-and-venmos'
HELP_MESSAGE_HOST = \
    '*Poker Pig Help:*\n'\
    '**%s**: Show help message.' % (COMMAND_PREFIX + HELP_COMMAND) + '\n'\
    '**%s**: Ping poker pig.' % (COMMAND_PREFIX + PING_COMMAND) + '\n'\
    '**%s**: Fetch all your images from cashapp-and-venmos.' % (COMMAND_PREFIX + MY_CASH_APPS_COMMAND) + '\n' \
    '**%s**: Create a wait list.' % (COMMAND_PREFIX + WL_COMMAND) + '\n' \
    '**%s**: Create a reservation wait list.' % (COMMAND_PREFIX + RESERVE_COMMAND) + '\n' \
    '**%s**: Toggle auto call !wl & !mycashapps in the channel %s' % ((COMMAND_PREFIX + TOGGLE_AUTO_POST_COMMAND), ACTIVE_GAMES_CHANNEL) + '\n'\
    '**%s** *optional*@{Someone}: Delete all messages from yourself or someone else in active-games.' % (COMMAND_PREFIX + CLEAR_COMMAND) + '\n'\
    '\nAdmin only:\n'\
    '**%s** @{Role}: Create a message to request a rank.' % (COMMAND_PREFIX + RANK_REQUEST_COMMAND) + '\n'\
    '**%s** {Game Description}: Create a wait list to find interested players.' % (COMMAND_PREFIX + INTEREST_COMMAND)
    #'*Poker Pig last updated on 3/03/2021, 6/2/2021*'
MENTION_STR = '<@!%s>'
WAIT_LIST_EMPTY_STR = '*No one*'
POKER_NOW_LINK = 'pokernow.club'
WAIT_EMOJI = '💺'
RANK_REQUEST_EMOJI = '👋'

INTERESTED_PLAYERS = set()


class InterestedPlayer:
    def __init__(self, user_id, channel_id, wl_message_id):
        self.user_id = user_id
        self.channel_id = channel_id
        self.wl_message_id = wl_message_id
        self.minutes_left = 60
        print("created interested player")

    def tick_expired(self):
        self.minutes_left -= 1
        print(self.minutes_left)
        return self.minutes_left <= 0


@tasks.loop(minutes=1)
async def tick_every_minute():
    expired = set(ip for ip in INTERESTED_PLAYERS if ip.tick_expired())
    for e in expired:
        await remove_from_wait_list(
            await BOT.get_channel(e.channel_id).fetch_message(e.wl_message_id),
            e.user_id
        )


@BOT.event
async def on_ready():
    print('We have logged in as {0.user}'.format(BOT))
    tick_every_minute.start()


def can_host(ctx):
    for role in ctx.message.author.roles:
        if True in (host in str(role).lower() for host in ('host', 'floor', 'admin')):
            return True


def is_admin(ctx):
    for role in ctx.message.author.roles:
        if True in (host in str(role).lower() for host in ('floor', 'admin')):
            return True


@BOT.command(name=PING_COMMAND)
async def ping(ctx: Context):
    await ctx.message.reply('Pong! (' + str(round(BOT.latency * 100)) + 'ms)')


@BOT.command(name=HELP_COMMAND)
async def poker_pig_help(ctx: Context):
    if can_host(ctx):
        await ctx.message.reply(HELP_MESSAGE_HOST)


async def start_wait_list(ctx, header_str: str, footer_str: str):
    message_to_send = header_str + ("\n%s\n\n" % WAIT_LIST_EMPTY_STR) + footer_str
    sent = await ctx.message.channel.send(message_to_send)
    await sent.add_reaction(WAIT_EMOJI)


@BOT.command(name=WL_COMMAND)
async def wl(ctx: Context):
    if can_host(ctx):
        await start_wait_list(
            ctx,
            "**Wait List | Host %s:**" % (MENTION_STR % ctx.author.id),
            "React with :seat: to be added"
        )


@BOT.command(name=RESERVE_COMMAND)
async def reserve(ctx: Context):
    if can_host(ctx):
        await start_wait_list(
            ctx,
            "**Reserved Players | Host %s:**" % (MENTION_STR % ctx.author.id),
            "React with :seat: to reserve"
        )


def get_channel(ctx: Context, channel_substr: str):
    for channel in ctx.message.guild.text_channels:
        if channel_substr in str(channel):
            return channel


async def show_supported_payments(ctx, user_id: str):
    messages = await get_channel(ctx, CASH_APPS_CHANNEL).history(limit=1000).flatten()
    image_links = []
    for m in messages:
        if user_id == str(m.author.id):
            for image in m.attachments:
                image_links.append(str(image.url))
    text_to_send = ":moneybag:" + MENTION_STR % user_id + ":moneybag:"
    if len(image_links) == 0:
        text_to_send += '\nDM host for their money apps.'
    header = await ctx.message.channel.send(text_to_send)
    for link in image_links:
        await header.reply(link)


@BOT.command(name=MY_CASH_APPS_COMMAND)
async def cash_apps(ctx: Context):
    if can_host(ctx):
        await show_supported_payments(ctx, str(ctx.author.id))


@BOT.command(name=TOGGLE_AUTO_POST_COMMAND)
async def toggle(ctx: Context):
    if can_host(ctx):
        user_id = str(ctx.author.id)
        if user_id in NO_AUTO_POST_USER_ID:
            NO_AUTO_POST_USER_ID.remove(user_id)
            await ctx.message.reply("Auto post enabled.")
        else:
            NO_AUTO_POST_USER_ID.add(user_id)
            await ctx.message.reply("Auto post disabled.")


@BOT.event
async def on_message(message):
    if POKER_NOW_LINK in str(message.content).lower():
        user_id = str(message.author.id)
        ctx = await BOT.get_context(message)
        if True in (s in str(message.channel).lower() for s in (ACTIVE_GAMES_CHANNEL, 'bot-testing')) \
                and user_id not in NO_AUTO_POST_USER_ID:
            await wl(ctx)
            await cash_apps(ctx)
        elif not can_host(ctx):
            await message.reply(MENTION_STR % user_id + " Bad man, Bad man! you are not authorized to post games here!")
            await message.delete()
    else:
        await BOT.process_commands(message)


async def clear_messages(message, user_id: str):
    if ACTIVE_GAMES_CHANNEL in str(message.channel) or 'bot-testing' in str(message.channel):
        messages = (await message.channel.history(limit=100).flatten())[::-1]
        message_id = []
        for m in messages:
            try:
                if str(m.author.id) in user_id or user_id in str(m.content)\
                        or m.reference.message_id in message_id:
                    message_id.append(m.id)
                    await m.delete()
            except AttributeError:
                continue


@BOT.command(name=CLEAR_COMMAND)
async def clear(ctx: Context, user_id: str = None):
    if user_id is None:
        user_id = str(ctx.message.author.id)
    if can_host(ctx):
        await clear_messages(ctx.message, user_id)


def add_to_interested_players(wl_message, user_id):
    if 'interest' in str(wl_message.content).lower():
        INTERESTED_PLAYERS.add(InterestedPlayer(
            user_id,
            wl_message.channel.id,
            wl_message.id)
        )


async def add_to_wait_list(wl_message, user_id):
    wait_list_str = str(wl_message.content)
    wait_list_str = wait_list_str.replace('\n' + WAIT_LIST_EMPTY_STR, "")
    first_line_end_idx = wait_list_str.find('\n')
    if user_id not in wait_list_str[first_line_end_idx:]:
        start_idx = wait_list_str.find('\n\n')
        wait_list_str = wait_list_str[:start_idx] + '\n' + MENTION_STR % user_id + wait_list_str[start_idx:]
        add_to_interested_players(wl_message, user_id)
        await wl_message.edit(content=wait_list_str)


@BOT.command(name=RANK_REQUEST_COMMAND)
async def rank_request(ctx: Context, role):
    if is_admin(ctx):
        sent = await ctx.channel.send("React with " + RANK_REQUEST_EMOJI + " to be given/removed from " + role + " role")
        await sent.add_reaction(RANK_REQUEST_EMOJI)
        await ctx.message.delete()


async def give_player_rank(member, rank_request_message):
    text = str(rank_request_message.content)
    role_id = int(text[text.find('<@&')+3:text.find('>')])
    role = get(rank_request_message.guild.roles, id=role_id)
    await member.add_roles(role)


@BOT.event
async def on_raw_reaction_add(payload):
    emoji = str(payload.emoji)
    if payload.user_id == BOT.user.id or emoji not in (WAIT_EMOJI, RANK_REQUEST_EMOJI):
        return
    message = await BOT.get_channel(payload.channel_id).fetch_message(payload.message_id)
    if message.author.id == BOT.user.id:
        if emoji == WAIT_EMOJI:
            await add_to_wait_list(message, str(payload.user_id))
        elif emoji == RANK_REQUEST_EMOJI:
            await give_player_rank(payload.member, message)


async def remove_from_interested_players(wl_message, user_id):
    if 'interest' in str(wl_message.content).lower():
        for ip in INTERESTED_PLAYERS:
            if ip.user_id == user_id and ip.wl_message_id == wl_message.id:
                INTERESTED_PLAYERS.remove(ip)
                await wl_message.remove_reaction(WAIT_EMOJI, await BOT.fetch_user(user_id))
                break


async def remove_from_wait_list(wl_message, user_id):
    wait_list_str = str(wl_message.content)
    if user_id in wait_list_str:
        first_line_end_idx = wait_list_str.find('\n')
        wait_list_str = wait_list_str[:first_line_end_idx] + wait_list_str[first_line_end_idx:]\
            .replace('\n' + MENTION_STR % user_id, '')
        is_empty = '<@!' not in wait_list_str[first_line_end_idx:]
        if is_empty:
            wait_list_str = wait_list_str[:first_line_end_idx] + '\n' \
                            + WAIT_LIST_EMPTY_STR + wait_list_str[first_line_end_idx:]
        await wl_message.edit(content=wait_list_str)
        await remove_from_interested_players(wl_message, user_id)


async def remove_player_rank(payload, rank_request_message):
    text = str(rank_request_message.content)
    role_id = int(text[text.find('<@&')+3:text.find('>')])
    guild = await BOT.fetch_guild(payload.guild_id)
    role = get(guild.roles, id=role_id)
    member = await guild.fetch_member(payload.user_id)
    await member.remove_roles(role)


@BOT.event
async def on_raw_reaction_remove(payload):
    emoji = str(payload.emoji)
    if payload.user_id == BOT.user.id or emoji not in (WAIT_EMOJI, RANK_REQUEST_EMOJI):
        return
    message = await BOT.get_channel(payload.channel_id).fetch_message(payload.message_id)
    if message.author.id == BOT.user.id:
        if emoji == WAIT_EMOJI:
            await remove_from_wait_list(message, str(payload.user_id))
        elif emoji == RANK_REQUEST_EMOJI:
            await remove_player_rank(payload, message)


@BOT.command(name=INTEREST_COMMAND)
async def interest(ctx: Context, *args):
    if is_admin(ctx):
        await start_wait_list(
            ctx,
            "**Interest in %s**" % " ".join(args),
            "React with :seat: to be added\n"
            "*Your reaction is removed after one hour*"
        )
        await ctx.message.delete()


BOT.run(TOKEN)
