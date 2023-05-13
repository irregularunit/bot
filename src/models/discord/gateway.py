# -*- coding: utf-8 -*-

"""
Serenity License (Attribution-NonCommercial-ShareAlike 4.0 International)

You are free to:

  - Share: copy and redistribute the material in any medium or format.
  - Adapt: remix, transform, and build upon the material.

The licensor cannot revoke these freedoms as long as you follow the license
terms.

Under the following terms:

  - Attribution: You must give appropriate credit, provide a link to the
    license, and indicate if changes were made. You may do so in any reasonable
    manner, but not in any way that suggests the licensor endorses you or your
    use.
  
  - Non-Commercial: You may not use the material for commercial purposes.
  
  - Share Alike: If you remix, transform, or build upon the material, you must
    distribute your contributions under the same license as the original.
  
  - No Additional Restrictions: You may not apply legal terms or technological
    measures that legally restrict others from doing anything the license
    permits.

This is a human-readable summary of the Legal Code. The full license is available
at https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode
"""

# pyright: reportUnknownMemberType=false, reportGeneralTypeIssues=false
# pyright: reportUntypedBaseClass=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportPrivateUsage=false
# Monkey patched MobileGateway class to allow for mobile connections.
from __future__ import annotations

from sys import platform
from typing import Any, NotRequired, Optional, Self, TypedDict

import discord
import yarl
from discord.http import INTERNAL_API_VERSION

__all__: tuple[str, ...] = ("MobileGateway",)


class IdentifyPayload(TypedDict):
    op: int
    d: MobilePayload


class MobilePayload(TypedDict):
    token: str
    properties: MobileProperties
    compress: bool
    large_threshold: int
    v: int
    intents: NotRequired[int]
    presence: NotRequired[PresencePayload]


class MobileProperties(TypedDict):
    os: str
    browser: str
    device: str
    referrer: str
    referring_domain: str


class PresencePayload(TypedDict):
    status: str
    game: NotRequired[Any]
    since: int
    afk: bool


class MobileGateway(discord.gateway.DiscordWebSocket):
    async def identify(self) -> None:
        payload = IdentifyPayload(
            op=2,
            d=MobilePayload(
                token=self.token,
                properties=MobileProperties(
                    os=platform,
                    browser="Discord iOS",
                    device="Discord iOS",
                    referrer="",
                    referring_domain="",
                ),
                compress=True,
                large_threshold=250,
                v=10,
            ),
        )

        if self.shard_id is not None and self.shard_count is not None:
            payload["d"]["shard"] = [self.shard_id, self.shard_count]

        state: Any = self._connection

        if state._activity is not None or state._status is not None:
            payload["d"]["presence"] = {
                "status": state._status,
                "game": state._activity,
                "since": 0,
                "afk": False,
            }

        if state._intents is not None:
            payload["d"]["intents"] = state._intents.value

        await self.call_hooks("before_identify", self.shard_id, initial=self._initial_identify)
        await self.send_as_json(payload)

    @classmethod
    async def from_client(
        cls,
        client: discord.Client,
        *,
        initial: bool = False,
        gateway: Optional[yarl.URL] = None,
        shard_id: Optional[int] = None,
        session: Optional[str] = None,
        sequence: Optional[int] = None,
        resume: bool = False,
        encoding: str = 'json',
        zlib: bool = True,
    ) -> Self:
        """Creates a main websocket for Discord from a :class:`Client`.

        This is for internal use only. (OR IS IT?)
        """

        gateway = gateway or cls.DEFAULT_GATEWAY

        if zlib:
            url = gateway.with_query(v=INTERNAL_API_VERSION, encoding=encoding, compress='zlib-stream')
        else:
            url = gateway.with_query(v=INTERNAL_API_VERSION, encoding=encoding)

        socket = await client.http.ws_connect(str(url))
        ws = cls(socket, loop=client.loop)

        # Dynamically add attributes
        ws.token = client.http.token
        ws._connection = client._connection
        ws._discord_parsers = client._connection.parsers
        ws._dispatch = client.dispatch
        ws.gateway = gateway
        ws.call_hooks = client._connection.call_hooks
        ws._initial_identify = initial
        ws.shard_id = shard_id
        ws._rate_limiter.shard_id = shard_id
        ws.shard_count = client._connection.shard_count
        ws.session_id = session
        ws.sequence = sequence
        ws._max_heartbeat_timeout = client._connection.heartbeat_timeout

        if client._enable_debug_events:
            ws.send = ws.debug_send
            ws.log_receive = ws.debug_log_receive

        client._connection._update_references(ws)

        # Poll event for OP Hello
        await ws.poll_event()

        if not resume:
            await ws.identify()
            return ws

        await ws.resume()
        return ws
