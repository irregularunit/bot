from __future__ import annotations

import math
from io import BytesIO
from typing import TYPE_CHECKING, Any, Optional

import discord
from discord.ext import commands
from discord.ui import View
from PIL import Image

from models import EmbedBuilder
from utils import BaseExtension, MemberConverter

if TYPE_CHECKING:
    from bot import Bot
    from utils import Context

__all__: tuple[str, ...] = ("DiscordUserHistory",)


class AvatarHistoryView(View):
    def __init__(self, ctx: Context, *, member: Optional[discord.Member] = None, timeout: Optional[float] = 60.0) -> None:
        super().__init__(timeout=timeout)
        self.ctx: Context = ctx
        self.bot: Bot = ctx.bot

        self.member: Optional[discord.Member] = member
        self.message: Optional[discord.Message] = None

        self.cached_avatars: list[str] = []

    def disable_view(self) -> None:
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                # This check is purly done for type checking purposes
                # and is not needed for the code to work.
                item.disabled = True

    async def on_timeout(self) -> None:
        self.disable_view()
        if self.message is not None:
            await self.message.edit(view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.ctx.author.id:
            return True

        await interaction.response.send_message("You cannot use this, sorry. :(", ephemeral=True)
        return False

    async def fetch_avatar_history_items(self) -> list[str]:
        query = "SELECT item_value FROM item_history WHERE uid = $1 AND item_type = $2"
        res = await self.bot.pool.fetch(query, self.member.id if self.member else self.ctx.author.id, "avatar")
        ret = [row["item_value"] for row in res]

        self.cached_avatars = ret
        return ret

    async def start(self) -> None:
        await self.fetch_avatar_history_items()

        self.add_item(PreviousAvatarButton(label="<", style=discord.ButtonStyle.secondary))
        self.add_item(NextAvatarButton(label=">", style=discord.ButtonStyle.secondary))
        self.add_item(CollageAvatarButton(label="Collage", style=discord.ButtonStyle.primary))

        embed = EmbedBuilder.factory(self.ctx)
        embed.set_footer(text=f"Avatar 1 of {len(self.cached_avatars)}")

        if len(self.cached_avatars) == 0:
            embed.description = "No avatar history found."
            embed.set_image(url=self.member.display_avatar.url if self.member else self.ctx.author.display_avatar.url)
            self.disable_view()
        else:
            embed.description = "Click the buttons to navigate through the avatar history."
            embed.set_image(url=self.cached_avatars[0])

        self.message = await self.ctx.send(embed=embed, view=self)


class PreviousAvatarButton(discord.ui.Button["AvatarHistoryView"]):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.disabled = False

    async def callback(self, interaction: discord.Interaction) -> None:
        if TYPE_CHECKING:
            assert self.view is not None

        view: AvatarHistoryView = self.view
        previous_or_last = view.cached_avatars[-1]
        current_index = view.cached_avatars.index(previous_or_last)

        embed = EmbedBuilder.factory(view.ctx)
        embed.set_image(url=previous_or_last)
        embed.set_footer(text=f"Avatar {current_index + 1} of {len(view.cached_avatars)}")

        self.view.message = await interaction.response.edit_message(embed=embed, view=view)


class NextAvatarButton(discord.ui.Button["AvatarHistoryView"]):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.disabled = False

    async def callback(self, interaction: discord.Interaction) -> None:
        if TYPE_CHECKING:
            assert self.view is not None

        view: AvatarHistoryView = self.view
        next_or_first = view.cached_avatars[0]
        current_index = view.cached_avatars.index(next_or_first)

        embed = EmbedBuilder.factory(view.ctx)
        embed.set_image(url=next_or_first)
        embed.set_footer(text=f"Avatar {current_index + 1} of {len(view.cached_avatars)}")

        self.view.message = await interaction.response.edit_message(embed=embed, view=view)


class CollageAvatarButton(discord.ui.Button["AvatarHistoryView"]):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.disabled = False

    def compute_grid_size(self, amount: int) -> int:
        return int(amount**0.5) + 1 if amount**0.5 % 1 else int(amount**0.5)

    def create_collage(self, images: list[Image.Image]) -> BytesIO:
        grid_size = self.compute_grid_size(len(images))
        rows: int = math.ceil(math.sqrt(len(images)))

        # Read the following code on your own risk.
        # I forgot why I did it this way. And I don't want to know.
        # Feel free to rewrite it if you want.
        w = h = 256 * rows
        with Image.new("RGBA", (w, h), (0, 0, 0, 0)) as collage:
            times_x = times_y = final_x = final_y = 0
            for avatar in images:
                if times_x == grid_size:
                    times_y += 1
                    times_x = 0

                x, y = times_x * 256, times_y * 256
                collage.paste(avatar, (x, y))

                final_x, final_y = max(x, final_x), max(y, final_y)
                times_x += 1

            collage: Image.Image = collage.crop((0, 0, final_x + 256, final_y + 256))

            buffer: BytesIO = BytesIO()
            collage.save(buffer, format="webp")
            buffer.seek(0)
            return buffer

    async def get_member_collage(self, member: discord.Member) -> Optional[discord.File]:
        if TYPE_CHECKING:
            assert self.view is not None

        results = await self.view.bot.pool.fetch(
            "SELECT * FROM avatar_history WHERE uid = $1 ORDER BY changed_at DESC", member.id
        )
        if not results:
            return None

        images: list[Image.Image] = []
        for result in results:
            with Image.open(BytesIO(result["avatar"])) as avatar:
                images.append(avatar.resize((256, 256)).convert("RGBA"))

        buffer: BytesIO = await self.view.bot.to_thread(self.create_collage, images)
        return discord.File(buffer, filename="collage.webp")

    async def callback(self, interaction: discord.Interaction) -> None:
        if TYPE_CHECKING:
            assert self.view is not None

        view: AvatarHistoryView = self.view
        embed = EmbedBuilder.factory(view.ctx)
        embed.set_image(url="attachment://collage.webp")
        embed.set_footer(text=f"Avatar collage of {view.member or view.ctx.author}")

        # ctx.author is typed as User | Member, hence the ignore.
        # Since our commands are guild only, we can safely assume that ctx.author is a Member.
        file: discord.File | None = await self.get_member_collage(view.member or view.ctx.author)  # type: ignore

        if not file:
            embed.description = "No avatar history found."
            embed.set_image(url=view.member.display_avatar.url if view.member else view.ctx.author.display_avatar.url)
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            embed.description = "Avatar collage of the user."
            self.view.disable_view()
            self.view.message = await interaction.response.edit_message(embed=embed, attachments=[file], view=view)


class DiscordUserHistory(BaseExtension):
    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)
        self.bot: Bot = bot

    @commands.command(name="avatar", aliases=("av",))
    async def avatar_command(
        self,
        ctx: Context,
        *,
        member: discord.Member = commands.param(default=None, converter=MemberConverter(), displayed_default="You"),
    ) -> None:
        await AvatarHistoryView(ctx, member=member).start()
