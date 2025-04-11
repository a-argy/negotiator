import os
import discord
import logging
from dotenv import load_dotenv
import PyPDF2
import io
import json
from datetime import datetime
from mistralai import Mistral
import re
from key_manager import KeyManager
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('pdf_bot')

# Load environment variables
load_dotenv()

# Constants from environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN_BOT3")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SIGNATURES_CHANNEL_ID = int(os.getenv("SIGNATURES_CHANNEL_ID", "0"))

# Validate required environment variables
if not all([DISCORD_TOKEN, MISTRAL_API_KEY, SIGNATURES_CHANNEL_ID]):
    missing_vars = []
    if not DISCORD_TOKEN:
        missing_vars.append("DISCORD_TOKEN_BOT3")
    if not MISTRAL_API_KEY:
        missing_vars.append("MISTRAL_API_KEY")
    if not SIGNATURES_CHANNEL_ID:
        missing_vars.append("SIGNATURES_CHANNEL_ID")
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

class PDFBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mistral_client = Mistral(api_key=MISTRAL_API_KEY)
        self.key_manager = KeyManager()

    async def setup_hook(self):
        """Optional method to set up the bot when it starts."""
        logger.info("Bot is starting up...")

    async def on_ready(self):
        """Called when the bot is ready to start working."""
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')

    async def extract_pdf_content(self, pdf_bytes):
        """Extract text content from PDF bytes."""
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            return "\n".join(page.extract_text() for page in pdf_reader.pages)
        except Exception as e:
            logger.error(f"Error extracting PDF content: {e}")
            return None

    def sign_data(self, data, signer_name):
        """Sign the data dictionary using the signer's private key."""
        try:
            # Get the private key for signing
            private_key = self.key_manager.get_private_key(signer_name)
            if not private_key:
                logger.error(f"No private key found for {signer_name}")
                return None

            # Convert dict to a deterministic string
            message = json.dumps(data, sort_keys=True).encode()

            # Hash and sign
            h = SHA256.new(message)
            signature = pkcs1_15.new(private_key).sign(h)

            return {
                "data": data,
                "signature": signature.hex(),
                "signer": signer_name,
                "signed_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error signing data: {e}")
            return None

    async def process_pdf_content(self, text, signer_name=None):
        """Process the PDF text using Mistral AI to extract meaningful information."""
        try:
            system_prompt = """You are an AI assistant that extracts structured information from documents into clean, valid JSON format.

            STRICT OUTPUT FORMAT RULES:
            1. Return ONLY raw JSON - no markdown, no code blocks, no explanations, and no ```json anywhere
            2. Use double quotes for all keys and string values
            3. No trailing commas
            4. No comments
            5. Boolean values must be true or false (lowercase)
            6. Null values must be null (lowercase)
            7. Numbers should not be in quotes

            CONTENT EXTRACTION RULES:
            1. Analyze the COMPLETE document text
            2. Extract key information such as BUT NOT LIMITED TO (this is where you need to use your judgement):
               - Names of parties involved
               - Dates (in ISO format: YYYY-MM-DD)
               - Monetary values (as numbers without currency symbols)
               - Property details
               - Document type
               - Any conditions or terms
               - Any other relevant information
            3. Use descriptive snake_case for all keys
            4. Structure data hierarchically
            5. Include ALL relevant information from the entire document
            """

            # Use the official chat.complete method
            response = self.mistral_client.chat.complete(
                model="mistral-large-latest",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"Extract ALL important information from this document into a clean JSON object:\n\n{text}"
                    }
                ]
            )

            # Get the response content
            content = response.choices[0].message.content

            # Extract just the JSON content between the first { and last }
            json_match = re.search(r'({.*})', content, re.DOTALL)
            if not json_match:
                logger.error(f"Could not find JSON content in response: {content}")
                return None
                
            json_content = json_match.group(1)

            # Parse the cleaned JSON
            try:
                extracted_data = json.loads(json_content)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response from Mistral: {json_content}")
                logger.error(f"JSON error: {str(e)}")
                return None

            # If no signer specified, try to use a name from the document or get a random signer
            if not signer_name:
                # Try to find a name in the extracted data
                if "sender" in extracted_data and "name" in extracted_data["sender"]:
                    signer_name = extracted_data["sender"]["name"]
                else:
                    signer_name = self.key_manager.get_random_signer()

            if not signer_name:
                logger.error("No signer available")
                return None

            # Sign the extracted data
            signed_data = self.sign_data(extracted_data, signer_name)
            if not signed_data:
                return None

            return {
                "processed_at": datetime.now().isoformat(),
                "document_text_length": len(text),
                "signed_data": signed_data
            }

        except Exception as e:
            logger.error(f"Error processing PDF content: {e}")
            logger.error(f"Original text: {text[:500]}...")  # Log first 500 chars of text for debugging
            return None

    async def on_message(self, message):
        """Handle incoming messages."""
        if message.author == self.user or message.channel.id != SIGNATURES_CHANNEL_ID:
            return

        pdf_attachments = [att for att in message.attachments if att.filename.lower().endswith('.pdf')]
        
        # Check number of PDF attachments
        if len(pdf_attachments) == 0:
            return
        elif len(pdf_attachments) > 1:
            await message.channel.send("Please send only one PDF file at a time. I'll process the first one only.")
            pdf_attachments = pdf_attachments[:1]  # Take only the first PDF

        # Check if a specific signer was mentioned
        signer_name = None
        content_lower = message.content.lower()
        for name in self.key_manager.list_available_signers():
            if name.lower() in content_lower:
                signer_name = name
                break

        attachment = pdf_attachments[0]  # We know we have exactly one PDF
        try:
            processing_msg = await message.channel.send("Processing PDF, please wait...")
            
            pdf_bytes = await attachment.read()
            text_content = await self.extract_pdf_content(pdf_bytes)
            
            if not text_content:
                await processing_msg.edit(content="Sorry, I couldn't read the PDF content.")
                return

            processed_data = await self.process_pdf_content(text_content, signer_name)
            if not processed_data:
                await processing_msg.edit(content="Sorry, I couldn't process the PDF content.")
                return

            filename = f"processed_{attachment.filename.replace('.pdf', '')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, indent=4, ensure_ascii=False)

            signer_info = f" (signed by {processed_data['signed_data']['signer']})" if processed_data.get('signed_data', {}).get('signer') else ""
            
            await processing_msg.delete()
            await message.channel.send(
                f"Here's the processed and signed data{signer_info}:",
                file=discord.File(filename)
            )
            os.remove(filename)

        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            await message.channel.send(f"Sorry, there was an error processing the PDF: {str(e)}")

def main():
    """Main function to run the bot."""
    intents = discord.Intents.default()
    intents.message_content = True
    client = PDFBot(intents=intents)
    client.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main() 