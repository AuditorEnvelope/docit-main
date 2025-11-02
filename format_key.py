#!/usr/bin/env python3
"""Format GitHub App private key for .env file"""

import sys

def format_pem_for_env(pem_file_path):
    """Read PEM file and format for .env"""
    try:
        with open(pem_file_path, 'r') as f:
            key_content = f.read()
        
        # Remove any trailing whitespace
        key_content = key_content.strip()
        
        # Replace actual newlines with \n
        formatted = key_content.replace('\n', '\\n')
        
        # Print the formatted line
        print(f'GITHUB_PRIVATE_KEY="{formatted}"')
        
        # Also save to a file
        with open('formatted_key.txt', 'w') as f:
            f.write(f'GITHUB_PRIVATE_KEY="{formatted}"')
        
        print("\n✅ Formatted key saved to: formatted_key.txt")
        print("✅ Copy the line above and replace GITHUB_PRIVATE_KEY in your .env")
        
    except FileNotFoundError:
        print(f"❌ Error: File '{pem_file_path}' not found!")
        print("\nUsage: python format_key.py <path-to-pem-file>")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python format_key.py <path-to-pem-file>")
        print("\nExample:")
        print("  python format_key.py ~/Downloads/lekhak-ai.2025-11-02.private-key.pem")
        sys.exit(1)
    
    pem_file = sys.argv[1]
    format_pem_for_env(pem_file)
