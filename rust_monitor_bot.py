import discord
from discord import app_commands
from discord.ext import tasks
import socket
import asyncio
from datetime import datetime, timezone

# ===== CONFIG =====
BOT_TOKEN = "12344567890"  # Replace with your bot token


# ===== BOT SETUP =====
intents = discord.Intents.default()  # No privileged intents needed
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# Store active monitoring tasks: {channel_id_host_port: asyncio.Task}
monitor_tasks = {}

# ===== UTILITY FUNCTIONS =====
def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def query_rust_server(host, port, timeout=3):
    """Ping a Rust server using A2S_INFO."""
    message = b"\xFF\xFF\xFF\xFFTSource Engine Query\x00"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        try:
            s.sendto(message, (host, port))
            data, _ = s.recvfrom(4096)
            server_name = data[6:].split(b'\x00', 1)[0].decode(errors='ignore')
            return True, server_name
        except:
            return False, None

# ===== MONITORING TASK =====
async def monitor_server(channel: discord.TextChannel, host: str, port: int, interval: int):
    """Continuously ping server and send updates to the channel."""
    while True:
        up, server_name = query_rust_server(host, port)
        ts = now_iso()
        if up:
            await channel.send(f"✅ **Rust Server is UP**: `{host}:{port}`\n**Name:** {server_name}\n🕒 {ts}")
        else:
            await channel.send(f"❌ **Rust Server is DOWN**: `{host}:{port}`\n🕒 {ts}")
        await asyncio.sleep(interval)

# ===== SLASH COMMANDS =====
@tree.command(name="monitor", description="Start monitoring a Rust server")
@app_commands.describe(
    server="Rust server IP/domain and port (host:port)",
    interval="Ping interval in seconds (default 10)"
)
async def monitor(interaction: discord.Interaction, server: str, interval: int = 10):
    if ":" in server:
        host, port_str = server.split(":", 1)
        port = int(port_str)
    else:
        host = server
        port = 28015

    key = f"{interaction.channel.id}_{host}_{port}"
    if key in monitor_tasks:
        await interaction.response.send_message(f"⚠️ Already monitoring `{host}:{port}` in this channel.", ephemeral=True)
        return  # Already monitoring

    # Start the long-running task
    task = bot.loop.create_task(monitor_server(interaction.channel, host, port, interval))
    monitor_tasks[key] = task

    # Send one confirmation message
    await interaction.response.send_message(f"🎮 Started monitoring `{host}:{port}` every {interval}s.", ephemeral=False)

#==== STOP COMMAND =====
@tree.command(name="stop", description="Stop all Rust server monitoring in this channel")
async def stop(interaction: discord.Interaction):
    channel_id = interaction.channel.id
    stopped = []

    # Collect all tasks for this channel
    keys_to_remove = [key for key in monitor_tasks if key.startswith(f"{channel_id}_")]

    for key in keys_to_remove:
        task = monitor_tasks.pop(key)
        task.cancel()
        _, host, port = key.split("_")
        stopped.append(f"{host}:{port}")

    if stopped:
        await interaction.response.send_message(f"🛑 Stopped monitoring: {', '.join(stopped)}", ephemeral=False)
    else:
        await interaction.response.send_message(f"⚠️ No active monitoring tasks in this channel.", ephemeral=True)

# ===== ON READY =====

# Sync commands globally (may take up to an hour to propagate)
@bot.event
async def on_ready():
    await tree.sync()  # Registers slash commands with Discord
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("Slash commands synced!")

# For testing, sync commands to a specific guild
# Replace with your test server's guild ID
#GUILD_ID = 1234567890123456789  # Replace with your guild ID 
#@bot.event
#async def on_ready():
#    guild = discord.Object(id=GUILD_ID)

    # Delete all old guild commands
#    for cmd in tree.get_commands():
#        try:
#            await tree.delete_command(cmd.name, guild=guild)
#        except Exception as e:
#            print(f"Error deleting command {cmd.name}: {e}")

    # Sync new commands for this guild
#    await tree.sync(guild=guild)

#    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
#    print("Slash commands synced for guild!")

# ===== RUN BOT =====
bot.run(BOT_TOKEN)