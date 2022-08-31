# Pydris

A simple asychronous wrapper for the Eludris API.

## Example

```py
from asyncio import get_event_loop
from pydris import Client, Message

client = Client("Thang")

@client.listen(lambda m: m.content.startswith("!ping")) # Accepts an optional predicate
async def ping_cmd(_: Message):
    await client.send("Pong!")

# You can have multiple listeners

@client.listen(lambda m: "hi" in m.content)
async def hi(message: Message):
    await client.send("Hey there!")

get_event_loop().run_until_complete(client.start())
```
