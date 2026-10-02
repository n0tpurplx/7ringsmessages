import os

import discord
from discord import app_commands
from discord.ext import commands


TOKEN = os.getenv("DISCORD_TOKEN")

APPLICATION_CHANNEL_ID = 1555692882428428400
APPLICATION_REVIEW_ROLE_ID = 1554994288558080041
STAFF_ROLE_ID = 1554970909201268836

EMBED_IMAGE = (
    "https://cdn.discordapp.com/attachments/"
    "1553869080815996989/1554997540993114202/IMG_5801.jpg"
    "?backend=b2&ex=6ac0e610&is=6abf9490"
    "&hm=836a742636fbc082f93db193de7a29368aed7a3567441d890c499f8c41fd66&"
)


intents = discord.Intents.default()
intents.members = True


class Bot(commands.Bot):
    async def setup_hook(self):
        self.add_view(StaffApplicationView())
        self.add_view(RulesView())

        synced = await self.tree.sync()
        print(f"Synced {len(synced)} slash commands.")


bot = Bot(
    command_prefix="!",
    intents=intents,
)


def make_embed(title: str, description: str = "") -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
    )
    embed.set_image(url=EMBED_IMAGE)
    return embed


# =========================================================
# STAFF APPLICATION
# =========================================================

class StaffApplicationModal(discord.ui.Modal, title="Staff Application"):

    age = discord.ui.TextInput(
        label="Age",
        placeholder="How old are you?",
        required=True,
        max_length=3,
    )

    roblox_username = discord.ui.TextInput(
        label="Roblox Username",
        placeholder="What is your Roblox username?",
        required=True,
        max_length=50,
    )

    experience = discord.ui.TextInput(
        label="Previous Experience",
        placeholder="Tell us about any previous staff experience.",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000,
    )

    why_staff = discord.ui.TextInput(
        label="Why should we choose you?",
        placeholder="Why would you be a good staff member?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1500,
    )

    availability = discord.ui.TextInput(
        label="Availability",
        placeholder="How active can you be?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000,
    )

    async def on_submit(self, interaction: discord.Interaction):

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "I couldn't verify your server roles.",
                ephemeral=True,
            )
            return

        # Don't allow existing staff members to apply.
        if interaction.user.get_role(STAFF_ROLE_ID):
            await interaction.response.send_message(
                "You already have the staff role and cannot apply.",
                ephemeral=True,
            )
            return

        channel = interaction.guild.get_channel(APPLICATION_CHANNEL_ID)

        if channel is None:
            try:
                channel = await interaction.client.fetch_channel(
                    APPLICATION_CHANNEL_ID
                )
            except discord.HTTPException:
                await interaction.response.send_message(
                    "The application channel could not be found.",
                    ephemeral=True,
                )
                return

        embed = make_embed(
            "New Staff Application",
            f"Application submitted by {interaction.user.mention}",
        )

        embed.add_field(
            name="Applicant",
            value=f"{interaction.user.mention}\n`{interaction.user.id}`",
            inline=False,
        )

        embed.add_field(
            name="Age",
            value=self.age.value,
            inline=True,
        )

        embed.add_field(
            name="Roblox Username",
            value=self.roblox_username.value,
            inline=True,
        )

        embed.add_field(
            name="Previous Experience",
            value=self.experience.value,
            inline=False,
        )

        embed.add_field(
            name="Why should we choose you?",
            value=self.why_staff.value,
            inline=False,
        )

        embed.add_field(
            name="Availability",
            value=self.availability.value,
            inline=False,
        )

        embed.set_footer(text="Status: Pending")

        await channel.send(
            embed=embed,
            view=ApplicationReviewView(interaction.user.id),
        )

        await interaction.response.send_message(
            "Your staff application has been submitted.",
            ephemeral=True,
        )


class StaffApplicationButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Apply for Staff",
            style=discord.ButtonStyle.primary,
            custom_id="staff_application_button",
        )

    async def callback(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "I couldn't verify your roles.",
                ephemeral=True,
            )
            return

        # Existing staff cannot apply.
        if interaction.user.get_role(STAFF_ROLE_ID):
            await interaction.response.send_message(
                "You already have the staff role and cannot apply.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(
            StaffApplicationModal()
        )


class StaffApplicationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(StaffApplicationButton())


class ApplicationReviewView(discord.ui.View):
    def __init__(self, applicant_id: int):
        super().__init__(timeout=None)

        accept = discord.ui.Button(
            label="Accept",
            style=discord.ButtonStyle.success,
            custom_id=f"staff_accept_{applicant_id}",
        )

        deny = discord.ui.Button(
            label="Deny",
            style=discord.ButtonStyle.danger,
            custom_id=f"staff_deny_{applicant_id}",
        )

        accept.callback = self.accept_application
        deny.callback = self.deny_application

        self.add_item(accept)
        self.add_item(deny)

    async def authorized(
        self,
        interaction: discord.Interaction,
    ) -> bool:

        if not isinstance(interaction.user, discord.Member):
            return False

        return interaction.user.get_role(
            APPLICATION_REVIEW_ROLE_ID
        ) is not None

    async def accept_application(
        self,
        interaction: discord.Interaction,
    ):

        if not await self.authorized(interaction):
            await interaction.response.send_message(
                "You don't have permission to review applications.",
                ephemeral=True,
            )
            return

        applicant_id = int(
            interaction.data["custom_id"].replace(
                "staff_accept_",
                "",
            )
        )

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "This application cannot be processed here.",
                ephemeral=True,
            )
            return

        try:
            member = guild.get_member(applicant_id)

            if member is None:
                member = await guild.fetch_member(applicant_id)

            role = guild.get_role(STAFF_ROLE_ID)

            if role is None:
                await interaction.response.send_message(
                    "The staff role could not be found.",
                    ephemeral=True,
                )
                return

            await member.add_roles(
                role,
                reason="Staff application accepted",
            )

        except discord.NotFound:
            await interaction.response.send_message(
                "That applicant is no longer in the server.",
                ephemeral=True,
            )
            return

        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to give the staff role.",
                ephemeral=True,
            )
            return

        embed = interaction.message.embeds[0]
        embed.set_footer(
            text=f"Status: Accepted • Reviewed by {interaction.user}"
        )

        await interaction.response.edit_message(
            embed=embed,
            view=DisabledReviewView(),
        )

    async def deny_application(
        self,
        interaction: discord.Interaction,
    ):

        if not await self.authorized(interaction):
            await interaction.response.send_message(
                "You don't have permission to review applications.",
                ephemeral=True,
            )
            return

        embed = interaction.message.embeds[0]
        embed.set_footer(
            text=f"Status: Denied • Reviewed by {interaction.user}"
        )

        await interaction.response.edit_message(
            embed=embed,
            view=DisabledReviewView(),
        )


class DisabledReviewView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        accept = discord.ui.Button(
            label="Accepted",
            style=discord.ButtonStyle.success,
            disabled=True,
        )

        deny = discord.ui.Button(
            label="Denied",
            style=discord.ButtonStyle.danger,
            disabled=True,
        )

        self.add_item(accept)
        self.add_item(deny)


# =========================================================
# RULES
# =========================================================

