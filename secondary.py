from discord import app_commands
from discord.app_commands import Choice
from discord import Embed, ButtonStyle
from discord.ui import Button, View
import discord, json, aiohttp, asyncio, os, pytz, re, sys, requests
from datetime import datetime
from functions.db import savedwcdb, loaddwcdb
from functions.config import loadconfig, saveconfig
from functions.format import format_time
from functions.setup import savesetup, loadsetup

class aclient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        intents.messages = True
        intents.members = True
        super().__init__(intents=intents)
        self.synced = False
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced:
            await self.tree.sync()
            self.synced = True
        print(f"Logged in as {self.user}")

        activity = discord.Activity(type=discord.ActivityType.watching, name=f"for scammers")
        await self.change_presence(activity=activity)

        print("Bot is in the following servers:")
        for guild in self.guilds:
            print(f"- {guild.name}: {guild.member_count} members")

        proof_view = ProofView([])
        self.add_view(proof_view)

currentinv = "dwcalert"
client = aclient()

dwcgroup = app_commands.Group(name="dwc",description=".")
timewastegroup = app_commands.Group(name="timewaste",description=".")
channelgroup = app_commands.Group(name="channel",description=".")

config = loadconfig()
staff = config.get("staff", "").split(",")
cooldown = {}

def blacklisted(user):
    return user.id == 1250977118192537615

def checkadmin(member):
    return member.guild_permissions.administrator

def getdiscordID(value):
    if value.startswith("dis_"):
        return value.replace("dis_", "")
    
async def checkrbxuser(user_id):
    url = f"https://users.roblox.com/v1/users/{user_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data["name"]
            return None
        
async def getrbxpfp(user_id: str) -> str:
    url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=60x60&format=Png&isCircular=false"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                image_url = data.get('data', [{}])[0].get('imageUrl', None)
                if image_url:
                    return image_url
                else:
                    raise Exception("No image URL found in the response.")
            else:
                raise Exception(f"Error fetching Roblox user data: {response.status}")
            
@client.event
async def on_member_join(member):
    try:
        dwcdb = loaddwcdb()
    except Exception as e:
        print(f"Error loading DWC database: {e}")
        return

    entry_id = f"dis_{member.id}"

    if entry_id in dwcdb:
        try:
            with open('data/setup.json', "r") as f:
                setup = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding setup data: {e}")
            return
        except Exception as e:
            print(f"Error loading setup data: {e}")
            return

        guild_id = str(member.guild.id)
        if guild_id in setup:
            config = setup[guild_id]
            dwc_role_id = config.get("dwc")
            if dwc_role_id:
                dwc_role = member.guild.get_role(dwc_role_id)
                if dwc_role:
                    try:
                        await member.add_roles(dwc_role)
                        print(f"Assigned DWC role to {member.name} in guild {member.guild.name}.")
                    except Exception as e:
                        print(f"Error assigning role to {member.name} in guild {member.guild.name}: {e}")
                else:
                    print(f"DWC role not found in guild {member.guild.name}.")
            else:
                print(f"DWC role ID not set in setup for guild {member.guild.name}.")
        else:
            print(f"Guild ID {guild_id} not found in setup.")


class RawProofButton(discord.ui.Button):
    def __init__(self, proof_list, message):
        super().__init__(label="Raw Proof", style=discord.ButtonStyle.primary, custom_id="raw_proof_button")
        self.proof_list = proof_list
        self.message = message

    async def callback(self, interaction: discord.Interaction):
        target_value = None

        if self.message.embeds:
            for embed in self.message.embeds:
                for field in embed.fields:
                    if field.name == "Target":
                        match = re.search(r'\(`(\d+)`\)', field.value)
                        if match:
                            target_value = match.group(1)
                            break

        if target_value:
            proof_data = loaddwcdb()
            proof_links_text = "No proof available."

            for prefix in ["dis_", "rbx_", "pp_", "ca_", "slx_"]:
                search_key = f"{prefix}{target_value}"

                if search_key in proof_data:
                    proof_entry = proof_data[search_key]
                    proof_links = proof_entry.get("proof", "").split()

                    proof_links_text = '\n'.join(proof_links)
                    break

            await interaction.response.send_message(proof_links_text, ephemeral=True)
        else:
            await interaction.response.send_message("No target value found.", ephemeral=True)

class ProofView(discord.ui.View):
    def __init__(self, proof_list, message_id=None):
        super().__init__(timeout=None)
        self.proof_list = proof_list
        self.message_id = message_id

    @discord.ui.button(label="Proof", style=discord.ButtonStyle.primary, custom_id="proof_button")
    async def proof_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        proof_embed = discord.Embed(color=discord.Color.blue(), description="Proofs:")
        added_urls = set()

        for i, url in enumerate(self.proof_list):
            if url not in added_urls:
                proof_embed.add_field(name=f"Proof {i + 1}", value=url, inline=False)
                added_urls.add(url)

        message = interaction.message
        target_value = None

        if message.embeds:
            for embed in message.embeds:
                for field in embed.fields:
                    if field.name == "Target":
                        match = re.search(r'\(`(\d+)`\)', field.value)
                        if match:
                            target_value = match.group(1)
                            break

        if target_value:
            proof_data = loaddwcdb()
            key_prefixes = ["dis_", "rbx_", "pp_", "ca_", "slx_"]

            for prefix in key_prefixes:
                search_key = f"{prefix}{target_value}"

                if search_key in proof_data:
                    proof_entry = proof_data[search_key]
                    proof_links = proof_entry.get("proof", "").split()

                    for url in proof_links:
                        if url not in added_urls:
                            proof_embed.add_field(name=f"Proof {len(added_urls) + 1}", value=url, inline=False)
                            added_urls.add(url)

        view = discord.ui.View(timeout=None)
        view.add_item(RawProofButton(self.proof_list, message))

        channel = interaction.channel
        if channel:
            await interaction.response.send_message(embed=proof_embed, view=view, ephemeral=True)
        else:
            pass


