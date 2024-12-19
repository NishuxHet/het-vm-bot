from discord import app_commands
from discord.ext import commands, tasks
import discord
import docker
import time
import re
import os
import concurrent.futures

# Replace the token with a secure method to load your bot's token
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.all()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

client = docker.from_env()

SERVER_LIMIT = 12
ROLE_ID = 1318893172469796876  # Replace with the role ID for deployment
database_file = 'database.txt'

executor = concurrent.futures.ThreadPoolExecutor(max_workers=150)


def add_to_database(user, container_name, ssh_command):
    with open(database_file, 'a') as f:
        f.write(f"{user}|{container_name}|{ssh_command}\n")


def remove_from_database(ssh_command):
    if not os.path.exists(database_file):
        return
    with open(database_file, 'r') as f:
        lines = f.readlines()
    with open(database_file, 'w') as f:
        for line in lines:
            if ssh_command not in line:
                f.write(line)


def get_user_servers(user):
    if not os.path.exists(database_file):
        return []
    servers = []
    with open(database_file, 'r') as f:
        for line in f:
            if line.startswith(user):
                servers.append(line.strip())
    return servers


def count_user_servers(user):
    return len(get_user_servers(user))


def has_role_permission(role_id: int):
    async def predicate(interaction: discord.Interaction):
        role = discord.Object(id=role_id)
        if role in interaction.user.roles:
            return True
        await interaction.response.send_message(
            embed=discord.Embed(description="You do not have permission to deploy VPS.", color=0xff0000),
            ephemeral=True,
        )
        return False

    return app_commands.check(predicate)


@bot.event
async def on_ready():
    change_status.start()
    print(f'Bot is ready. Logged in as {bot.user}')
    await bot.tree.sync()


@tasks.loop(minutes=1)
async def change_status():
    await bot.change_presence(activity=discord.Game(name="with VPS(s)"))


@bot.tree.command(name="deploy-ubuntu", description="Creates a new server with Ubuntu 22.04.")
@has_role_permission(ROLE_ID)
async def deploy_ubuntu(interaction: discord.Interaction):
    await create_server_task(interaction)


@bot.tree.command(name="deploy-debian", description="Creates a new server with Debian 12.")
@has_role_permission(ROLE_ID)
async def deploy_debian(interaction: discord.Interaction):
    await create_server_task_debian(interaction)


async def create_server_task(interaction: discord.Interaction):
    await interaction.response.send_message(
        embed=discord.Embed(description="Creating server, This takes a few seconds.", color=0x00ff00)
    )
    user = str(interaction.user)
    if count_user_servers(user) >= SERVER_LIMIT:
        await interaction.followup.send(
            embed=discord.Embed(
                description="Error: Server Limit-reached\nError: Server Limit-reached```", color=0xff0000
            )
        )
        return

    image = "ubuntu:22.04"
    commands = """
    apt update && \
    apt install -y tmate && \
    tmate -F
    """

    container = client.containers.run(image, command="sh -c '{}'".format(commands), detach=True, tty=True)

    ssh_session_line = await get_ssh_session_line(container)
    if ssh_session_line:
        await interaction.user.send(
            embed=discord.Embed(
                description=(
                    f"### Successfully created VPS\n"
                    f"SSH Session Command: ```{ssh_session_line}```\n"
                    f"Powered by [conicnodes](https://discord.gg/FE8jY7DB3B)\n"
                    f"OS: Ubuntu 22.04"
                ),
                color=0x00ff00,
            )
        )
        add_to_database(user, container.name, ssh_session_line)
        await interaction.followup.send(
            embed=discord.Embed(
                description="Server created successfully. Check your DMs for details.", color=0x00ff00
            )
        )
    else:
        await interaction.followup.send(
            embed=discord.Embed(
                description="Something went wrong or the server is taking longer than expected. Contact Support.",
                color=0xff0000,
            )
        )
        container.stop()
        container.remove()


async def create_server_task_debian(interaction: discord.Interaction):
    await interaction.response.send_message(
        embed=discord.Embed(
            description="Creating server, This takes a few seconds.\n\nLog:```running apt update\nrunning apt install tmate -y\nrunning tmate -F```",
            color=0x00ff00,
        )
    )
    user = str(interaction.user)
    if count_user_servers(user) >= SERVER_LIMIT:
        await interaction.followup.send(
            embed=discord.Embed(
                description=(
                    "Error: Server Limit-reached\n"
                    "```Failed to run apt update\nFailed to run apt install tmate\nFailed to run tmate -F\n"
                    "Error: Server Limit-reached```"
                ),
                color=0xff0000,
            )
        )
        return

    image = "debian:12"
    commands = """
    apt update && \
    apt install -y tmate && \
    tmate -F
    """

    container = client.containers.run(image, command="sh -c '{}'".format(commands), detach=True, tty=True)

    ssh_session_line = await get_ssh_session_line(container)
    if ssh_session_line:
        await interaction.user.send(
            embed=discord.Embed(
                description=(
                    f"### Successfully created VPS\n"
                    f"SSH Session Command: ```{ssh_session_line}```\n"
                    f"Powered by [is-a.space](https://discord.gg/is-a-space)\n"
                    f"OS: Debian 12"
                ),
                color=0x00ff00,
            )
        )
        add_to_database(user, container.name, ssh_session_line)
        await interaction.followup.send(
            embed=discord.Embed(
                description="Server created successfully. Check your DMs for details.", color=0x00ff00
            )
        )
    else:
        await interaction.followup.send(
            embed=discord.Embed(
                description="Something went wrong or the server is taking longer than expected. Contact Support.",
                color=0xff0000,
            )
        )
        container.stop()
        container.remove()


# Start the bot
bot.run(TOKEN)