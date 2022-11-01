# pyright: strict
from __future__ import annotations
import typing
import re

if typing.TYPE_CHECKING:
    from .models import Message

PT = typing.TypeVar("PT")

class Param(typing.Generic[PT]):
    def __init__(self, name: str, parser: Parser[PT], required: typing.Optional[bool] = None, default: typing.Optional[typing.Any] = None, multiple: bool = False, short: typing.Optional[str] = None, flag: typing.Optional[bool] = None):
        self.name = name
        self.parser = parser
        self.default = default
        self.required = required if required is not None else (default is None)
        self.multiple = multiple
        self.short = short
        self.flag = flag if flag is not None else (short is not None)

        if required is True and default is not None:
            raise ValueError(
                "Parameter cannot be required and have a default value")

        if flag is False and short is not None:
            raise ValueError("Parameters with short names must be glags")

    async def parse(self, arg: str) -> PT | list[PT]:
        matches = await self.parser.parse(arg, self)
        if len(matches) == 0:
            if self.required:
                raise ValueError(f"Parameter {self.name} is required")
            elif self.default is None:
                raise ValueError(
                "Parameter cannot be required and have a default value")
            else:
                return self.default
        if self.multiple:
            return matches
        else:
            return matches[-1]

class Parser(typing.Protocol[PT]):
    async def parse(self, arg: str, param: Param[PT]) -> list[PT]: ...

class StringParser:
    async def parse(self, arg: str, param: Param[str]) -> list[str]:
        pattern = r"[a-zA-Z0-9]"
        found = re.findall(f"--{param.name} ?({pattern})", arg)
        if param.short:
            found += re.findall(f"-{param.short} ?({pattern})", arg)
        return found

class NumberParser:
    def __init__(self, decimal: bool = False, signed: bool = True):
        self.decimal = decimal
        self.signed = signed

    async def parse(self, arg: str, param: Param[int]) -> list[float | int]:
        pattern = r"-?\d+"
        if self.decimal:
            pattern = r"-?\d+.?\d*"
        if not self.signed:
            pattern = pattern[2:]
        found = re.findall(f"--{param.name} ?({pattern})", arg)
        if param.short:
            found += re.findall(f"-{param.short} ?({pattern})", arg)
        return [float(i) for i in found]

class BoolParser:
    async def parse(self, arg: str, param: Param[bool]) -> list[bool]:
        pattern = r"yes|no|y|n|true|false|t|f|1|0"
        found = re.findall(f"--{param.name} ?({pattern})",
                           arg, re.IGNORECASE)
        if param.short:
            found += re.findall(f"-{param.short} ?({pattern})",
                                arg, re.IGNORECASE)
        found = [True if i in ["yes", "y", "true", "t", "1"] else False for i in found]
        if not param.multiple:
            found = [f"--{param.name}" in arg or  f"-{param.short}" in arg] + found
        return found

class Command:
    def __init__(self, func: typing.Callable[..., typing.Coroutine[typing.Any, typing.Any, typing.Any]], name: typing.Optional[str] = None, aliases: typing.Optional[list[str]] = None, description: typing.Optional[str] = None):
        self.name = name or func.__name__
        self.description = description or func.__doc__
        self.aliases = aliases if aliases is not None else []
        self.names = [self.name] + self.aliases
        self.func = func
        self.args: list[Param[typing.Any]] = []

    @classmethod
    def command(cls, name: typing.Optional[str] = None, aliases: typing.Optional[list[str]] = None, description: typing.Optional[str] = None):
        def inner(func: typing.Callable[..., typing.Coroutine[typing.Any, typing.Any, typing.Any]]):
            return cls(func, name, aliases, description)
        return inner

    async def invoke(self, msg: Message):
        args, kwargs = parse_content(msg.content)
        params: list[Param[typing.Any]] = []
        kwparams: dict[str, Param[typing.Any]] = {}
        for arg in self.args:
            if arg.flag:
                kwparams[arg.name] = arg
            else:
                params.append(arg)
        passed_args: dict[str, typing.Any] = {}
        if len(args) < len(params):
            # raise ValueError("Not good enough")
            raise ValueError("Not enough args")
        for (arg, param) in zip(args, params):
            passed_args[param.name] = param.parse(arg)
        passed_kwargs: dict[str, typing.Any] = {}
        for (k, v) in kwparams.items():
            if (kwarg := kwargs.get("k")) is not None:
                passed_kwargs[k] = v.parse(kwarg)
            else:
                # raise ValueError("Not good enough")
                raise ValueError("Not enough args")
        await self.func(msg, *passed_args, **passed_kwargs)

def parse_content(content: str) -> tuple[list[str], dict[str, str]]:
    args: list[str] = []
    kwargs: dict[str, str] = {}
    quoted = False
    escaped = False
    dash = False
    double_dash = False

    value = ""
    name = ""

    for c in content:
        if c == "\\" and not escaped:
            escaped = True
        elif escaped:
            value += c
            escaped = False
        elif c == "\"" and not quoted:
            quoted = True
        elif c == "\"":
            quoted = False
            if name:
                kwargs[name] = value
            elif value:
                args.append(value)
            name = ""
            value = ""
        elif c == "-" and not dash and value == "" and not quoted:
            dash = True
        elif c == "-" and not double_dash and value == "" and not quoted:
            double_dash = True
        elif double_dash and c != " ":
            name += c
        elif dash and c != " ":
            name = c
            dash = False
        elif c == " ":
            if double_dash:
                double_dash = False
                dash = False
            elif quoted:
                value += c
            else:
                if name:
                    kwargs[name] = value
                elif value:
                    args.append(value)
                name = ""
                value = ""
        else:
            value += c

    if name:
        kwargs[name] = value
    elif value:
        args.append(value)

    return (args, kwargs)