@dwcgroup.command(name="add", description="Adds DWC to a specific user or service")
@app_commands.describe(
    type="Select the service type",
    value="Value associated with the service type",
    reason="Reason for adding to DWC",
    proof="Proof URL(s) for the DWC, separated by commas or spaces"
)
@app_commands.choices(type=[
    app_commands.Choice(name="Discord", value="dis_"),
    app_commands.Choice(name="Roblox", value="rbx_"),
    app_commands.Choice(name="Paypal", value="pp_"),
    app_commands.Choice(name="Cashapp", value="ca_"),
    app_commands.Choice(name="Sellix", value="slx_"),
])
async def dwcadd(interaction: discord.Interaction, type: app_commands.Choice[str], value: str, reason: str, proof: str = None):
    print(f"dwc add command ran by: {interaction.user.name}")
    await interaction.response.defer(ephemeral=True, thinking=True)

    if str(interaction.user.id) not in staff:
        await interaction.followup.send("You do not have permission to run this command.", ephemeral=True)
        return

    try:
        dwcdb = loaddwcdb()
    except Exception as e:
        await interaction.followup.send(f"Error loading DWC database: {e}")
        return

    entry_id = f"{type.value}{value}"
    if entry_id in dwcdb:
        embed = discord.Embed(description=f"This user or service is already in the DWC database for {type.name}.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return

    if proof:
        proof_list = re.split(r'[,\s]+', proof)
        proof_list = [link for link in proof_list if link.startswith("https://")]
        formatted_proof = ' '.join(proof_list) if proof_list else 'NULL'
    else:
        proof_list = []
        formatted_proof = 'NULL'

    target_username = None
    target_id = None
    thumbnail_url = None
    rawtarget = value

    if type.value == "dis_":
        try:
            user = await client.fetch_user(int(value))
            if user.bot:
                await interaction.followup.send(f"You cannot add a bot to the DWC list.", ephemeral=True)
                return
            target_id = user.id
            target_username = user.name
            thumbnail_url = user.avatar.url if user.avatar else user.default_avatar.url
            rawtarget = target_username
        except discord.NotFound:
            await interaction.followup.send(f"User `{value}` not found.", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"Error fetching user: {e}", ephemeral=True)
            return

    elif type.value == "rbx_":
        target_username = await checkrbxuser(value)
        if not target_username:
            await interaction.followup.send(f"Roblox ID `{value}` does not exist.")
            return
        thumbnail_url = await getrbxpfp(value)

    elif type.value == "pp_":
        thumbnail_url = "https://i.imgur.com/UVQkAd4.png"
        if '@' not in value or '.' not in value:
            await interaction.followup.send(f"Invalid PayPal email address: {value}")
            return

    elif type.value == "ca_":
        thumbnail_url = "https://i.imgur.com/SriTgtn.png"
        if not value.isalnum() or not any(c.isalpha() for c in value) or len(value) > 20:
            await interaction.followup.send(f"Invalid Cashapp user: {value}.")
            return

    elif type.value == "slx_":
        thumbnail_url = "https://i.imgur.com/WEe6ycT.png"
        if not value.startswith("https://") or ("mysellix.io" not in value and "sellix.io" not in value):
            await interaction.followup.send(f"Invalid Sellix URL: {value}.")
            return
        match = re.search(r"https://([^\.]+)\.mysellix\.io|https://([^\.]+)\.sellix\.io", value)
        if match:
            target_value = match.group(1) if match.group(1) else match.group(2)
        else:
            target_value = value

    entry = {
        "server": str(interaction.guild_id),
        "reason": reason,
        "rawtarget": rawtarget,
        "by": str(interaction.user.id),
        "rawserver": interaction.guild.name,
        "time": [str(int(datetime.now().timestamp() * 1000))],
        "proof": formatted_proof,
        "rawmod": str(interaction.user)
    }

    embed = discord.Embed(title="DWC Entry Added", color=discord.Color.red())
    target_display = (f"<@{target_id}>(`{target_id}`)" if type.value == "dis_" else f"{target_username}(`{target_value}`)" if type.value == "slx_" else f"{value}(`{value}`)")
    embed.add_field(name="Target", value=target_display, inline=False)
    embed.add_field(name="Server", value=interaction.guild.name, inline=True)
    embed.add_field(name="Moderator", value=f"<@{interaction.user.id}> (`{interaction.user.name}`)", inline=True)
    embed.add_field(name="DWC Type", value=type.name, inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(text="Users with DWC (deal with caution) are responsible for or have been involved in scams. Do not deal with these users. Check if someone is DWC using /check.")

    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)

    view = ProofView(proof_list=proof_list) if proof_list else discord.ui.View()

    dwcdb[entry_id] = entry

    try:
        savedwcdb(dwcdb)
    except Exception as e:
        await interaction.followup.send(f"Error saving DWC database: {e}")
        return

    setup_path = "data/setup.json"
    try:
        with open(setup_path, "r") as f:
            setup = json.load(f)
    except json.JSONDecodeError as e:
        await interaction.followup.send(f"Error decoding setup data: {e}", ephemeral=True)
        return
    except Exception as e:
        await interaction.followup.send(f"Error loading setup data: {e}", ephemeral=True)
        return

    for guild_id, config in setup.items():
        guild = client.get_guild(int(guild_id))
        if guild is None:
            continue

        dwc_role_id = config.get("dwc")
        dwc_channel_id = config.get("dwc-channel")

        if dwc_role_id and target_id:
            member = guild.get_member(target_id)
            if member:
                dwc_role = guild.get_role(dwc_role_id)
                if dwc_role:
                    try:
                        await member.add_roles(dwc_role)
                    except Exception as e:
                        await interaction.followup.send(f"Error assigning role to {member.mention} in guild {guild.name}: {e}", ephemeral=True)

        if dwc_channel_id:
            dwc_channel = guild.get_channel(dwc_channel_id)
            if dwc_channel:
                try:
                    await dwc_channel.send(embed=embed, view=view)
                    await asyncio.sleep(0.25)
                except discord.Forbidden:
                    print(f"Bot lacks permission to send messages in channel {dwc_channel.name} in guild {guild.name}.")
                    continue
                except Exception as e:
                    await interaction.followup.send(f"Error sending message in DWC channel in guild {guild.name}: {e}", ephemeral=True)

    await interaction.followup.send(embed=embed, view=view)

@dwcgroup.command(name="check", description="Checks if a specific user or service is DWC")
@app_commands.describe(type="Select the service type", value="Value associated with the service type")
@app_commands.choices(type=[
    app_commands.Choice(name="Discord", value="dis_"),
    app_commands.Choice(name="Roblox", value="rbx_"),
    app_commands.Choice(name="Paypal", value="pp_"),
    app_commands.Choice(name="Cashapp", value="ca_"),
    app_commands.Choice(name="Sellix", value="slx_"),
])
async def dwccheck(interaction: discord.Interaction, type: app_commands.Choice[str], value: str):
    await interaction.response.defer(thinking=True)
    print(f"dwc check command ran by: {interaction.user.name}")

    try:
        dwcdb = loaddwcdb()
    except Exception as e:
        await interaction.followup.send(f"Error loading DWC database: {e}", ephemeral=True)
        return

    search_value = value.lower()
    entry_id = f"{type.value}{search_value}"

    entry = dwcdb.get(entry_id)
    if entry:
        embed = discord.Embed(title="DWC Entry Details", color=discord.Color.red())
        target_value = entry.get('rawtarget', value)
        formatted_proof = entry.get('proof', 'NULL')

        if isinstance(formatted_proof, str):
            proof_list = re.split(r'[ ,]+', formatted_proof) if formatted_proof != 'NULL' else []
        elif isinstance(formatted_proof, dict) and formatted_proof.get("NULL"):
            proof_list = []
        else:
            proof_list = [url for url in formatted_proof.values()]

        if type.value == "dis_":
            target_value = f"<@{value}>"
            try:
                user = await client.fetch_user(int(value))
                thumbnail_url = user.avatar.url if user.avatar else user.default_avatar.url
                embed.set_thumbnail(url=thumbnail_url)

                member = interaction.guild.get_member(int(value))
                setup = loadsetup()
                dwc_role_id = setup.get(str(interaction.guild.id), {}).get("dwc")

                if member and dwc_role_id:
                    dwc_role = interaction.guild.get_role(dwc_role_id)
                    if dwc_role and dwc_role not in member.roles:
                        await member.add_roles(dwc_role)
            except discord.NotFound:
                pass
            except Exception as e:
                await interaction.followup.send(f"Error fetching user: {e}", ephemeral=True)
                return
        elif type.value == "rbx_":
            target_value = await checkrbxuser(value)
            thumbnail_url = await getrbxpfp(value)
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)
        elif type.value == "ca_":
            embed.set_thumbnail(url="https://i.imgur.com/SriTgtn.png")
        elif type.value == "pp_":
            embed.set_thumbnail(url="https://i.imgur.com/UVQkAd4.png")
        elif type.value == "slx_":
            embed.set_thumbnail(url="https://i.imgur.com/WEe6ycT.png")

        embed.add_field(name="Target", value=f"{target_value}(`{value}`)", inline=False)
        embed.add_field(name="Server", value=entry.get('rawserver', 'Unknown'), inline=True)
        embed.add_field(name="Moderator", value=f"<@{entry['by']}> (`{entry['rawmod']}`)", inline=True)
        embed.add_field(name="DWC Type", value=type.name, inline=True)
        embed.add_field(name="Reason", value=entry.get("reason", "No reason provided"), inline=False)
        embed.set_footer(text="Users with DWC (deal with caution) are responsible for or have been involved in scams. Do not deal with these users.")

        if proof_list:
            view = ProofView(proof_list=proof_list)
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send(embed=embed)
    else:
        if type.value == "dis_":
            target_value = f"<@{value}>"
        elif type.value == "rbx_":
            target_value = await checkrbxuser(value)
        elif type.value == "slx_":
            match = re.search(r"https://([^\.]+)\.mysellix\.io|https://([^\.]+)\.sellix\.io", value)
            if match:
                target_value = match.group(1) if match.group(1) else match.group(2)
        else:
            target_value = value
        embed = discord.Embed(description=f"{target_value} has no reports of being DWC for **{type.name}**. However, it is recommended you use a **trusted** middleman whenever possible to avoid potential scams.", color=discord.Color.green())
        await interaction.followup.send(embed=embed)



