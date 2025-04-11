from Crypto.PublicKey import RSA
import json
import os
from pathlib import Path

class KeyManager:
    def __init__(self):
        self.keys_dir = Path("keys")
        self.public_keys_file = self.keys_dir / "public_keys.json"
        self.private_keys_file = self.keys_dir / "private_keys.json"
        
        # Create keys directory if it doesn't exist
        self.keys_dir.mkdir(exist_ok=True)
        
        # Load or initialize key dictionaries
        self.public_keys = self._load_keys(self.public_keys_file)
        self.private_keys = self._load_keys(self.private_keys_file)

    def _load_keys(self, file_path):
        """Load keys from JSON file or return empty dict if file doesn't exist."""
        if file_path.exists():
            with open(file_path, 'r') as f:
                return {name: bytes.fromhex(key_hex) for name, key_hex in json.load(f).items()}
        return {}

    def _save_keys(self):
        """Save both public and private keys to their respective files."""
        # Save public keys
        with open(self.public_keys_file, 'w') as f:
            json.dump({name: key.hex() for name, key in self.public_keys.items()}, f, indent=2)
        
        # Save private keys
        with open(self.private_keys_file, 'w') as f:
            json.dump({name: key.hex() for name, key in self.private_keys.items()}, f, indent=2)

    def generate_key_pair(self, name):
        """Generate a new key pair for a given name."""
        # Generate new RSA key pair
        key = RSA.generate(2048)
        
        # Export keys in the format we want to store
        private_key = key.export_key()
        public_key = key.publickey().export_key()
        
        # Store keys
        self.private_keys[name] = private_key
        self.public_keys[name] = public_key
        
        # Save to files
        self._save_keys()

    def get_public_key(self, name):
        """Get public key for a name. Returns None if not found."""
        return RSA.import_key(self.public_keys[name]) if name in self.public_keys else None

    def get_private_key(self, name):
        """Get private key for a name. Returns None if not found."""
        return RSA.import_key(self.private_keys[name]) if name in self.private_keys else None

    def list_available_signers(self):
        """Return list of names with available key pairs."""
        return list(self.public_keys.keys())

    def get_random_signer(self):
        """Return a random name from available signers."""
        import random
        signers = self.list_available_signers()
        return random.choice(signers) if signers else None 