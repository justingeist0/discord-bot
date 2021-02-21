import discord
import random
import os

token = os.getenv("DISCORD_BOT_TOKEN")

client = discord.Client()

reaction = '💺'
wait_list_instructions = "Click the " + reaction + " reaction to join %s's wait list.\n" \
                       "Click it again to leave the wait list."
reserve_wait_list = "Click the " + reaction + " reaction to join %s's wait list.\n" \
                       "Click it again to leave the wait list."
empty_str = '\n*No wait list yet*'
mention_str = '<@!%s>'
new_line_mention_str = '\n<@!%s>'
active_games = 'active-games'
poker_now_link = 'pokernow.club'

wl_command = '!wl'.lower()
money_command = '!buyin'.lower()
ignore_command = '!botignore'
help_command = '!pighelp'
clear_command = '!clear'
help_message = '**%s**: Create a wait list.' % wl_command + '\n' \
               '**%s**: Fetch your images from venmos-and-cashapps.' % money_command + '\n' \
               '**%s**: Clear all game related messages when your game is finished.' % clear_command


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    if message.author == client.user:
        if str(message.content).find('Click it again to leave the wait list') != -1:
            await message.add_reaction(reaction)
        return
    print(message.content)
    user_id = message.author.id
    if str(message.content).find(ignore_command) != -1:
        return
    elif message.content == 'ping':
        await message.channel.send('Pong ' + ('ping! ' if bool(random.getrandbits(1)) else ' ') + '(' + str(round(client.latency * 100)) + 'ms)')

    elif message.content == 'pong':
        await message.channel.send('Ping' + (' pong!' if bool(random.getrandbits(1)) else ''))

    elif message.content == 'beep':
        await message.channel.send('Boop' + (' beep!' if bool(random.getrandbits(1)) else ''))

    elif message.content == 'boop':
        await message.channel.send('Beep' + (' boop!' if bool(random.getrandbits(1)) else ''))

    elif help_command == str(message.content).lower():
        await message.channel.send(help_message)

    elif clear_command == str(message.content).lower():
        await clear_messages(message)

    elif wl_command == str(message.content).lower():
        await start_wait_list(message, user_id, True)

    elif money_command == str(message.content).lower():
        await show_supported_payments(message, user_id)

    elif active_games in str(message.channel) or 'bot-testing' in str(message.channel):
        if str(message.content).find(poker_now_link) != -1:
            await show_supported_payments(message, user_id)
            await start_wait_list(message, user_id, False)


async def show_supported_payments(message, user_id):
    payment_links = ["Buy in to " + mention_str % user_id + "'s game:\n\n"
                                 "*Only enter the name you're playing with in the message.   \n "
                                 "Do NOT mention anything about poker.*"]
    for channel in message.guild.text_channels:
        if "cashapp-and-venmos" in str(channel):
            messages = await channel.history(limit=500).flatten()
            for m in messages:
                if str(message.author) == str(m.author):
                    for image in m.attachments:
                        payment_links.append(image.url)
            break
    if len(payment_links) == 1:
        payment_links.append('**Nothing found.**')
    for i in payment_links:
        await message.channel.send(i)


async def start_wait_list(message, name_id, is_reserve_wait_list):
    message_to_send = "**Wait List:**" \
                      "%s\n\n" % empty_str + (reserve_wait_list % (mention_str % name_id) if is_reserve_wait_list \
                        else wait_list_instructions % (mention_str % name_id))
    await message.channel.send(message_to_send)


async def clear_messages(message):
    if active_games in str(message.channel) or 'bot-testing' in str(message.channel):
        messages = await message.channel.history(limit=100).flatten()
        user = message.author
        delete_next_if_bot = False
        reversed_messages = []
        for m in messages:
            reversed_messages.insert(0, m)
        for m in reversed_messages:
            if str(user) == str(m.author):
                await m.delete()
                delete_next_if_bot = True
            elif m.author == client.user and delete_next_if_bot:
                await m.delete()
            else:
                delete_next_if_bot = False


@client.event
async def on_raw_reaction_add(payload):
    if payload.user_id == client.user.id or str(payload.emoji) != reaction:
        return
    print('Added reaction' + str(payload))
    message = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
    await add_to_wait_list(message, new_line_mention_str % payload.user_id)


async def add_to_wait_list(message, mention_user):
    if message.author == client.user and str(message.content).find("Wait List:") != -1:
        wait_list_str = str(message.content)
        wait_list_str = wait_list_str.replace(empty_str, "")
        start_idx = wait_list_str.find('\n\n')
        if wait_list_str.find(mention_user) != -1:
            return
        wait_list_str = wait_list_str[0:start_idx] + mention_user + wait_list_str[start_idx:]
        await message.edit(content=wait_list_str)


@client.event
async def on_raw_reaction_remove(payload):
    if str(payload.emoji) == reaction:
        print('Removed reaction' + str(payload))
        message = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if message.author == client.user:
            wait_list_str = str(message.content)
            mention_user = new_line_mention_str % payload.user_id
            if wait_list_str.find(mention_user) == -1:
                return
            wait_list_str = wait_list_str.replace(mention_user, '')
            name_idx = wait_list_str.find('<@!')
            if 'join' in wait_list_str[name_idx-10:name_idx]:
                start_idx = wait_list_str.find('\n\n')
                wait_list_str = wait_list_str[0:start_idx] + empty_str + wait_list_str[start_idx:]
            await message.edit(content=wait_list_str)


client.run(token)
