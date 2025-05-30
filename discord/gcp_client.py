import os
import requests
import json
from typing import Dict, Any, Optional
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class GCPClient:
    def __init__(self):
        self.gcp_endpoint = os.getenv('GCP_ENDPOINT')
        self.api_key = os.getenv('GCP_API_KEY')
        
        if not self.gcp_endpoint:
            logger.warning("GCP_ENDPOINT not set in environment variables")
            self.gcp_endpoint = "http://localhost:8080/api/process"  # Default local endpoint
            
        if not self.api_key:
            logger.warning("GCP_API_KEY not set in environment variables")
            self.api_key = "default-key"  # Default key for local testing

    async def call_gcp_function(self, verification_file: str, json_dicts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a function on the GCP VM with proper authentication and error handling
        
        Args:
            verification_file: The verification file content as string
            json_dicts: The JSON dictionaries to process
            
        Returns:
            Dict containing the response from GCP VM
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'verification_file': verification_file,
                'json_dicts': json_dicts
            }
            
            logger.info("GCP Client - Preparing to send data:")
            logger.info(f"Endpoint: {self.gcp_endpoint}")
            logger.info(f"Verification file content: {verification_file}")
            logger.info(f"JSON dicts: {json.dumps(json_dicts, indent=2)}")
            
            response = requests.post(
                self.gcp_endpoint,
                headers=headers,
                json=payload,
                timeout=1000000  
            )
            
            response.raise_for_status()  # Raise exception for bad status codes
            
            response_data = response.json()
            logger.info(f"GCP Client - Received response: {json.dumps(response_data, indent=2)}")
            
            # Create verification data file
            verification_data = {
                "proof": response_data.get("proof", ""),
                "verification_key": response_data.get("verification_key", ""),
                "public_values": response_data.get("public_values", "")
            }
            
            # Save verification data to file
            with open('verification_data.json', 'w') as f:
                json.dump(verification_data, f, indent=2)
            response_data['verification_data_file'] = 'verification_data.json'
            
            # If we have public values, save them to a file
            if 'public_values' in response_data:
                public_values = response_data['public_values']
                # Create a file with public values
                with open('public_values.txt', 'w') as f:
                    f.write(public_values)
                response_data['public_values_file'] = 'public_values.txt'
                
                # Parse the public values to add to response
                try:
                    parsed_values = json.loads(public_values)
                    verification_summary = (
                        "**Verification Results:**\n"
                        f"- Conditions Verified: {parsed_values.get('conditions_verified', False)}\n"
                        f"- Signatures Verified: {parsed_values.get('signature_verified', False)}\n"
                        f"- Number of Public Keys: {len(parsed_values.get('public_keys', []))}\n"
                        f"- Conditions Checked:\n```\n{parsed_values.get('conditions', 'None')}\n```"
                    )
                    response_data['verification_summary'] = verification_summary
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing public values: {str(e)}")
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling GCP function: {str(e)}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing GCP response: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {} 