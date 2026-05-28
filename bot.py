import asyncio
import os

from twitchio.ext import commands
from colorama import init, Fore
from dotenv import load_dotenv

init()

load_dotenv()
TOKEN = os.getenv["TOKEN"]

WORD_COUNTER = {}
BOTS = {}

class ChatBot(commands.Bot):
    def __init__(self, streamer):
        super().__init__(
            token="oauth:" + TOKEN,
            prefix="",
            initial_channels=[streamer]
        )

        self.stream = streamer

        # aktive websocket clients
        self.clients = set()

    async def event_ready(self):
        print(
            Fore.GREEN +
            f"Bot logged in as {self.nick}" +
            Fore.RESET
        )

    async def event_message(self, message):
        if message.echo:
            return

        username = message.author.name
        content = message.content
        timestamp = message.timestamp

        formatted = (
            f"CHAT_MESSAGE;{timestamp};{username};{content}"
        )

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
                await client.send_text(formatted)
            except:
                dead_clients.add(client)

        self.clients -= dead_clients


async def start_bot(streamer: str):
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