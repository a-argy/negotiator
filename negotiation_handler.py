import json
import discord
from typing import Dict, List, Optional, Any
from datetime import datetime
import io

class NegotiationState:
    def __init__(self):
        self.negotiation_started: bool = False
        self.first_bot_to_speak: Optional[str] = None
        self.bot_data: Dict[str, Dict[str, Any]] = {}  # Centralized storage for bot data
        
    def initialize_bot_data(self, bot_id: str):
        """Initialize data structure for a new bot"""
        if bot_id not in self.bot_data:
            self.bot_data[bot_id] = {
                "debrief_text": "",
                "json_dicts": [],
                "context": []
            }
        
    def add_context(self, bot_id: str, context_data: dict, source: str = "debrief"):
        """Add any type of context data for a bot"""
        self.initialize_bot_data(bot_id)
        
        # Add timestamp and source to the context
        context_entry = {
            "data": context_data,
            "timestamp": datetime.now().isoformat(),
            "source": source
        }
        
        self.bot_data[bot_id]["context"].append(context_entry)
        
    def add_json_dict(self, bot_id: str, json_dict: dict):
        """Add a JSON dictionary to the bot's list of JSON dicts"""
        self.initialize_bot_data(bot_id)
        self.bot_data[bot_id]["json_dicts"].append(json_dict)
    
    def get_json_dicts(self, bot_id: str) -> List[Dict]:
        """Get all JSON dictionaries for a bot"""
        self.initialize_bot_data(bot_id)
        return self.bot_data[bot_id]["json_dicts"]
    
    def update_debrief_text(self, bot_id: str, new_text: str):
        """Update the debrief text for a bot"""
        self.initialize_bot_data(bot_id)
        current_text = self.bot_data[bot_id]["debrief_text"]
        self.bot_data[bot_id]["debrief_text"] = current_text + "\n" + new_text if current_text else new_text
    
    def get_debrief_text(self, bot_id: str) -> str:
        """Get the complete debrief text for a bot"""
        self.initialize_bot_data(bot_id)
        return self.bot_data[bot_id]["debrief_text"]
    
    def get_bot_context(self, bot_id: str) -> List[Dict]:
        """Get all context for a bot"""
        self.initialize_bot_data(bot_id)
        return self.bot_data[bot_id]["context"]
        
    def start_negotiation(self, bot_ids: List[str]) -> str:
        """Start the negotiation with a coin flip to decide who goes first"""
        # Perform coin flip
        import random
        self.first_bot_to_speak = random.choice(bot_ids)
        self.negotiation_started = True
        return self.first_bot_to_speak  # Just return the ID, let the handler format the message

class DebriefHandler:
    def __init__(self, bot_id: str, debrief_channel_id: int):
        self.bot_id = bot_id
        self.debrief_channel_id = debrief_channel_id
        
    async def process_debrief(self, message: discord.Message) -> Optional[dict]:
        """Process any type of debrief content"""
        result = {}
        json_dicts = []
        debrief_text = ""
        
        # Add message content to debrief text if present
        if message.content:
            debrief_text += message.content + "\n"
            result["message_content"] = message.content
        
        # Process any attached files
        for attachment in message.attachments:
            try:
                content = await attachment.read()
                if attachment.filename.endswith('.json'):
                    try:
                        content_str = content.decode('utf-8')
                        json_data = json.loads(content_str)
                        json_dicts.append(json_data)
                        
                        # Add the JSON content as text to the debrief text
                        formatted_json = json.dumps(json_data, indent=2)
                        debrief_text += f"\nFile: {attachment.filename}\n{formatted_json}\n"
                        
                        # Store the file content in result
                        result[f"file_{attachment.filename}"] = json_data
                    except json.JSONDecodeError:
                        # If JSON parsing fails, store as raw text
                        content_str = content.decode('utf-8')
                        debrief_text += f"\nFile: {attachment.filename}\n{content_str}\n"
                        result[f"file_{attachment.filename}"] = content_str
                else:
                    # Store non-JSON files as text
                    content_str = content.decode('utf-8')
                    debrief_text += f"\nFile: {attachment.filename}\n{content_str}\n"
                    result[f"file_{attachment.filename}"] = content_str
            except Exception as e:
                error_msg = f"Warning: Could not process file {attachment.filename}: {str(e)}"
                debrief_text += f"\n{error_msg}\n"
                await message.channel.send(error_msg)
        
        result["json_dicts"] = json_dicts
        result["debrief_text"] = debrief_text
            
        return result if result else None

