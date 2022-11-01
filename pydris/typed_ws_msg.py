# pyright: strict
# Taken from https://github.com/discatpy-dev/core/blob/main/discatcore/gateway/types.py, thanks emre <3
from aiohttp import WSMessage, WSMsgType
import typing
import builtins
from typing_extensions import Self, TypeGuard
from dataclasses import dataclass

DT = typing.TypeVar("DT")

@dataclass
class BaseTypedWSMessage(typing.Generic[DT]):
    type: WSMsgType
    data: DT
    extra: str

    @classmethod
    def convert_from_untyped(cls: builtins.type[Self], msg: WSMessage) -> Self:
        return cls(
            typing.cast(WSMsgType, msg[0]),
            typing.cast(DT, msg[1]),
            typing.cast(str, msg[2]),
        )


TextTypedWSMessage = BaseTypedWSMessage[str]
BinaryTypedWSMessage = BaseTypedWSMessage[bytes]


def is_text(base: BaseTypedWSMessage[typing.Any]) -> TypeGuard[TextTypedWSMessage]:
    return base.type is WSMsgType.TEXT


def is_binary(base: BaseTypedWSMessage[typing.Any]) -> TypeGuard[BinaryTypedWSMessage]:
    return base.type is WSMsgType.BINARY


def convert_from_untyped(msg: WSMessage) -> BaseTypedWSMessage[typing.Any]:
    base: BaseTypedWSMessage[typing.Any] = BaseTypedWSMessage.convert_from_untyped(msg)

    if base.type == WSMsgType.TEXT:
        return typing.cast(TextTypedWSMessage, base)
    elif base.type == WSMsgType.BINARY:
        return typing.cast(BinaryTypedWSMessage, base)
    return base

