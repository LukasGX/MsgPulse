import asyncio
import json
import os
import re
import aiohttp
from datetime import datetime

from twitchio.ext import commands
from colorama import init, Fore
from dotenv import load_dotenv

init()

load_dotenv()
USER_TOKEN = os.getenv("TWITCH_USER_TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

WORD_COUNTER = {}
BOTS = {}

APP_TOKEN = None

async def get_app_token():
    url = "https://id.twitch.tv/oauth2/token"

    params = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params) as resp:
            data = await resp.json()

    return data["access_token"]

_token_lock = asyncio.Lock()

async def ensure_app_token():
    global APP_TOKEN

    async with _token_lock:
        if APP_TOKEN is None:
            APP_TOKEN = await get_app_token()

    return APP_TOKEN

# word filtering
EMOJI_REGEX = re.compile(r"[\U00010000-\U0010ffff]")

def process_word(word):
    word = word.lower()

    emojis = EMOJI_REGEX.findall(word)
    word = EMOJI_REGEX.sub("", word)

    cleaned = re.sub(r"[^a-z0-9äöüß]", "", word)

    result = []

    if cleaned:
        result.append(cleaned)

    result.extend(emojis)

    return result

class ChatBot(commands.Bot):
    def __init__(self, streamer):
        super().__init__(
            token=USER_TOKEN.replace("oauth:", ""),
            prefix="",
            initial_channels=[streamer]
        )

        self.stream = streamer
        self.clients = set()
        self.most_words = {}
        self.live_since = datetime.now()
    
    def getAllWords(self):
        sorted_words = sorted(
            self.most_words.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_words

    async def event_ready(self):
        print(
            Fore.GREEN +
            f"Bot logged in as {self.nick}" +
            Fore.RESET
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.twitch.tv/helix/users",
                headers={
                    "Client-ID": CLIENT_ID,
                    "Authorization": f"Bearer {APP_TOKEN}"
                },
                params={"login": self.stream}
            ) as resp:
                user_data = await resp.json()

        data = user_data.get("data", [])
        if not data:
            return

        self.broadcaster_id = data[0]["id"]

    async def event_message(self, message):
        if message.echo:
            return

        username = message.author.name
        content = message.content
        timestamp = message.timestamp

        words = re.split(r"\s+", content)

        for word in words:
            processed_words = process_word(word)

            for w in processed_words:
                self.most_words[w] = self.most_words.get(w, 0) + 1

        formatted = (
            f"CHAT_MESSAGE;{timestamp};{username};{content}"
        )

        formatted_count = "WORD_COUNT;" + ";".join(
            f"{key}={value}" for key, value in self.most_words.items()
        )

        msg = {
            "type": "chat_message",
            "timestamp": timestamp.isoformat(),
            "username": username,
            "content": content,
            "word_count": ";".join(f"{key}={value}" for key, value in self.most_words.items())
        }

        print(
            f"{Fore.CYAN}[{timestamp}]"
            f"{Fore.RESET} "
            f"{Fore.YELLOW}{username}"
            f"{Fore.RESET} "
            f"{content}"
        )

        dead_clients = set()

        for client in self.clients:
            try:
                await client.send_text(json.dumps(msg))
            except:
                dead_clients.add(client)

        self.clients -= dead_clients

async def start_bot(streamer: str):
    global APP_TOKEN

    if APP_TOKEN is None:
        APP_TOKEN = await ensure_app_token()

    if streamer in BOTS:
        return BOTS[streamer]

    bot = ChatBot(streamer)
    BOTS[streamer] = bot

    asyncio.create_task(bot.start())

    print(Fore.GREEN + f"Bot for {streamer} started" + Fore.RESET)

    return bot

async def stop_bot(streamer: str):
    bot = BOTS.get(streamer)

    if not bot:
        return

    await bot.close()

    del BOTS[streamer]

    print(Fore.RED + f"Bot for {streamer} stopped" + Fore.RESET)