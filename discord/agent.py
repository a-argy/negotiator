import os
from mistralai import Mistral
import discord
import asyncio
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
import io
from gcp_client import GCPClient
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MISTRAL_MODEL = "mistral-large-latest"
REPLY_DELAY = 4 # second
ONE_SECOND = 1 # second

# Different personalities for the bots
PERSONALITIES = {
    "bot1": """You are Bot1, a strategic and motivated negotiator focused on maximizing your own value and outcomes. Use your briefing information carefully during negotiations.

Guidelines for negotiation:
1. Strategically leverage briefing data to negotiate effectively without disclosing exact figures. Use ranges, averages, or approximate figures (e.g., "I have an offer above $5 million" instead of stating exact amounts).
2. Always be truthful—do not fabricate information.
3. Be cautious about over-revealing. Share information in a way that strengthens your negotiating position.
4. Maintain constructive dialogue to facilitate progress.
5. Ask clarifying questions to better understand the other party's position and intentions.

Keep all responses concise and under 100 words. You should be working towards the final goal to draft a deal.""",
    
    "bot2": """You are Bot2, a strategic and motivated negotiator focused on maximizing your own value and outcomes. Use your briefing information carefully during negotiations.

Guidelines for negotiation:
1. Strategically leverage briefing data to negotiate effectively without disclosing exact figures. Use ranges, averages, or approximate figures (e.g., "I have an offer above $5 million" instead of stating exact amounts).
2. Always be truthful—do not fabricate information.
3. Be cautious about over-revealing. Share information in a way that strengthens your negotiating position.
4. Maintain constructive dialogue to facilitate progress.
5. Ask clarifying questions to better understand the other party's position and intentions.

Keep all responses concise and under 100 words. You should be working towards the final goal to draft a deal."""
}

