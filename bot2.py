import os
import discord
import logging
import random
import asyncio

from discord.ext import commands
from dotenv import load_dotenv
from agent import MistralAgent

PREFIX = "?"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("discord")

# Load the environment variables
load_dotenv()

# Channel IDs
BRIEFING_CHANNEL_ID = int(os.getenv("BRIEFING_CHANNEL_OMEGA_ID"))
NEGOTIATION_CHANNEL_ID = int(os.getenv("NEGOTIATION_CHANNEL_ID"))

# Bot IDs
BOT_ID = os.getenv("SECOND_BOT_ID")
OTHER_BOT_ID = os.getenv("FIRST_BOT_ID")

# Create the bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Initialize agent as None
agent = None

@bot.event
async def on_ready():
    logger.info(f"{bot.user} has connected to Discord!")
    # Create Mistral agent now that bot is ready
    global agent
    agent = MistralAgent(
        personality_key="bot2",
        bot_id=BOT_ID,
        bot_name="Negotiator Bot 2"
    )
    # Set up the agent
    agent.set_channels(BRIEFING_CHANNEL_ID, NEGOTIATION_CHANNEL_ID)
    agent.set_other_bot(OTHER_BOT_ID)

@bot.event
async def on_message(message: discord.Message):
    # Don't delete this line! It's necessary for the bot to process commands.
    await bot.process_commands(message)

    # Ignore messages from self
    if message.author.id == bot.user.id or message.content.startswith("!") or message.content.startswith("?"):
        return
    
    # Handle messages in briefing channel
    if message.channel.id == BRIEFING_CHANNEL_ID:            
        await agent.process_brief(message)
        return
    
    # Handle messages in negotiation channel
    if message.channel.id == NEGOTIATION_CHANNEL_ID:
        if message.author.bot and message.author.id == int(agent.other_bot_id):
            await agent.handle_negotiation_message(message)
            return

@bot.command(name="start")
async def start_negotiation(ctx):
    """Start the negotiation with Bot2 initiating the conversation"""
    if ctx.channel.id != NEGOTIATION_CHANNEL_ID:
        await ctx.send("This command can only be used in the negotiation channel.")
        return
        
    if agent.negotiation_started:
        await ctx.send("Negotiation has already started.")
        return
        
    # Mark negotiation as started
    agent.negotiation_started = True
    
    # Send welcome message
    welcome_msg = "Hi, bot1! I'm bot2. Let's work out a deal!"
    
    # Add welcome message to conversation history
    agent.conversation_history.append({
        "role": "me",
        "content": welcome_msg
    })

    await ctx.send(welcome_msg)

@bot.command(name="transcript")
async def show_transcript(ctx):
    """Show the conversation transcript"""
    transcript = agent.get_conversation_text()
    
    # Split transcript into chunks if too long
    max_length = 1900  # Discord message limit
    
    if len(transcript) <= max_length:
        await ctx.send(f"```\n{transcript}\n```")
    else:
        chunks = [transcript[i:i+max_length] for i in range(0, len(transcript), max_length)]
        for i, chunk in enumerate(chunks):
            await ctx.send(f"```\nTranscript (Part {i+1}/{len(chunks)}):\n{chunk}\n```")

# Start the bot
bot.run(os.getenv("DISCORD_TOKEN_BOT2")) 