from discord.key_manager import KeyManager

def main():
    # Initialize key manager
    key_manager = KeyManager()
    
    # List of names to generate keys for
    names = [
        "Alice",
        "Bob",
        "Charlie",
        "Diana",
        "Eve"
    ]
    
    # Generate key pairs for each name
    for name in names:
        print(f"Generating key pair for {name}...")
        key_manager.generate_key_pair(name)
    
    print("\nKey pairs generated and stored for:")
    print("\n".join(f"- {name}" for name in key_manager.list_available_signers()))

if __name__ == "__main__":
    main() 