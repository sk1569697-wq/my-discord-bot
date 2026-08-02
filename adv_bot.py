import discord
from discord.ext import commands
import aiohttp
import asyncio
import random

bot = commands.Bot(command_prefix="?", intents=discord.Intents.all())

# ⚠️ अपना नया टोकन यहाँ डालें (पुराना रीसेट करने के बाद)
BOT_TOKEN = "MTUyOTc3MjcwNTc4MjY5Nzk4NA.GIr_VV.KFoI3uFS4kOisztBwZDFWOrs8Vuml_Z08nHY04"

user_database = {}

def generate_advertiser_embeds(member, slot_num, status="Stopped", config_state="Not configured"):
    embed1 = discord.Embed(title="💎 VIP Advertising Access", color=discord.Color.purple())
    embed1.description = f"Welcome {member.mention} to your private ad service.\n✨ **Duration Active:** 3 Days\n✨ **Available Slots:** 2"
    embed1.add_field(
        name="🚀 Easy Setup Guide:", 
        value="Step 1: Press 📝 **Configure**\nStep 2: Fill your account data & ad link\nStep 3: Press ▶ **Start**", 
        inline=False
    )
    
    embed2 = discord.Embed(title=f"📡 Live Status Room — Slot {slot_num}", color=discord.Color.gold())
    status_emoji = "🔴" if status == "Stopped" else "🟢"
    config_emoji = "❌" if config_state == "Not configured" else "✅"
    
    embed2.add_field(name="Current State", value=f"{status_emoji} {status}", inline=True)
    embed2.add_field(name="Setup Config", value=f"{config_emoji} {config_state}", inline=True)
    embed2.set_footer(text="Powered by Premium Advertiser System")
    
    return [embed1, embed2]

class ConfigureModal(discord.ui.Modal):
    def __init__(self, slot_num, main_message):
        super().__init__(title=f"Setup variables for Slot {slot_num}")
        self.slot_num = slot_num
        self.main_message = main_message
        
        self.user_token = discord.ui.TextInput(label="Paste your User Token *", placeholder="Enter your token here...")
        self.channels = discord.ui.TextInput(label="Target Channel IDs *", placeholder="Comma-separated IDs...")
        self.delay_range = discord.ui.TextInput(label="Interval Time (Seconds) *", default="10")
        self.ad_content = discord.ui.TextInput(label="Ad Message Text *", style=discord.TextStyle.long)
        
        self.add_item(self.user_token)
        self.add_item(self.channels)
        self.add_item(self.delay_range)
        self.add_item(self.ad_content)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        channel_list = [cid.strip() for cid in self.channels.value.split(",") if cid.strip().isdigit()]
        
        if not channel_list:
            await interaction.followup.send("❌ Channel IDs must be valid numbers!", ephemeral=True)
            return

        try:
            if "-" in self.delay_range.value:
                parts = self.delay_range.value.split("-")
                min_d, max_d = int(parts[0].strip()), int(parts[1].strip())
            else:
                min_d = int(self.delay_range.value.strip())
                max_d = min_d
        except:
            min_d, max_d = 10, 10

        user_database[user_id]["slots"][self.slot_num] = {
            "token": self.user_token.value,
            "channels": channel_list,
            "min_delay": min_d,
            "max_delay": max_d,
            "message": self.ad_content.value,
            "is_running": False
        }
        
        user_database[user_id]["current_config"] = "Configured"
        embeds = generate_advertiser_embeds(interaction.user, self.slot_num, status=user_database[user_id]["current_status"], config_state="Configured")
        await self.main_message.edit(embeds=embeds)
        await interaction.followup.send(f"✅ Slot {self.slot_num} setup completed safely!", ephemeral=True)