RULES = {

    "general": (
        "**General Rules**\n\n"
        "1. Treat all members respectfully.\n"
        "2. Follow all instructions given by authorized staff.\n"
        "3. Do not intentionally disrupt ongoing roleplay.\n"
        "4. Keep all roleplay realistic and consistent with your character.\n"
        "5. Do not exploit bugs, glitches, or unintended game mechanics.\n"
        "6. Do not impersonate staff, law enforcement, or other players.\n"
        "7. Do not advertise other communities without permission.\n"
        "8. Do not abuse Discord channels, voice channels, or server features.\n"
        "9. Do not evade punishments using alternate accounts.\n"
        "10. Staff may intervene in situations not explicitly covered by these rules."
    ),

    "frp": (
        "**FRP - Fail Roleplay**\n\n"
        "1. All actions must remain reasonably realistic.\n"
        "2. Do not perform unrealistic stunts or actions your character could not reasonably survive.\n"
        "3. Do not ignore realistic consequences of injuries, collisions, or dangerous situations.\n"
        "4. Do not intentionally drive at unrealistic speeds without a valid roleplay reason.\n"
        "5. Do not use vehicles in ways that would be physically impossible in real life.\n"
        "6. Do not disregard injuries simply to continue an encounter.\n"
        "7. Do not intentionally exploit game mechanics to gain an unrealistic advantage.\n"
        "8. Do not perform actions that disregard the situation or the roleplay of others."
    ),

    "rdm": (
        "**RDM - Random Deathmatch**\n\n"
        "1. Killing or attacking another player without a valid roleplay reason is prohibited.\n"
        "2. You must have a legitimate in-character reason before initiating violence.\n\n"
        "**Exception:** Members with the County Serial Killer role are exempt from this requirement, provided they properly roleplay their actions.\n\n"
        "3. Do not attack players simply because they are annoying, nearby, or belong to a particular department.\n"
        "4. Retaliation must be based on an actual roleplay situation.\n"
        "5. Do not participate in random shootouts without an established scenario.\n"
        "6. Self-defense must be proportionate to the threat presented."
    ),

    "vdm": (
        "**VDM - Vehicle Deathmatch**\n\n"
        "1. Do not intentionally use a vehicle to run over or kill another player without a valid roleplay reason.\n"
        "2. Vehicles must not be used as weapons simply to provoke or eliminate players.\n"
        "3. Do not repeatedly ram vehicles without an appropriate roleplay justification.\n"
        "4. Accidental collisions must be roleplayed appropriately.\n"
        "5. Do not intentionally use vehicle physics or glitches to launch, trap, or injure other players."
    ),

    "nlr": (
        "**NLR - New Life Rule**\n\n"
        "1. After dying, your character must treat the death as a new life.\n"
        "2. Do not return to the scene of your death for revenge.\n"
        "3. Do not use information learned during your previous life to influence your new life.\n"
        "4. Do not immediately resume the same confrontation after respawning.\n"
        "5. You may not remember the exact circumstances of your death unless explicitly permitted.\n"
        "6. Do not use alternate characters to continue a situation that your previous character was involved in."
    ),

    "fearrp": (
        "**FearRP**\n\n"
        "1. Your character must value their life realistically.\n"
        "2. Comply with reasonable demands when faced with a credible and immediate threat.\n"
        "3. Do not pull out a weapon when someone already has you at gunpoint unless the situation reasonably allows it.\n"
        "4. Do not attempt to flee an unavoidable threat without a realistic opportunity.\n"
        "5. Do not disregard being outnumbered or surrounded when escape is not reasonably possible.\n"
        "6. Do not use game mechanics to avoid a situation your character would realistically fear."
    ),

    "combat_logging": (
        "**Combat Logging**\n\n"
        "1. Leaving the game to avoid arrest, death, consequences, or an ongoing roleplay situation is prohibited.\n"
        "2. Do not disconnect while being pursued, detained, or actively involved in an encounter.\n"
        "3. If you experience a genuine crash or connection issue, inform staff when possible.\n"
        "4. Do not intentionally switch servers or reset your character to escape consequences.\n"
        "5. Do not exploit respawning or reconnecting to gain an advantage."
    ),

    "exploiting": (
        "**Exploiting & Cheating**\n\n"
        "1. Exploiting, scripting, or using unauthorized third-party tools is prohibited.\n"
        "2. Do not abuse bugs or glitches for an advantage.\n"
        "3. Do not intentionally bypass game limitations.\n"
        "4. Do not use unauthorized methods to obtain restricted vehicles, equipment, or access.\n"
        "5. Report significant exploits to staff instead of abusing them.\n"
        "6. Do not knowingly assist another player in exploiting."
    ),

    "cop_baiting": (
        "**Cop Baiting**\n\n"
        "1. Do not intentionally provoke law enforcement without a valid roleplay reason.\n"
        "2. Do not repeatedly commit minor offenses solely to force police interaction.\n"
        "3. Do not deliberately obstruct police operations for entertainment.\n"
        "4. Do not repeatedly flee from officers without a reasonable roleplay scenario.\n"
        "5. Do not intentionally create unrealistic situations to waste department resources."
    ),

    "safe_zones": (
        "**Safe Zones**\n\n"
        "1. Violence and criminal activity are prohibited in designated safe zones.\n"
        "2. Do not use safe zones to escape an active pursuit or confrontation.\n"
        "3. Do not initiate combat immediately outside a safe zone to circumvent its protections.\n"
        "4. Do not intentionally lure players into safe zones to avoid consequences.\n"
        "5. Follow any additional restrictions established for specific safe zones."
    ),

    "department_staff": (
        "**Department & Staff Conduct**\n\n"
        "1. Department members must follow their department's procedures and chain of command.\n"
        "2. Do not abuse department permissions, equipment, or privileges.\n"
        "3. Do not impersonate department members.\n"
        "4. Do not interfere with another department's operations without a valid reason.\n"
        "5. Staff must remain impartial when handling reports and disputes.\n"
        "6. Do not use staff permissions to gain personal advantages.\n"
        "7. Department members must maintain appropriate roleplay standards while on duty.\n"
        "8. Follow any additional department-specific regulations."
    ),

    "roleplay_integrity": (
        "**Roleplay & Character Integrity**\n\n"
        "1. Keep your character's actions consistent with their role.\n"
        "2. Do not use out-of-character information to gain an in-character advantage (metagaming).\n"
        "3. Do not force outcomes on other players without allowing reasonable interaction (powergaming).\n"
        "4. Do not ignore injuries, vehicle damage, or other significant consequences.\n"
        "5. Do not intentionally interrupt another player's roleplay scenario.\n"
        "6. Keep out-of-character arguments separate from in-character situations."
    ),
}


