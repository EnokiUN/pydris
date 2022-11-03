# pyright: strict
from __future__ import annotations
import typing

from .models import Message
from .commands import Command

if typing.TYPE_CHECKING:
    from .client import Client


class Extension:
    """A simple abstraction of a list of commands to help split up your
    bot's codebase into different files.

    Example
    -------

    .. code-block:: python3

        # ext.py
        ext = Extension("name", "optional description") # this variable must be called ext

        @ext.command() # You can add params like normal
        async def foo(client: Client, msg: Message): ...

        # main.py
        client.load("ext") # a python dotpath

    """
    def __init__(self, name: str, description: typing.Optional[str] = None):
        self.name = name
        self.description = description
        self.commands: dict[str, Command] = {}

    def command(self, name: typing.Optional[str] = None, aliases: typing.Optional[list[str]] = None, description: typing.Optional[str] = None):
        """A simple decorator that adds a command to the extension."""
        def inner(func: typing.Callable[..., typing.Coroutine[typing.Any, typing.Any, typing.Any]]):
            command = Command(func, name, aliases, description)
            for i in command.names:
                if i in self.commands:
                    raise ValueError("A command with this name already exists")
                self.commands[i] = command
            return command
        return inner

    async def invoke(self, client: Client, msg: Message, prefix: str):
        cmd = msg.content[len(prefix):].split(" ", 1)[0]
        if (command := self.commands.get(cmd)) is not None:
            return await command.invoke_with_client(client, msg, prefix)