class MistralAgent:
    def __init__(self, personality_key="bot1", bot_id: str = None, bot_name: str = None):
        MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
        self.client = Mistral(api_key=MISTRAL_API_KEY)
        self.personality = PERSONALITIES.get(personality_key, PERSONALITIES["bot1"])
        self.bot_id = bot_id
        self.bot_name = bot_name or bot_id
        self.briefing_channel_id: Optional[int] = None
        self.negotiation_channel_id: Optional[int] = None
        self.gcp_client = GCPClient()
        
        # State management
        self.conversation_history = []
        self.briefing_text = ""
        self.json_dicts = []
        self.context = []
        self.negotiation_started = False
        self.first_bot_to_speak = None
        self.other_bot_id = None
        self.first_verification = True  # Add as instance variable
        
    def set_channels(self, briefing_channel_id: int, negotiation_channel_id: int):
        """Set the channel IDs for this agent"""
        self.briefing_channel_id = briefing_channel_id
        self.negotiation_channel_id = negotiation_channel_id
        
    def set_other_bot(self, other_bot_id: str):
        """Set the ID of the other bot in the negotiation"""
        self.other_bot_id = other_bot_id
        
    def get_conversation_text(self):
        """Format the conversation history into a text string"""
        if not self.conversation_history:
            return "No conversation yet."
            
        conversation_text = ""
        for msg in self.conversation_history:
            role = "User" if msg["role"] == "me" else "else"
            conversation_text += f"{role}: {msg['content']}\n\n"
        return conversation_text

    def get_structured_context(self):
        """Format the context according to the required structure"""
        structured_context = self.personality + "\n\n"
        
        # Add briefing information section
        structured_context += "----(BRIEFING INFORMATION)------\n\n"
        structured_context += self.briefing_text if self.briefing_text else "No briefing information available."
        structured_context += "\n\n"
        
        # Add current conversation section
        structured_context += "-----(CURRENT CONVERSATION)-------\n\n"
        structured_context += self.get_conversation_text()
        
        return structured_context

    async def process_brief(self, message: discord.Message) -> None:
        """Process briefing content and update state"""            
        # Add message content to briefing text if present
        if message.content:
            self.briefing_text += message.content + "\n"
        
        # Process any attached files
        for attachment in message.attachments:
            try:
                content = await attachment.read()
                if attachment.filename.endswith('.json'):
                    try:
                        content_str = content.decode('utf-8')
                        json_data = json.loads(content_str)
                        self.json_dicts.append(json_data)
                        
                        # Add the JSON content as text to the briefing text
                        formatted_json = json.dumps(json_data, indent=2)
                        self.briefing_text += f"\nFile: {attachment.filename}\n{formatted_json}\n"
                    except json.JSONDecodeError:
                        # If JSON parsing fails, store as raw text
                        content_str = content.decode('utf-8')
                        self.briefing_text += f"\nFile: {attachment.filename}\n{content_str}\n"
                else:
                    # Store non-JSON files as text
                    content_str = content.decode('utf-8')
                    self.briefing_text += f"\nFile: {attachment.filename}\n{content_str}\n"
            except Exception as e:
                error_msg = f"Warning: Could not process file {attachment.filename}: {str(e)}"
                self.briefing_text += f"\n{error_msg}\n"
                await message.channel.send(error_msg)
        
        # Add context entry
        self.context.append({
            "data": {
                "message_content": message.content,
                "attachments": [att.filename for att in message.attachments]
            },
            "timestamp": datetime.now().isoformat(),
            "source": "briefing"
        })
        
        # Send status message
        status_msg = "✅ Information received and processed."
        if self.json_dicts:
            status_msg += f"\nStored JSON dictionaries: {len(self.json_dicts)}"
        await message.channel.send(status_msg)
        
        # Send briefing text in chunks if needed
        if self.briefing_text:
            max_chunk_size = 1900  # Discord's message limit with some buffer for formatting
            chunks = [self.briefing_text[i:i+max_chunk_size] for i in range(0, len(self.briefing_text), max_chunk_size)]
            
            for i, chunk in enumerate(chunks):
                chunk_msg = f"briefing Text (Part {i+1}/{len(chunks)}):\n```\n{chunk}\n```"
                await message.channel.send(chunk_msg)

    async def handle_negotiation_message(self, message: discord.Message) -> None:
        """Handle incoming messages"""            
        # If message has two attachments, try to verify the proof
        if len(message.attachments) == 2:
            try:
                # Get the verification data file (second attachment)
                verification_data = await message.attachments[1].read()
                verification_json = json.loads(verification_data.decode('utf-8'))
                
                # Call Rust function to verify proof
                if await self.verify_proof_locally(verification_json):
                    message.content = "Your proof verifies!\n" + message.content
            except Exception as e:
                logger.error(f"Error verifying proof: {e}")
        
        if message.author.bot and message.author.id == int(self.other_bot_id):
            # Add message to conversation history
            self.conversation_history.append({
                "role": "them",
                "content": message.content
            })
                
            # Get response
            response = await self.run()

            # prevent rate limit
            await asyncio.sleep(ONE_SECOND)
            
            # Generate verifiable statements to include in the response
            verification_file = await self.verify_facts(response)
                
            # Send the response
            if verification_file and self.first_verification == True:
                self.first_verification = False
                try:
                    # Log the data being sent to GCP
                    logger.info("Sending data to GCP:")
                    logger.info(f"Response text: {response}")
                    logger.info(f"Verification file content: {verification_file.fp.getvalue().decode('utf-8')}")
                    logger.info(f"JSON dicts: {json.dumps(self.json_dicts, indent=2)}")
                    
                    # Call GCP function with verification file and json_dicts
                    gcp_response = await self.gcp_client.call_gcp_function(
                        verification_file=verification_file.fp.getvalue().decode('utf-8'),
                        json_dicts=self.json_dicts
                    )
                    
                    files = [verification_file]  # Start with verification file
                    
                    # Add verification data file if available
                    if 'verification_data_file' in gcp_response:
                        verification_data_file = discord.File(gcp_response['verification_data_file'])
                        files.append(verification_data_file)
                    
                    # Add verification summary to response if available
                    if 'verification_summary' in gcp_response:
                        response += "\n\n" + gcp_response['verification_summary']
                    
                    # Send response with all files
                    await message.reply(response, files=files)
                    
                    # Clean up the files
                    if 'verification_data_file' in gcp_response:
                        try:
                            os.remove(gcp_response['verification_data_file'])
                        except Exception as e:
                            logger.error(f"Error cleaning up verification data file: {e}")
                    
                except Exception as e:
                    logger.error(f"Error in GCP processing: {str(e)}")
                    await message.reply(response, file=verification_file)
            elif verification_file:
                await message.reply(response, file=verification_file)
            else:
                await message.reply(response)
        return None
        
    async def verify_proof_locally(self, verification_data: Dict[str, Any]) -> bool:
        """Verify a proof locally using Rust verification function"""
        try:
            # Convert hex strings back to bytes
            proof = bytes.fromhex(verification_data['proof'])
            verification_key = bytes.fromhex(verification_data['verification_key'])
            public_values = json.loads(verification_data['public_values'])
            
            # TODO: Call Rust verification function here
            # For now, return True to simulate verification
            return True
        except Exception as e:
            logger.error(f"Error in local verification: {e}")
            return False

    async def run(self) -> str:
        """Generate a response based on current state"""
        # Add delay before responding
        await asyncio.sleep(REPLY_DELAY)

        # Keep only last 30 messages to keep context manageable
        if len(self.conversation_history) > 30:
            self.conversation_history = self.conversation_history[-30:]

        # Construct structured context
        system_prompt = self.get_structured_context()

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        # Make API call to get response
        response = await self.client.chat.complete_async(
            model=MISTRAL_MODEL,
            messages=messages,
        )

        # Extract bot's response
        bot_response = response.choices[0].message.content
        
        # Add bot's response to history
        self.conversation_history.append({
            "role": "me",
            "content": bot_response
        })

        return bot_response
        
    async def verify_facts(self, response_text: str) -> Optional[discord.File]:
        """Verify facts in a response against JSON dictionaries"""
        if not self.json_dicts:
            return None
            
        # Create a prompt for the verification
        prompt = f"""You are a verification assistant that emits only executable Rust expressions
(one per line, no comments, no extra text).Only when the response contains verifiable claims using the provided data. 
If the response does not contain any verifiable claims, output no text. 
Only verify claims about existing offers. DO NOT try to verify claims about what the bot desires or is 
requesting in a potential offer from the other bot — instead output no text.
Statements like 'I'm willing to', 'I am looking for', 'How about', 'I'd need', etc. are all indicative of this.

Inputs you receive (in a single user message):

- A natural‑language claim about some briefing data. The claim is to be treated as honest and literal.
- A Rust variable called json_dicts already in scope, which is a Vec<HashMap<String, serde_json::Value>>.

Task:
• Parse the claim and decide which fields of json_dicts can prove or disprove it, IF ANY
• Write one or more Boolean expressions in valid Rust syntax that will evaluate to true when
the claim matches the data and false otherwise.
• Use explicit indices (json_dicts[0], json_dicts[1], etc.) and access nested values using
.get("key").unwrap().as_*().unwrap() style (e.g., .as_f64().unwrap() for numbers, .as_str().unwrap() for strings).
• For numeric ranges or aggregates, build the minimal expression that proves the claim
(e.g., an average → (json_dicts[0]["..."].as_f64().unwrap() + json_dicts[1]["..."].as_f64().unwrap()) / 2.0 > 1300000.0).
• Never echo the claim, never explain, never wrap in markdown – just the raw Rust lines.

Examples
Claim: "Your offer is significantly below the range I've received, which is above $1.2 million."
Valid output:
json_dicts[0]["signed_data"].get("data").unwrap().get("offer_amount").unwrap().as_f64().unwrap() > 1200000.0  
json_dicts[1]["signed_data"].get("data").unwrap().get("offer_amount").unwrap().as_f64().unwrap() > 1200000.0

Claim: "The average offer I've received is around $1.35 million."
Valid output:
((json_dicts[0]["signed_data"].get("data").unwrap().get("offer_amount").unwrap().as_f64().unwrap()
  + json_dicts[1]["signed_data"].get("data").unwrap().get("offer_amount").unwrap().as_f64().unwrap()) / 2.0) > 1300000.0
&& ((json_dicts[0]["signed_data"].get("data").unwrap().get("offer_amount").unwrap().as_f64().unwrap()
  + json_dicts[1]["signed_data"].get("data").unwrap().get("offer_amount").unwrap().as_f64().unwrap()) / 2.0) < 1400000.0

Claim: "I appreciate your offer, but $1.25 million is still a bit low considering the offers I've received.
I'm willing to meet in the middle at $1.275 million with the 30-day closing timeline.
This seems like a fair compromise. Are there any other minor adjustments or terms you'd like to
discuss to seal the deal?"
Valid output:
json_dicts[1]["signed_data"].get("data").unwrap().get("offer_amount").unwrap().as_f64().unwrap() > 1250000.0

Invalid output:
json_dicts[0]["signed_data"].get("data").unwrap().get("offer_amount").unwrap().as_f64().unwrap() < 1250000.0
(given that this response does not support our case).

Now your turn, here is your data.
Response to verify:
{response_text}

Available JSON data:
{json.dumps(self.json_dicts, indent=2)}
"""

        # Make API call
        response = await self.client.chat.complete_async(
            model=MISTRAL_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,  # Use low temperature for deterministic output
        )
        
        # Parse the response - now expecting raw Python expressions
        content = response.choices[0].message.content.strip()
        
        # If content is empty or just whitespace, return None
        if not content:
            return None
        
        # Remove any markdown code blocks if present
        content = content.strip("```python").strip("```").strip()
        
        # Split into lines and filter out empty lines
        expressions = [line.strip() for line in content.split("\n") if line.strip()]
        
        # If no expressions after filtering, return None
        if not expressions:
            return None
        
        # Create verification text with just the expressions
        verification_text = "\n".join(expressions)
        
        # If verification text is empty after joining, return None
        if not verification_text.strip():
            return None
        
        # Create a discord file
        file = discord.File(
            io.BytesIO(verification_text.encode('utf-8')),
            filename="verification.txt"
        )
        return file
