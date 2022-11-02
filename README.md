# Pydris

A simple asychronous wrapper for the Eludris API.

## Example

```py
from asyncio import get_event_loop
from pydris import Client, Message

client = Client("Thang", "!")

@client.listen(lambda m: m.content.startswith("!ping")) # Accepts an optional predicate
async def ping_cmd(_: Message):
    await client.send("Pong!")

# You can have multiple listeners

@client.listen(lambda m: "hi" in m.content)
async def hi(msg: Message):
    await client.send("Hey there!")

# You can also have commands
@client.command("hello", aliases=["hi", "howdy"], description="says hi back")
async def hello(_: Message):
    # Docstring is automatically set as the description if one isn't passed
    await client.send("hi")

# There's also a fairly powerful decorator centric argument parser
@param("c", BoolParser(), required=False)
@param("b", NumberParser(signed=False), short="b") # this is a flag
@param("a", StringParser())
@client.command("foo")
async def foo(_: Message, a: str, b: int, c: Optional[bool]):
    # invoked with something like `!foo "hello world" y -b 9` or `!foo h -b0`
    await client.send(f"{a} {b} {c}")

# You can also set error handlers
@hello.error
@sus.error
async def handle_errors(_: Message, err: Exception):
    await client.send(f"{err}")

client.run()
```
