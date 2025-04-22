import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
import asyncio
import logging

# ======================
# FLASK KEEP-ALIVE SERVER
# ======================
app = Flask(__name__)

@app.route('/')
def home():
    return "🚂 Rizz Rail Bot is Online and Awake!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Start Flask in background thread
flask_thread = Thread(target=run_flask, daemon=True)
flask_thread.start()

# ======================
# DISCORD BOT SETUP
# ======================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True
intents.reactions = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
active_lfgs = {}  # {message_id: {players: [], max_players: int, expires_at: datetime}}

# ======================
# BOT COMMANDS
# ======================
@bot.command()
@commands.cooldown(1, 30, commands.BucketType.user)
async def railsteam(ctx):
    """Pings online members"""
    try:
        online_members = [
            member.mention for member in ctx.guild.members
            if member.status != discord.Status.offline
            and not member.bot
            and member != ctx.author
        ]
        await ctx.send(f"🚂 **ALL ABOARD!** {' '.join(online_members)}" if online_members else "No one is online! 🚂")
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command()
@commands.cooldown(1, 300, commands.BucketType.user)
async def lfg(ctx, game: str, slots: str):
    """Create LFG post (format: !lfg "Game" 2/4)"""
    try:
        open_slots, total_slots = map(int, slots.split('/'))
        
        embed = discord.Embed(
            title=f"🚂 LFG: {game}",
            description=f"**{open_slots}/{total_slots} slots open**\nReact with ✅ to join!",
            color=0x3498db
        )
        embed.set_footer(text=f"Hosted by {ctx.author.display_name} | Expires in 1 hour")
        embed.add_field(name="Players", value=ctx.author.mention)
        
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('✅')
        
        active_lfgs[msg.id] = {
            "players": [ctx.author.id],
            "max_players": total_slots,
            "expires_at": datetime.now() + timedelta(hours=1)
        }
    except ValueError:
        await ctx.send("❌ Use format: `!lfg \"Game Name\" open/total`")
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command()
@commands.cooldown(1, 60, commands.BucketType.user)
async def railsupdate(ctx):
    """Check Dead Rails updates"""
    try:
        embed = discord.Embed(
            title="🚂 Dead Rails v2.1.0",
            description="**Latest Update**\n- New haunted map\n- Fixed ghost train bug",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Couldn't fetch updates: {str(e)}")

# ======================
# EVENT HANDLERS
# ======================
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or reaction.emoji != '✅' or reaction.message.id not in active_lfgs:
        return
    
    lfg_data = active_lfgs[reaction.message.id]
    if user.id in lfg_data["players"]:
        await reaction.remove(user)
        return
    
    if len(lfg_data["players"]) >= lfg_data["max_players"]:
        await reaction.message.channel.send(f"❌ {user.mention} Group is full!")
        await reaction.remove(user)
        return
    
    lfg_data["players"].append(user.id)
    embed = reaction.message.embeds[0]
    embed.set_field_at(0, name="Players", value='\n'.join([f"<@{id}>" for id in lfg_data["players"]]))
    await reaction.message.edit(embed=embed)

@tasks.loop(minutes=5)
async def clean_expired_lfgs():
    now = datetime.now()
    to_remove = [msg_id for msg_id, data in active_lfgs.items() if data["expires_at"] < now]
    for msg_id in to_remove:
        try:
            del active_lfgs[msg_id]
        except:
            pass

# ======================
# ERROR HANDLING & STARTUP
# ======================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Please wait {error.retry_after:.0f} seconds before using this again!")
    else:
        await ctx.send("❌ An error occurred. Try again later.")

@bot.event
async def on_ready():
    clean_expired_lfgs.start()
    print(f"{bot.user.name} is online with these commands:\n"
          f"- !railsteam\n- !lfg\n- !railsupdate\n"
          f"Keep-alive server running on port 8080")

# ======================
# ANTI-CRASH SYSTEM
# ======================
async def main():
    while True:
        try:
            await bot.start('BOT_TOKEN')
        except Exception as e:
            print(f"Bot crashed: {e}. Restarting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())