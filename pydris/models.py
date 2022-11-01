# pyright: strict
from __future__ import annotations
import typing

class MessagePayload(typing.TypedDict):
    author: str
    content: str

class MessageResponse(typing.TypedDict):
    author: str
    content: str

class Message:
    """A class which represents an Eludris Message

    Attributes
    ----------
    author: :cls:`str`
        The name of the person who sent the message.
    content: :cls:`str`
        The content of the message.
    """
    __slots__ = ("author", "content")
    def __init__(self, author: str, content: str) -> None:
        self.author = author
        self.content = content

    def __repr__(self) -> str:
        return f"<Message author={self.author}>"

    def __str__(self) -> str:
        return f"[{self.author}]: {self.content}"

    def to_dict(self) -> MessagePayload:
        return {"author": self.author, "content": self.content}

    @classmethod
    def from_dict(cls, data: MessagePayload) -> Message:
        return cls(data["author"], data["content"])
