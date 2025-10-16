#!/usr/bin/env python3
"""
Rust Server A2S Monitor — Always Notify
Continuously pings a Rust server (via UDP A2S_INFO) and sends notifications every check.
"""

import socket
import time
from datetime import datetime, timezone
import aiohttp
import asyncio

# 🟡 REPLACE THIS with your new secure webhook URL
#DISCORD_WEBHOOK = "https://discord.com/api/webhooks/REPLACE_THIS_WITH_YOUR_NEW_WEBHOOK"

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

async def send_discord_webhook(content: str):
    if not DISCORD_WEBHOOK:
        return
    try:
        async with aiohttp.ClientSession() as session:
            data = {"content": content}
            async with session.post(DISCORD_WEBHOOK, json=data, timeout=5) as resp:
                await resp.text()
    except Exception as e:
        print(f"⚠️ Discord webhook error: {e}")

def query_rust_server(host, port, timeout=3):
    """
    Send A2S_INFO query to a Rust server.
    Returns (True, server_name) if alive, (False, None) otherwise.
    """
    message = b"\xFF\xFF\xFF\xFFTSource Engine Query\x00"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        try:
            s.sendto(message, (host, port))
            data, _ = s.recvfrom(4096)
            name_start = 6
            server_name = data[name_start:].split(b'\x00', 1)[0].decode(errors='ignore')
            return True, server_name
        except socket.timeout:
            return False, None
        except Exception:
            return False, None

async def monitor(host, port, interval, logfile):
    with open(logfile, "a", encoding="utf-8") as f:
        f.write(f"# Monitoring started {now_iso()} host={host} port={port} interval={interval}s\n")
    print(f"🎮 Monitoring Rust server {host}:{port} every {interval}s — Press Ctrl+C to stop")

    while True:
        up, server_name = query_rust_server(host, port)
        ts = now_iso()
        status = "UP" if up else "DOWN"
        line = f"{ts} {host}:{port} {status}\n"

        with open(logfile, "a", encoding="utf-8") as f:
            f.write(line)

        if up:
            print(f"{ts} 🟢 {host}:{port} is UP — {server_name}")
            msg = f"✅ **Rust Server is UP**\n`{host}:{port}`\n**Name:** {server_name}\n🕒 {ts}"
        else:
            print(f"{ts} 🔴 {host}:{port} is DOWN")
            msg = f"❌ **Rust Server is DOWN**\n`{host}:{port}`\n🕒 {ts}"

        await send_discord_webhook(msg)
        await asyncio.sleep(interval)

def parse_host_port(address: str, default_port: int = 28015):
    if ":" in address:
        host, port_str = address.split(":", 1)
        return host.strip(), int(port_str)
    return address.strip(), default_port

def main():
    print("🕹️ Rust Server Monitor — Always Notify")
    print("=======================================")
    address = input("🌐 Enter server IP or domain:port (e.g., biweekly.eu.moose.gg:28010): ").strip()
    interval_input = input("⏳ Ping interval in seconds (default 10): ").strip()
    interval = float(interval_input) if interval_input else 10.0

    host, port = parse_host_port(address)
    logfile = f"{host.replace('.', '_')}_{port}_ping.log"

    try:
        asyncio.run(monitor(host, port, interval, logfile))
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user.")

if __name__ == "__main__":
    main()