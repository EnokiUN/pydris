from __future__ import annotations
from aiohttp import ClientSession, ClientWebSocketResponse
from asyncio import sleep, create_task
from json import loads
import typing

from .models import MessagePayload, Message, MessageResponse

REST_URL = "https://eludris.tooty.xyz/"
GATEWAY_URL = "wss://eludris.tooty.xyz/ws/"


class Client:
    """A simple class that handles interfacing with the Eludris API."""
    __slots__ = ("name", "rest_url", "gateway_url", "session", "listeners", "ws")
    def __init__(self, name: str, rest_url: str = REST_URL, gateway_url: str = GATEWAY_URL) -> None:
        self.name = name
        self.rest_url = rest_url
        self.gateway_url = gateway_url

        self.session = ClientSession()
        self.listeners: list[tuple[typing.Callable[[Message], bool], typing.Callable[[Message], typing.Coroutine[typing.Any, typing.Any, typing.Any]]]] = []

        self.ws: ClientWebSocketResponse

    async def handle_heartbeat(self) -> None:
        """A simple function that send's a ping to the Eludris gateway every 20 seconds."""
        while True:
            await self.ws.ping()
            await sleep(20)

    async def start(self) -> None:
        """A function that initialises the handler's connection to the Eludris gateway."""
        self.ws = await self.session.ws_connect(self.gateway_url)
        create_task(self.handle_heartbeat())
        async for payload in self.ws:
            data: MessagePayload = loads(payload.data)
            create_task(self.handle_message(data))

    async def handle_message(self, message: MessagePayload) -> None:
        """A function that handles messages getting received."""
        msg = Message.from_dict(message)
        for pred, listener in self.listeners:
            if pred(msg) is True:
                await listener(msg)

    async def send_message(self, message: Message) -> MessageResponse:
        """A simple function that sends a message object to Eludris."""
        async with self.session.post(self.rest_url, json=message.to_dict()) as response:
            return await response.json()

    async def send(self, content: str) -> MessageResponse:
        """A simple function that sends a message with the bot name and specified content to Eludris."""
        return await self.send_message(Message(self.name, content))

    def listen(self, pred: typing.Callable[[Message], bool]):
        def inner(listener: typing.Callable[[Message], typing.Coroutine[typing.Any, typing.Any, typing.Any]]):
            self.listeners.append((pred, listener))
            return listener
        return inner