class NegotiationHandler:
    def __init__(self, negotiation_channel_id: int):
        self.negotiation_channel_id = negotiation_channel_id
        self.state = NegotiationState()
        self.debrief_handlers: Dict[str, DebriefHandler] = {}
        self.agents: Dict[str, Any] = {}  # Store references to agents
        self.conversation_history: List[Dict] = []  # Stores the negotiation conversation
        self.bot_names: Dict[str, str] = {}  # Maps bot IDs to names
        
    def register_bot(self, bot_id: str, debrief_channel_id: int, agent=None, bot_name: str = None):
        """Register a bot and its debrief channel"""
        self.debrief_handlers[bot_id] = DebriefHandler(bot_id, debrief_channel_id)
        if agent:
            self.agents[bot_id] = agent
        if bot_name:
            self.bot_names[bot_id] = bot_name
            
    def get_bot_name(self, bot_id: str) -> str:
        """Get the name of a bot"""
        return self.bot_names.get(bot_id, bot_id)
            
    def add_to_conversation(self, author_name: str, content: str):
        """Add a message to the conversation history"""
        self.conversation_history.append({
            "author": author_name,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
    def get_conversation_transcript(self) -> str:
        """Get the complete conversation transcript"""
        if not self.conversation_history:
            return "No conversation yet."
            
        transcript = ""
        for msg in self.conversation_history:
            transcript += f"{msg['author']} ({msg['timestamp']}): {msg['content']}\n\n"
        return transcript
    
    async def start_negotiation(self, channel: discord.TextChannel) -> str:
        """Start the negotiation process with a coin flip"""
        # Get list of bot IDs
        bot_ids = list(self.agents.keys())
        
        # Perform coin flip and get result
        first_bot_id = self.state.start_negotiation(bot_ids)
        
        # Format the coin flip message using the handler's get_bot_name method
        bot_name = self.get_bot_name(first_bot_id)
        coin_flip_msg = f"🎲 **COIN FLIP** 🎲\n\nA coin has been flipped! {bot_name} will speak first.\n\n{bot_name} will start the negotiation."
        
        # Send initialization prompt to first bot
        if first_bot_id in self.agents:
            first_bot_agent = self.agents[first_bot_id]
            first_bot_agent.conversation_history.append({
                "role": "user", 
                "content": "The negotiation has started. Please begin by introducing yourself and stating your position."
            })
            
        return coin_flip_msg
        
    async def handle_message(self, message: discord.Message, bot_id: str) -> Optional[str]:
        """Handle incoming messages in either debrief or negotiation channels"""
        
        # Handle debrief channel messages
        if message.channel.id == self.debrief_handlers[bot_id].debrief_channel_id:
            debrief_data = await self.debrief_handlers[bot_id].process_debrief(message)
            if debrief_data:
                self.state.add_context(bot_id, debrief_data, "debrief")
                
                # Update debrief text
                if "debrief_text" in debrief_data:
                    self.state.update_debrief_text(bot_id, debrief_data["debrief_text"])
                
                # Add JSON dictionaries to state
                if "json_dicts" in debrief_data and debrief_data["json_dicts"]:
                    for json_dict in debrief_data["json_dicts"]:
                        self.state.add_json_dict(bot_id, json_dict)

                # Get the current state
                debrief_text = self.state.get_debrief_text(bot_id)
                json_dicts = self.state.get_json_dicts(bot_id)

                # Send initial status
                initial_msg = "✅ Information received and processed."
                if json_dicts:
                    initial_msg += f"\nStored JSON dictionaries: {len(json_dicts)}"
                await message.channel.send(initial_msg)

                # Split debrief text into chunks and send
                max_chunk_size = 1900  # Discord's message limit with some buffer for formatting
                chunks = [debrief_text[i:i+max_chunk_size] for i in range(0, len(debrief_text), max_chunk_size)]
                
                for i, chunk in enumerate(chunks):
                    chunk_msg = f"Debrief Text (Part {i+1}/{len(chunks)}):\n```\n{chunk}\n```"
                    await message.channel.send(chunk_msg)
                
                return None  # Return None since we've handled sending messages directly
            
        # Handle negotiation channel messages
        elif message.channel.id == self.negotiation_channel_id:
            # If negotiation hasn't started yet, only accept !start command
            if not self.state.negotiation_started:
                return None  # Let the bot handle !start command
                
            # Add message to conversation history
            self.add_to_conversation(message.author.name, message.content)
            
            # Let the bot handle the response through its normal flow
            return None
            
        return None
        
    async def verify_response(self, bot_id: str, response: str) -> Optional[discord.File]:
        """Verify facts in a response against JSON dictionaries"""
        if bot_id not in self.agents:
            return None
            
        agent = self.agents[bot_id]
        json_dicts = self.state.get_json_dicts(bot_id)
        
        # Check if there are any JSON dicts to verify against
        if not json_dicts:
            return None
            
        # Make a verification call to the Mistral model
        verify_response = await agent.verify_facts(response, json_dicts)
        
        # If verification found references to facts in the JSON data, return a text file
        if verify_response and "references" in verify_response and verify_response["references"]:
            # Create a text file with the verification code
            verification_text = "# Fact Verification\n\n"
            for ref in verify_response["references"]:
                verification_text += f"{ref}\n\n"
                
            # Create a discord file
            file = discord.File(
                io.BytesIO(verification_text.encode('utf-8')),
                filename="verification.txt"
            )
            return file
            
        return None 