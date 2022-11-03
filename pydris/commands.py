# pyright: strict
from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    from .models import Message

PT = typing.TypeVar("PT")

class Param(typing.Generic[PT]):
    """A simple class which represents a parameter."""
    __slots__ = ("name", "parser", "default", "required", "multiple", "short", "flag")
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

    async def parse(self, args: list[str]) -> PT | list[PT]:
        parsed: list[list[PT]] = []
        for i in args:
            parsed.append(await self.parser.parse(i))
        matches = [i for j in parsed for i in j]
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
    async def parse(self, arg: str) -> list[PT]: ...

class StringParser:
    """A string parser, just passes forward anything it gets."""
    async def parse(self, arg: str) -> list[str]:
        return [arg]

class NumberParser:
    """A number parser, adds the options to validate if a number is a decimal or is signed"""
    __slots__ = ("decimal", "signed")
    def __init__(self, decimal: bool = True, signed: bool = True):
        self.decimal = decimal
        self.signed = signed

    async def parse(self, arg: str) -> list[float | int]:
        if self.decimal:
            found = float(arg)
        else:
            found = int(arg)
        if not self.signed and found < 0:
            raise ValueError("This number can't be negative")
        return [found]

class BoolParser:
    async def parse(self, arg: str) -> list[bool]:
        if arg.lower() in ["yes", "y", "true", "t", "1", ""]:
            found = True
        elif arg.lower() in ["no", "n", "false", "f", "0"]:
            found = False
        else:
            raise ValueError("Value cannot be interpreted as a boolean")
        return [found]

class Command:
    """A simple class which represents a command."""
    __slots__ = ("prefix", "name", "description", "aliases", "names", "func", "args", "handler")
    def __init__(self, func: typing.Callable[..., typing.Coroutine[typing.Any, typing.Any, typing.Any]], name: typing.Optional[str] = None, aliases: typing.Optional[list[str]] = None, description: typing.Optional[str] = None):
        self.name = name or func.__name__
        self.description = description or func.__doc__
        self.aliases = aliases if aliases is not None else []
        self.names = [self.name] + self.aliases
        self.func = func
        self.args: list[Param[typing.Any]] = []
        self.handler: typing.Optional[typing.Callable[[Message, Exception], typing.Coroutine[typing.Any, typing.Any, typing.Any]]] = None

    @classmethod
    def command(cls, name: typing.Optional[str] = None, aliases: typing.Optional[list[str]] = None, description: typing.Optional[str] = None):
        def inner(func: typing.Callable[[Message, Exception], typing.Coroutine[typing.Any, typing.Any, typing.Any]]):
            return cls(func, name, aliases, description)
        return inner

    def error(self, func: typing.Callable[..., typing.Coroutine[typing.Any, typing.Any, typing.Any]]):
        """Registers an error handle for this comman.d"""
        self.handler = func
        return func

    async def invoke(self, msg: Message, prefix: str):
        try:
            invocation = prefix + msg.content[len(prefix):].split(" ", 1)[0]
            args, kwargs = parse_content(msg.content[len(invocation):])
            params: list[Param[typing.Any]] = []
            kwparams: dict[str, Param[typing.Any]] = {}
            for arg in self.args:
                if arg.flag:
                    kwparams[arg.name] = arg
                else:
                    params.append(arg)
            passed_args: dict[str, typing.Any] = {}
            for (arg, param) in zip(args, params):
                passed_args[param.name] = await param.parse([arg])
            for param in params:
                if passed_args.get(param.name) is None:
                    if not param.required:
                        passed_args[param.name] = param.default
                    else:
                        # raise ValueError("Not good enough")
                        raise ValueError("Not enough args")
            for v in kwparams.values():
                skwarg = None
                if (kwarg := kwargs.get(v.name)) is not None or (v.short is not None and (skwarg := kwargs.get(v.short)) is not None):
                    parsed: list[str] = []
                    if kwarg:
                        parsed.extend(kwarg)
                    if skwarg:
                        parsed.extend(skwarg)
                    passed_args[v.name] = await v.parse(parsed)
                else:
                    # raise ValueError("Not good enough")
                    raise ValueError("Not enough args")
            await self.func(msg, **passed_args)
        except Exception as e:
            if self.handler is not None:
                await self.handler(msg, e)
            else:
                raise

def param(name: str, parser: Parser[typing.Any], required: typing.Optional[bool] = None, default: typing.Optional[typing.Any] = None, multiple: bool = False, short: typing.Optional[str] = None, flag: typing.Optional[bool] = None):
    def inner(cmd: Command):
        cmd.args.append(Param(name, parser, required, default, multiple, short, flag))
        return cmd
    return inner

def parse_content(content: str) -> tuple[list[str], dict[str, list[str]]]:
    args: list[str] = []
    kwargs: dict[str, list[str]] = {}
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
                kwargs.setdefault(name, []).append(value)
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
            if double_dash and name == "":
                args.append("--")
            elif dash and name == "":
                args.append("-")
            if double_dash:
                double_dash = False
                dash = False
            elif name and value == "":
                continue
            elif quoted:
                value += c
            else:
                if name:
                    kwargs.setdefault(name, []).append(value)
                elif value:
                    args.append(value)
                name = ""
                value = ""
        else:
            value += c

    if name:
        kwargs.setdefault(name, []).append(value)
    elif value:
        args.append(value)

    return (args, kwargs)