class ProfessionalPanel(discord.ui.View):
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member
        self.current_slot = 1
        self.main_message = None

    @discord.ui.button(label="Slot 1", style=discord.ButtonStyle.green, row=0)
    async def slot1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_slot(interaction, 1)

    @discord.ui.button(label="Slot 2", style=discord.ButtonStyle.secondary, row=0)
    async def slot2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.switch_slot(interaction, 2)

    @discord.ui.button(label="Configure", style=discord.ButtonStyle.blurple, emoji="📝", row=1)
    async def configure_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ConfigureModal(self.current_slot, self.main_message))

    @discord.ui.button(label="Start", style=discord.ButtonStyle.green, emoji="▶", row=1)
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        slot_data = user_database.get(user_id, {}).get("slots", {}).get(self.current_slot)
        
        if not slot_data or "token" not in slot_data:
            await interaction.followup.send(f"❌ Setup Slot {self.current_slot} before running!", ephemeral=True)
            return
        if slot_data["is_running"]:
            await interaction.followup.send(f"❌ Ad cycle is already running on Slot {self.current_slot}!", ephemeral=True)
            return

        slot_data["is_running"] = True
        user_database[user_id]["current_status"] = "Running"
        
        embeds = generate_advertiser_embeds(interaction.user, self.current_slot, status="Running", config_state="Configured")
        await self.main_message.edit(embeds=embeds)
        
        asyncio.create_task(self.run_advertiser(user_id, self.current_slot, interaction.user))
        await interaction.followup.send(f"🟢 Ad loops initialized on Slot {self.current_slot}!", ephemeral=True)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, emoji="⏹", row=1)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        slot_data = user_database.get(user_id, {}).get("slots", {}).get(self.current_slot)
        
        if slot_data: 
            slot_data["is_running"] = False
        user_database[user_id]["current_status"] = "Stopped"
        
        embeds = generate_advertiser_embeds(interaction.user, self.current_slot, status="Stopped", config_state=user_database[user_id]["current_config"])
        await self.main_message.edit(embeds=embeds)
        await interaction.followup.send(f"🛑 Ad cycles paused on Slot {self.current_slot}.", ephemeral=True)

    async def switch_slot(self, interaction, slot_num):
        user_id = interaction.user.id
        self.current_slot = slot_num
        
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label and child.label.startswith("Slot"):
                if child.label == f"Slot {slot_num}":
                    child.style = discord.ButtonStyle.green
                else:
                    child.style = discord.ButtonStyle.secondary
                    
        slot_data = user_database.get(user_id, {}).get("slots", {}).get(slot_num, {})
        status = "Running" if slot_data.get("is_running") else "Stopped"
        config = "Configured" if "token" in slot_data else "Not configured"
        
        user_database[user_id]["current_status"] = status
        user_database[user_id]["current_config"] = config
        
        embeds = generate_advertiser_embeds(interaction.user, slot_num, status=status, config_state=config)
        await interaction.response.edit_message(embeds=embeds, view=self)

    async def run_advertiser(self, user_id, slot_num, user_obj):
        data = user_database[user_id]["slots"][slot_num]
        headers = {"Authorization": data["token"], "Content-Type": "application/json"}
        payload = {"content": data["message"]}
        
        async with aiohttp.ClientSession() as session:
            while data["is_running"]:
                for channel_id in data["channels"]:
                    if not data["is_running"]: 
                        break
                    # FIX: Correct Discord API Endpoint
                    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
                    try:
                        async with session.post(url, headers=headers, json=payload) as res:
                            if res.status == 401:
                                data["is_running"] = False
                                user_database[user_id]["current_status"] = "Stopped"
                                embeds = generate_advertiser_embeds(user_obj, slot_num, status="Stopped", config_state="Configured")
                                await self.main_message.edit(embeds=embeds)
                                await user_obj.send(f"❌ Slot {slot_num} Invalid token passed! Cycle aborted.")
                                break
                            elif res.status in (200, 201):
                                print(f"[Slot {slot_num} - Done] Sent message to channel {channel_id}")
                    except Exception as e:
                        print(f"[Exception Slot {slot_num}] {e}")
                    await asyncio.sleep(3)
                    
                if not data["is_running"]: 
                    break
                sleep_time = random.randint(data["min_delay"], data["max_delay"])
                print(f"[Slot {slot_num}] Sleeping loop for {sleep_time} seconds...")
                await asyncio.sleep(sleep_time)

@bot.command()
async def give(ctx, member: discord.Member):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Admin permission is required!")
        return
        
    user_database[member.id] = {
        "slots": {},
        "current_status": "Stopped",
        "current_config": "Not configured"
    }
    embeds = generate_advertiser_embeds(member, 1, status="Stopped", config_state="Not configured")
    view = ProfessionalPanel(member)
    
    msg = await member.send(embeds=embeds, view=view)
    view.main_message = msg

bot.run(BOT_TOKEN)