@dwcgroup.command(name="remove", description="Removes DWC from a specific user or service")
@app_commands.describe(type="Select the service type", value="Value associated with the service type", reason="Reason for removing from DWC")
@app_commands.choices(type=[
    app_commands.Choice(name="Discord", value="dis_"),
    app_commands.Choice(name="Roblox", value="rbx_"),
    app_commands.Choice(name="Paypal", value="pp_"),
    app_commands.Choice(name="Cashapp", value="ca_"),
    app_commands.Choice(name="Sellix", value="slx_"),
])
async def dwcremove(interaction: discord.Interaction, type: app_commands.Choice[str], value: str, reason: str):
    print(f"DWC remove command ran by: {interaction.user.name}")
    
    if str(interaction.user.id) not in staff:
        await interaction.followup.send("You do not have permission to run this command.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        db = loaddwcdb()
    except Exception as e:
        await interaction.followup.send(f"Error loading DWC database: {e}", ephemeral=True)
        return

    entry_id = f"{type.value}{value}"
    if entry_id not in db:
        await interaction.followup.send(f"{value} is not in the DWC database for {type.name}.", ephemeral=True)
        return

    del db[entry_id]

    try:
        savedwcdb(db)
    except Exception as e:
        await interaction.followup.send(f"Error saving DWC database: {e}", ephemeral=True)
        return

    target_username, target_value, thumbnail_url = None, value, None

    if type.value == "dis_":
        target_value = f"<@{value}>"
        try:
            user = await client.fetch_user(int(value))
            thumbnail_url = user.avatar.url if user.avatar else user.default_avatar.url
            member = interaction.guild.get_member(int(value))
            setup = loadsetup()
            dwc_role_id = setup.get(str(interaction.guild.id), {}).get("dwc")

            if member and dwc_role_id:
                dwc_role = interaction.guild.get_role(dwc_role_id)
                if dwc_role and dwc_role not in member.roles:
                    await member.remove_roles(dwc_role)
        except discord.NotFound:
            pass
        except Exception as e:
            await interaction.followup.send(f"Error fetching user: {e}", ephemeral=True)
            return

    elif type.value == "rbx_":
        target_username = await checkrbxuser(value)
        if not target_username:
            await interaction.followup.send(f"Roblox ID `{value}` does not exist.")
            return
        target_value = target_username
        thumbnail_url = await getrbxpfp(value)

    elif type.value == "pp_":
        thumbnail_url = "https://i.imgur.com/UVQkAd4.png"
        if '@' not in value or '.' not in value:
            await interaction.followup.send(f"Invalid PayPal email address: {value}")
            return

    elif type.value == "ca_":
        thumbnail_url = "https://i.imgur.com/SriTgtn.png"
        if not value.isalnum() or not any(c.isalpha() for c in value) or len(value) > 20:
            await interaction.followup.send(f"Invalid Cashapp user: {value}.")
            return

    elif type.value == "slx_":
        thumbnail_url = "https://i.imgur.com/WEe6ycT.png"
        if not value.startswith("https://") or ("mysellix.io" not in value and "sellix.io" not in value):
            await interaction.followup.send(f"Invalid Sellix URL: {value}.")
            return
        match = re.search(r"https://([^\.]+)\.mysellix\.io|https://([^\.]+)\.sellix\.io", value)
        if match:
            target_value = match.group(1) if match.group(1) else match.group(2)
        else:
            target_value = value

    target_display = (f"{target_value}" if type.value == "slx_" else f"{value}(`{value}`)")
    embed = discord.Embed(title="DWC Entry Removed", color=discord.Color.green())
    embed.add_field(name="Target", value=target_display, inline=False)
    embed.add_field(name="Moderator", value=f"<@{interaction.user.id}> (`{interaction.user.name}`)", inline=True)
    embed.add_field(name="DWC Type", value=type.name, inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(text="This user has been removed from the DWC list. They are no longer considered a scam risk. However, it is still recommended you use a middleman")

    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)

    try:
        with open("data/setup.json", "r") as f:
            setup = json.load(f)
    except json.JSONDecodeError as e:
        await interaction.followup.send(f"Error decoding setup data: {e}", ephemeral=True)
        return
    except Exception as e:
        await interaction.followup.send(f"Error loading setup data: {e}", ephemeral=True)
        return

    for guild_id, config in setup.items():
        guild = client.get_guild(int(guild_id))
        if guild is None:
            continue

        dwc_role_id = config.get("dwc")
        dwc_channel_id = config.get("dwc-channel")

        if dwc_role_id:
            dwc_role = guild.get_role(dwc_role_id)
            member = guild.get_member(int(value)) if type.value == "dis_" else None

            if dwc_role and member:
                try:
                    await member.remove_roles(dwc_role)
                    if dwc_channel_id:
                        dwc_channel = guild.get_channel(dwc_channel_id)
                        embed.add_field(name="Server", value=guild.name, inline=False)
                        await dwc_channel.send(embed=embed)
                    await asyncio.sleep(0.25)
                except Exception as e:
                    await interaction.followup.send(f"Error removing role or sending announcement in guild {guild.name}: {e}", ephemeral=True)


@dwcgroup.command(name="edit", description="Edits a specific DWC entry")
@app_commands.describe(
    type="Select the service type",
    value="Value associated with the service type",
    reason="Reason for editing the DWC entry",
    proof="Proof URL(s) for the DWC, separated by commas or spaces"
)
@app_commands.choices(type=[
    app_commands.Choice(name="Discord", value="dis_"),
    app_commands.Choice(name="Roblox", value="rbx_"),
    app_commands.Choice(name="Paypal", value="pp_"),
    app_commands.Choice(name="Cashapp", value="ca_"),
    app_commands.Choice(name="Sellix", value="slx_"),
])
async def editdwc(interaction: discord.Interaction, type: app_commands.Choice[str], value: str, reason: str, proof: str = None):
    print(f"dwc edit command ran by: {interaction.user.name}")

    if str(interaction.user.id) not in staff:
        await interaction.followup.send("You do not have permission to run this command.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        dwcdb = loaddwcdb()
    except Exception as e:
        await interaction.followup.send(f"Error loading DWC database: {e}", ephemeral=True)
        return

    entry_id = f"{type.value}{value}"
    if entry_id not in dwcdb:
        await interaction.followup.send(f"No {type.name} entry found for {value}.", ephemeral=True)
        return

    dwcdb[entry_id]['reason'] = reason

    # Process the proof input
    if proof:
        proof_list = re.split(r'[,\s]+', proof)
        proof_list = [link for link in proof_list if link.startswith("https://")]
        formatted_proof = ' '.join(proof_list) if proof_list else 'NULL'
    else:
        current_proof = dwcdb[entry_id].get('proof', 'NULL')
        formatted_proof = current_proof

    dwcdb[entry_id]['proof'] = formatted_proof

    if type.value == "dis_":
        try:
            user = await client.fetch_user(int(value))
            if user.bot:
                await interaction.followup.send(f"You cannot add a bot to the DWC list.", ephemeral=True)
                return
            target_username = user.name
            dwcdb[entry_id]['rawtarget'] = target_username
        except discord.NotFound:
            await interaction.followup.send(f"User `{value}` not found.", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"Error fetching user: {e}", ephemeral=True)
            return

    elif type.value == "rbx_":
        target_username = await checkrbxuser(value)
        if not target_username:
            await interaction.followup.send(f"Roblox ID `{value}` does not exist.")
            return
        dwcdb[entry_id]['rawtarget'] = target_username

    dwcdb[entry_id]['time'] = [str(int(datetime.now().timestamp() * 1000))]

    try:
        savedwcdb(dwcdb)
    except Exception as e:
        await interaction.followup.send(f"Error saving DWC database: {e}", ephemeral=True)
        return

    entry = dwcdb[entry_id]
    embed = discord.Embed(title="DWC Entry Edited", color=discord.Color.yellow())
    target_display = (f"<@{value}>(`{value}`)" if type.value == "dis_" else f"{target_username}(`{value}`)")

    if type.value == "dis_":
        target_display = f"<@{value}>"
        try:
            user = await client.fetch_user(int(value))
            if user:
                embed.set_thumbnail(url=user.avatar.url)
        except Exception:
            pass
    elif type.value == "rbx_":
        target_display = await checkrbxuser(value)
        pfp_url = await getrbxpfp(value)
        if pfp_url:
            embed.set_thumbnail(url=pfp_url)

    elif type.value == "ca_":
        embed.set_thumbnail(url="https://i.imgur.com/SriTgtn.png")

    elif type.value == "pp_":
        embed.set_thumbnail(url="https://i.imgur.com/UVQkAd4.png")

    elif type.value == "slx_":
        embed.set_thumbnail(url="https://i.imgur.com/WEe6ycT.png")

    embed.add_field(name="Target", value=f"{target_display}(`{value}`)", inline=False)
    embed.add_field(name="Server", value=entry['rawserver'], inline=True)
    embed.add_field(name="Moderator", value=f"<@{entry['by']}> (`{entry['rawmod']}`)", inline=True)
    embed.add_field(name="DWC Type", value=type.name, inline=True)
    embed.add_field(name="Reason", value=entry["reason"], inline=False)
    embed.set_footer(text="Users with DWC (deal with caution) are responsible for or have been involved in scams. Do not deal with these users. Check if someone is DWC using /check.")

    # Create the ProofView instance
    proof_data = dwcdb[entry_id]['proof']
    if proof_data != "NULL":
        proof_urls = re.split(r'[ ,]+', proof_data)
        view = ProofView(proof_list=proof_list) if proof_list else discord.ui.View()
    else:
        view = discord.ui.View()

    await interaction.followup.send(embed=embed, view=view)

    try:
        with open("data/setup.json", "r") as f:
            setup = json.load(f)
    except json.JSONDecodeError as e:
        await interaction.followup.send(f"Error decoding setup data: {e}", ephemeral=True)
        return
    except Exception as e:
        await interaction.followup.send(f"Error loading setup data: {e}", ephemeral=True)
        return

    for guild_id, config in setup.items():
        guild = client.get_guild(int(guild_id))
        if guild is None:
            continue

        dwc_role_id = config.get("dwc")
        dwc_channel_id = config.get("dwc-channel")

        if dwc_role_id:
            role = guild.get_role(dwc_role_id)
            member = guild.get_member(int(value)) if type.value == "dis_" else None

            if role and member and role not in member.roles:
                try:
                    await member.add_roles(role)
                except Exception as e:
                    await interaction.followup.send(f"Error assigning role to {member.mention} in guild {guild.name}: {e}", ephemeral=True)
                    return

        if dwc_channel_id:
            dwc_channel = guild.get_channel(dwc_channel_id)
            if dwc_channel:
                try:
                    await dwc_channel.send(embed=embed, view=view)
                    await asyncio.sleep(0.25)
                except Exception as e:
                    await interaction.followup.send(f"Error sending message in DWC channel in guild {guild.name}: {e}", ephemeral=True)

@channelgroup.command(name="set", description="Sets a channel for DWC reports")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):

    if blacklisted(interaction.user) or not checkadmin(interaction.user):
        await interaction.followup.send("You do not have permission to run this command.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        with open("data/setup.json", "r") as f:
            setup = json.load(f)
    except Exception as e:
        await interaction.followup.send(f"Error loading setup data: {e}", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    if guild_id not in setup:
        setup[guild_id] = {"dwc-channel": None, "dwc": None, "timewaster": None}
    
    setup[guild_id]["dwc-channel"] = channel.id

    try:
        with open("data/setup.json", "w") as f:
            json.dump(setup, f, indent=4)
    except Exception as e:
        await interaction.followup.send(f"Error saving setup data: {e}", ephemeral=True)
        return

    await interaction.followup.send(f"DWC report channel has been set to {channel.mention}")

@channelgroup.command(name="remove", description="Removes the DWC report channel")
async def removechannel(interaction: discord.Interaction):
    print(f"remove channel command ran by: {interaction.user.name}")
    await interaction.response.defer(ephemeral=True, thinking=True)
    if blacklisted(interaction.user) or not checkadmin(interaction.user):
        await interaction.followup.send("You do not have permission to run this command.", ephemeral=True)
        return



    try:
        with open("data/setup.json", "r") as f:
            setup = json.load(f)
    except Exception as e:
        await interaction.followup.send(f"Error loading setup data: {e}", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    if guild_id in setup:
        setup[guild_id].pop("dwc-channel", None)
        try:
            with open("data/setup.json", "w") as f:
                json.dump(setup, f, indent=4)
        except Exception as e:
            await interaction.followup.send(f"Error saving setup data: {e}", ephemeral=True)
            return

    await interaction.followup.send("DWC report channel has been removed.")

@client.tree.command(name="setrole", description="Sets a role for a server")
@app_commands.choices(type=[
    app_commands.Choice(name="DWC", value="dwc"),
    app_commands.Choice(name="Timewaster", value="timewaster")
])
async def setrole(interaction: discord.Interaction, role: discord.Role, type: app_commands.Choice[str]):
    

    if blacklisted(interaction.user) or not checkadmin(interaction.user):
        await interaction.followup.send("You do not have permission to run this command.", ephemeral=True)
        return
    
    await interaction.response.defer(thinking=True)
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.isfile("data/setup.json"):
        with open("data/setup.json", "w") as f:
            json.dump({}, f, indent=4)

    try:
        with open("data/setup.json", "r") as f:
            setup = json.load(f)
    except json.JSONDecodeError as e:
        await interaction.followup.send(f"Error decoding setup data: {e}", ephemeral=True)
        return
    except Exception as e:
        await interaction.followup.send(f"Error loading setup data: {e}", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    if guild_id not in setup:
        setup[guild_id] = {"dwc": None, "timewaster": None}

    if type.value == "dwc":
        setup[guild_id]["dwc"] = role.id
    elif type.value == "timewaster":
        setup[guild_id]["timewaster"] = role.id

    try:
        with open("data/setup.json", "w") as f:
            json.dump(setup, f, indent=4)
    except Exception as e:
        await interaction.followup.send(f"Error saving setup data: {e}", ephemeral=True)
        return

    await interaction.followup.send('Roles have been updated.')

@client.tree.command(name="rules", description="sends a rules embed")
async def rules(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    print(f"rules command ran by: {interaction.user.name}")
    embed = discord.Embed(title="Dwc Rules", description="Scamming ✅\nAttempted Scamming ✅\nBreaching Contract/Trade Agreement ✅\nLocking ✅ (lock threats against someone who is not following through with deal is the only exception)\nRevenge Scamming ✅ (if you are well established and have a good reputation, you may be given a short time window to pay this back to have DWC removed)\nLetting someone get scammed ✅ (only counts if you know a scam will take place and don't warn to help prevent it)\nAssisting a DWC in a DWC activity ✅\nReverting ✅ (unless you are reverting an account that was involved in a scam deal immediately after it is processed)\nCharging back ✅ (paypal, cash app, bank, etc.)\nRefusing Trusted MM ✅\nBeaming Discord/Roblox accounts ✅\nFaking vouches ✅\nFake OGI (OGE, OGB, etc.) ✅ (advertising as simply \"OGE\" or \"OGB\" means the account must already have been tested. If not, then it must be advertised as untested)\nSelling/Trading Free Items ✅\nLeaving Servers To Avoid DWC ✅\nImpersonating (Larping) ✅ (impersonating with ill intent is DWC; trolling via impersonation is not DWC but is also not recommended)\nFalse Advertising ✅ (leaving out important info/history about an item/acc that results it being unsellable (no mention about an account being DWC, Underaged and/or Unsafe) or pulled by OGO. If the user mistakenly misinforms about their listing, they have 24h after being told to correct it before it is DWC)\nFailing To Prove Ownership ✅\nUsing Fake Images/Videos In A Deal ✅\nLying About C/O ✅\nRatting ✅\nDefamation ✅\nDDOSing Other WiFi Networks ✅\nSending Beam Links ✅\nBuying Any Dox From A Doxxer ✅\nMaking False DWC claim(s) (may result in being ticket banned) 🟨 (can include fake/made up claims and/or faked evidence; this is up to mod discretion and ultimately depends on the circumstances and the user's reputation)\nDoxxing 🟨 (doxxing is DWC unless you are doxxing someone who is DWC for scamming, revenge scamming doesn’t count)\nRequesting To Lock 🟨 (depends on circumstances)\nJoking About Being DWC 🟨 (depends on situation and up to staff discretion; please avoid doing this because it becomes hard to tell what is and isn’t a joke)\nLeaking Account Name(s) 🟨 (up to staff discretion: depends on situation, the account in question, the severity of the leak, and the intentions behind it)\nPassword Guessing (PGing) ❌\nTrading for DWC Accounts ❌ (this only applies to individuals who have no knowledge of an account that's been involved in a scam)\nDiscord raiding/nuking ❌ (just enable member verification)")
    await interaction.followup.send(embed=embed)

@client.tree.command(name="setup", description="Sets up the bot in this server, run this when the bot is first added")
async def setup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)

    if blacklisted(interaction.user) or not checkadmin(interaction.user):
        await interaction.followup.send("You do not have permission to run this command.", ephemeral=True)
        return
    
    embed = discord.Embed(title="Server Setup",
                      description="**IMPORTANT: YOU MUST READ EVERYTHING BELOW BEFORE CONTINUING**")

    embed.add_field(name="Info",
                    value="our bot is a discord bot that makes DWC syncrhonization easy across servers. We provide a comprehensive database of DWC/time waster users and accounts that are updated in real time across servers. Once a user is added to the database, they are given their role accordingly in every server the bot is in.",
                    inline=False)
    embed.add_field(name="Trusted",
                    value="This bot can be added to any server, but only trusted servers can add/remove from this database. You can apply to be trusted in our discord with the `/discord` command. **As a trusted server, the server owner is responsible for any misuse by mods. Any misuse or abuse will result in a removal of trusted.**",
                    inline=False)
    embed.add_field(name="Roles",
                    value="Make sure you configure your roles correctly after this using `/setrole`.",
                    inline=False)
    embed.add_field(name="Appeal",
                    value="Users can appeal their DWC/time waster designation (if they were wrongly accused) either in the server they were given it in or in our discord server which you can join with `/discord`.",
                    inline=False)
    embed.add_field(name="Commands",
                    value="Users trused by our server will be able to edit the DWC database from their server (if the server is trusted) under the server's name. Only give this role to people you trust as the server as a whole will be held reliable for any misuse/abuse of the bot. Make sure that all users with this permission has the Manage Messages permission.",
                    inline=False)
    embed.add_field(name="Attaching proof",
                    value="You can use any URL or image hosting to attach proof in DWC reports. You can additionally send the image anywhere in any channel, copy the media link, and then remove everything after `?ex=` in the URL (example: `https://media.discordapp.net/attachments/1118939971181625404/1118940330671218699/IMG_5951.png`)",
                    inline=False)
    embed.add_field(name="Help",
                    value="Additional bot help can be given in our discord server. Run `/discord` to get the invite.",
                    inline=False)
    
    message = await interaction.followup.send(embed=embed)

    class CombinedView(discord.ui.View):
        def __init__(self, message, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.countdown_time = 10
            self.message = message
            self.cancelled = False

        @discord.ui.button(label="Continue", style=discord.ButtonStyle.danger, custom_id="continue_button")
        async def continue_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
            if button.disabled:
                return

            button.disabled = True
            await interaction.response.edit_message(view=self)


            if not os.path.exists("data"):
                os.makedirs("data")
            if not os.path.isfile("data/setup.json"):
                with open("data/setup.json", "w") as f:
                    json.dump({}, f, indent=4)
            try:
                with open("data/setup.json", "r") as f:
                    if os.path.getsize("data/setup.json") == 0:
                        setup = {}
                    else:
                        setup = json.load(f)
            except json.JSONDecodeError as e:
                await interaction.followup.send(f"Error decoding setup data: {e}", ephemeral=True)
                return
            except Exception as e:
                await interaction.followup.send(f"Error loading setup data: {e}", ephemeral=True)
                return

            guild_id = str(interaction.guild.id)
            if guild_id not in setup:
                setup[guild_id] = {
                    "dwc-channel": None,
                    "dwc": None,
                    "timewaster": None
                }

            try:
                with open("data/setup.json", "w") as f:
                    json.dump(setup, f, indent=4)
            except Exception as e:
                await interaction.followup.send(f"Error saving setup data: {e}", ephemeral=True)
                return

            new_embed = discord.Embed(description="This server has been set up. You should now use `/getconfig` to set up your roles and then run `/sync` to sync your server with our database.")
            await self.message.edit(embed=new_embed, view=None)

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="cancel_button")
        async def cancel_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.defer(ephemeral=True)
            self.cancelled = True
            try:
                await self.message.delete()
            except discord.errors.NotFound:
                pass

        async def start_countdown(self, interaction: discord.Interaction, button: discord.ui.Button):
            while self.countdown_time > 0:
                if self.cancelled:
                    return
                button.label = f"Continue ({self.countdown_time})"
                button.style = discord.ButtonStyle.danger
                button.disabled = True
                await interaction.edit_original_response(view=self)
                await asyncio.sleep(1)
                self.countdown_time -= 1

            button.disabled = False
            button.label = "Continue"
            button.style = discord.ButtonStyle.grey
            if not self.cancelled:
                await interaction.edit_original_response(view=self)

    view = CombinedView(message)
    await view.start_countdown(interaction, view.children[0])


@client.tree.command(name="sync", description="Syncs every user in the server's roles with our database")
async def sync(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    if blacklisted(interaction.user) or not checkadmin(interaction.user):
        await interaction.followup.send("You do not have permission to run this command.", ephemeral=True)
        return
    guild_id = str(interaction.guild.id)
    user_id = str(interaction.user.id)

    if guild_id not in cooldown:
        cooldown[guild_id] = {}

    COOLDOWN_PERIOD = 5 * 1000

    if user_id in cooldown[guild_id] and (datetime.now() - cooldown[guild_id][user_id]).total_seconds() * 1000 < COOLDOWN_PERIOD:
        remaining_time = COOLDOWN_PERIOD - (datetime.now() - cooldown[guild_id][user_id]).total_seconds() * 1000
        embed = discord.Embed(
            description=f"You are on cooldown! Try again in `{format_time(int(remaining_time / 1000))}`.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    setup = loadsetup()
    
    if guild_id not in setup:
        setup[guild_id] = {
            "dwc-channel": None,
            "dwc": None,
            "timewaster": None,
            "last-sync": None
        }
    
    lastsync = setup[guild_id].get("last-sync")
    TIME_BETWEEN_SYNCS = 12 * 60 * 60 * 2 # 24 hours

    if lastsync:
        last_sync_time = datetime.strptime(lastsync, "%Y-%m-%d %H:%M:%S")
        if (datetime.now() - last_sync_time).total_seconds() < TIME_BETWEEN_SYNCS:
            remaining_time = TIME_BETWEEN_SYNCS - (datetime.now() - last_sync_time).total_seconds()
            embed = discord.Embed(
                description=f"A sync has been run on this server too recently. Try again in `{format_time(int(remaining_time))}`.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

    chicago_tz = pytz.timezone('America/Chicago')
    setup[guild_id]["last-sync"] = datetime.now(chicago_tz).strftime("%Y-%m-%d %H:%M:%S")
    savesetup(setup)
    
    cooldown[guild_id][user_id] = datetime.now()
    
    embed = discord.Embed(
        title="Check everyone",
        description="You are about to run a DWC/Time Waster check on every member in the server. **Please read below before continuing.**",
        color=discord.Color.yellow()
    )
    embed.add_field(name="Note", value="You should only do this once per server when you first add the bot to the server, or if you reset the role or otherwise lose track of every DWC/Time Waster member. As new members are made DWC, they are updated automatically so there is no need to run this command regularly.", inline=False)
    embed.add_field(name="How it works", value="This command will check every member in this server for their DWC/Time Waster status. Everyone in our database who is in this server will be given their roles accordingly, however we will not remove members who already have the role but are not in our database. It is best practice to remove any member of your DWC/Time Waster roles and let this command sync your members with our database.", inline=False)
    embed.add_field(name="Roles", value=f"Make sure you configured your roles correctly before this using `/setrole`. The current role configuration is {setup[guild_id].get('dwc', '`none set`')} (DWC) and {setup[guild_id].get('timewaster', '`none set`')} (Time Waster).", inline=False)

    cancel = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.danger, custom_id="cancel")

    async def button_callback(inter):
        await inter.response.defer(ephemeral=True, thinking=True)
        await inter.followup.send("Sync cancelled.", ephemeral=True)

    cancel.callback = button_callback

    view = discord.ui.View()
    view.add_item(cancel)

    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    await asyncio.sleep(5)
    dwcdb = loaddwcdb()

    dwc_role_id = setup[guild_id].get("dwc")
    if not dwc_role_id:
        await interaction.followup.send("DWC role not set up for this server.", ephemeral=True)
        return

    dwc_role = interaction.guild.get_role(dwc_role_id)
    if not dwc_role:
        await interaction.followup.send("DWC role not found in this server.", ephemeral=True)
        return
    
    for member in interaction.guild.members:
        user_id_str = f"dis_{member.id}"
        try:
            if user_id_str in dwcdb:
                if dwc_role not in member.roles:
                    await member.add_roles(dwc_role, reason="DWC sync")
            else:
                if dwc_role in member.roles:
                    await member.remove_roles(dwc_role, reason="DWC sync")
        except discord.Forbidden:
            pass
        except Exception as e:
            pass

    embed = discord.Embed(
        title="Sync Completed",
        description="The sync process has completed successfully.",
        color=discord.Color.green()
    )
    await interaction.followup.send(embed=embed, ephemeral=True)

@client.tree.command(name="getconfig", description="Provides a list of current roles and channels")
async def getconfig(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    print(f"get config command ran by: {interaction.user.name}")

    try:
        with open("data/setup.json", "r") as f:
            setup = json.load(f)
    except Exception as e:
        await interaction.followup.send(f"Error loading setup data: {e}", ephemeral=True)
        return

    guildsetup = setup.get(str(interaction.guild.id), {
        "dwc-channel": None,
        "dwc": None,
        "timewaster": None
    })

    dwcchannel = guildsetup.get("dwc-channel", None)
    dwc = guildsetup.get("dwc", None)
    timewaster = guildsetup.get("timewaster", None)

    dwcchannel_display = f"<#{dwcchannel}>" if dwcchannel else "none set"
    dwc_display = f"<@&{dwc}>" if dwc else "none set"
    timewaster_display = f"<@&{timewaster}>" if timewaster else "none set"

    embed = discord.Embed(color=discord.Color.green())
    embed.add_field(name="DWC Alerts", value=dwcchannel_display, inline=False)
    embed.add_field(name="DWC Role", value=dwc_display, inline=False)
    embed.add_field(name="Time Waster Role", value=timewaster_display, inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)


@client.tree.command(name="discord", description="An invite to our main discord server")
async def channelremove(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    print(f"discord command ran by: {interaction.user.name}")
    await interaction.followup.send(f"https://discord.gg/{currentinv}")


@client.tree.command(name="appeal", description="Appeal a DWC or time waster entry")
async def appeal(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    print(f"appeal command ran by: {interaction.user.name}")

    embed = discord.Embed(
        description="If you believe you were wrongly accused or found an error in our database, open a ticket in our discord server below.",
        color=discord.Color.yellow()
    )
    embed.set_footer(text="Note: If you are appealing your own DWC or time waster and you were not wrongly accused, do not bother opening a ticket. Entries in our database are permanent.")

    button = Button(label="Join Discord", url=f"https://discord.gg/{currentinv}", style=ButtonStyle.link)
    view = View()
    view.add_item(button)

    await interaction.followup.send(embed=embed, view=view, ephemeral=True)

client.start_time = datetime.now()
@client.tree.command(name="uptime", description="displays how long bot has been running and ping info")
async def uptime(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    print(f"appeal command ran by: {interaction.user.name}")
    current_time = datetime.now()
    uptime = current_time - client.start_time

    days, reminder = divmod(uptime.total_seconds(), 86400)
    hours, reminder = divmod(reminder, 3600)
    minutes, seconads = divmod(reminder, 60)
    embed = discord.Embed(title="Uptime", description=f"`{int(days)}d {int(hours)}h {int(minutes)}m {int(seconads)}s`", color=discord.Color.green())
    embed.set_footer(text=f"Ping: {round(client.latency * 1000)}")
    await interaction.followup.send(embed=embed)

@client.tree.command(name="stats", description="Displays statistic info about dwc alert.")
async def stats(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    print(f"stats command ran by: {interaction.user.name}")
    
    server_count = len(client.guilds)
    user_count = sum(guild.member_count for guild in client.guilds)

    embed = discord.Embed(
        title="Stats",
        description=f"**Server Count:** `{str(server_count)}`\t**Users:** `{str(user_count)}`",
        color=discord.Color.from_rgb(0, 0, 0)
    )
    await interaction.followup.send(embed=embed)

ownerids = [682830561714110502, 1216226450739429377, 517298185966977024, 576106133295464478]

@client.tree.command(name="restart", description="hard resets bot")
async def restart(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    if interaction.user.id not in ownerids:
        embed = discord.Embed(description="Sorry you do not have permission to run this command.", color=discord.Color.red())
        await interaction.followup.send(embed=embed)
        return

    print("Bot restart has been initiated")

    await interaction.followup.send("Bot restarting...", ephemeral=True)
    os.execv(sys.executable, ['python main.py'] + sys.argv)

@client.tree.command(name='upload', description='Upload an image to Imgur')
@app_commands.describe(image='The image file to upload')
async def upload(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer(thinking=True, ephemeral=True)
    if str(interaction.user.id) not in staff:
        await interaction.followup.send("You do not have permission to use this command.")
        return



    image_path = f'./temp_{image.filename}'
    await image.save(image_path)

    with open(image_path, 'rb') as file:
        files = {
            'image': (image.filename, file, 'image/gif'),
            'type': (None, 'file'),
            'name': (None, image.filename),
        }

        headers = {
            'Authorization': f'Client-ID 546c25a59c58ad7',
        }

        response = requests.post('https://api.imgur.com/3/upload', headers=headers, files=files)

    if response.status_code == 200:
        data = response.json()
        image_url = data['data']['link']
        await interaction.followup.send(f'{image_url}')
    else:
        await interaction.followup.send('Failed to upload image.')
    os.remove(image_path)

client.tree.add_command(dwcgroup)
client.tree.add_command(channelgroup)

client.run("MTYOUR_DISCORD_BOT_TOKEN")
#client.run("MTYOUR_DISCORD_BOT_TOKEN")