class RulesSelect(discord.ui.Select):

    def __init__(self):
        options = [
            discord.SelectOption(
                label="General Rules",
                value="general",
            ),
            discord.SelectOption(
                label="FRP",
                value="frp",
                description="Fail Roleplay",
            ),
            discord.SelectOption(
                label="RDM",
                value="rdm",
                description="Random Deathmatch",
            ),
            discord.SelectOption(
                label="VDM",
                value="vdm",
                description="Vehicle Deathmatch",
            ),
            discord.SelectOption(
                label="NLR",
                value="nlr",
                description="New Life Rule",
            ),
            discord.SelectOption(
                label="FearRP",
                value="fearrp",
                description="Fear Roleplay",
            ),
            discord.SelectOption(
                label="Combat Logging",
                value="combat_logging",
            ),
            discord.SelectOption(
                label="Exploiting & Cheating",
                value="exploiting",
            ),
            discord.SelectOption(
                label="Cop Baiting",
                value="cop_baiting",
            ),
            discord.SelectOption(
                label="Safe Zones",
                value="safe_zones",
            ),
            discord.SelectOption(
                label="Department & Staff",
                value="department_staff",
            ),
            discord.SelectOption(
                label="Roleplay Integrity",
                value="roleplay_integrity",
            ),
        ]

        super().__init__(
            placeholder="Select a rules section...",
            options=options,
            custom_id="rules_section_select",
        )

    async def callback(self, interaction: discord.Interaction):

        content = RULES[self.values[0]]

        embed = make_embed(
            "Server Rules",
            content,
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )


class RulesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RulesSelect())


# =========================================================
# COMMANDS
# =========================================================

@bot.tree.command(
    name="staffapps",
    description="Send the staff application panel.",
)
async def staffapps(interaction: discord.Interaction):

    embed = make_embed(
        "Staff Applications",
        (
            "Interested in joining our staff team?\n\n"
            "Click the button below to submit a staff application."
        ),
    )

    await interaction.response.send_message(
        embed=embed,
        view=StaffApplicationView(),
    )


@bot.tree.command(
    name="rulesembed",
    description="Send the server rules panel.",
)
async def rulesembed(interaction: discord.Interaction):

    embed = make_embed(
        "Server Rules",
        (
            "Please select a category below to view the rules "
            "for that section.\n\n"
            "Your selected rules will only be visible to you."
        ),
    )

    await interaction.response.send_message(
        embed=embed,
        view=RulesView(),
    )


@bot.tree.command(
    name="say",
    description="Send a message to a channel.",
)
@app_commands.describe(
    channel="The channel to send the message in.",
    message="The message to send.",
)
async def say(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    message: str,
):

    await channel.send(message)

    await interaction.response.send_message(
        f"Message sent to {channel.mention}.",
        ephemeral=True,
    )


# =========================================================
# EVENTS
# =========================================================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print("Messages bot is online.")


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN environment variable is missing.")

bot.run(TOKEN)
