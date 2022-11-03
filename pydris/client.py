# pyright: strict
from __future__ import annotations
from aiohttp import ClientSession, ClientWebSocketResponse
from asyncio import sleep, create_task, get_event_loop_policy
from json import loads
import typing

from .models import MessagePayload, Message, MessageResponse
from .typed_ws_msg import BaseTypedWSMessage
from .commands import Command

REST_URL = "https://eludris.tooty.xyz/"
GATEWAY_URL = "wss://eludris.tooty.xyz/ws/"


class Client:
    """A simple class that handles interfacing with the Eludris API."""
    __slots__ = ("name", "rest_url", "gateway_url", "session", "listeners", "ws", "prefix", "commands")
    def __init__(self, name: str, rest_url: str = REST_URL, gateway_url: str = GATEWAY_URL, prefix: typing.Optional[str] = None) -> None:
        self.name = name
        self.rest_url = rest_url
        self.gateway_url = gateway_url
        self.prefix = prefix
        self.commands: dict[str, Command] = {}

        self.session = ClientSession()
        self.listeners: list[tuple[typing.Callable[[Message], bool], typing.Callable[[Message], typing.Coroutine[typing.Any, typing.Any, typing.Any]]]] = []

        self.ws: ClientWebSocketResponse

    async def handle_heartbeat(self):
        """A simple function that send's a ping to the Eludris gateway every 20 seconds."""
        while True:
            await self.ws.ping()
            await sleep(20)

    async def start(self):
        """A function that initialises the handler's connection to the Eludris gateway."""
        # Here we face the minor issue of aiohttp websockets being not fully typed :/
        self.ws = await self.session.ws_connect(self.gateway_url) # type: ignore
        create_task(self.handle_heartbeat())
        async for payload in self.ws:
            wsmsg: BaseTypedWSMessage[typing.Any] = BaseTypedWSMessage.convert_from_untyped(payload)
            data = typing.cast(str, wsmsg.data)
            msg: MessagePayload = loads(data)
            create_task(self.handle_message(msg))

    def run(self):
        try:
            get_event_loop_policy().get_event_loop().run_until_complete(self.start())
        except KeyboardInterrupt:
            return

    async def handle_message(self, message: MessagePayload):
        """A function that handles messages getting received."""
        msg = Message.from_dict(message)
        for pred, listener in self.listeners:
            if pred(msg):
                await listener(msg)

    async def send_message(self, message: Message) -> MessageResponse:
        """A simple function that sends a message object to Eludris."""
        async with self.session.post(self.rest_url+"messages/", json=message.to_dict()) as response:
            return await response.json()

    async def send(self, content: str) -> MessageResponse:
        """A simple function that sends a message with the bot name and specified content to Eludris."""
        return await self.send_message(Message(self.name, content))

    def listen(self, pred: typing.Callable[[Message], bool]):
        """A simple decorator to register a listener for a message."""
        def inner(listener: typing.Callable[[Message], typing.Coroutine[typing.Any, typing.Any, typing.Any]]):
            self.listeners.append((pred, listener))
            return listener
        return inner

    def command(self, name: typing.Optional[str] = None, aliases: typing.Optional[list[str]] = None, description: typing.Optional[str] = None):
        """A simple decorator that adds a command to the bot."""
        def inner(func: typing.Callable[..., typing.Coroutine[typing.Any, typing.Any, typing.Any]]):
            prefix: str
            if self.prefix is None:
                raise ValueError("Prefix can't be None")
            else:
                prefix = self.prefix
            cmd = Command(func, name, aliases, description)
            for i in cmd.names:
                if i in self.commands:
                    raise ValueError("A command with this name already exists")
                self.commands[i] = cmd
            self.listeners.append((lambda m: m.content.startswith(prefix) and m.content[len(prefix):].split()[0] in cmd.names, lambda m: cmd.invoke(m, prefix)))
            return cmd
        return inner
