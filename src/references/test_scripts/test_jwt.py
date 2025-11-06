# # # # # import os
# # # # # import jwt
# # # # # import time
# # # # # import requests
# # # # # from pathlib import Path
# # # # # from dotenv import load_dotenv

# # # # # # Load environment
# # # # # load_dotenv(Path(__file__).parent.parent / ".env")

# # # # # def verify_jwt():
# # # # #     """Verify JWT generation and validate it with GitHub"""
# # # # #     print("="*80)
# # # # #     print("JWT VERIFICATION")
# # # # #     print("="*80)
    
# # # # #     # Get private key
# # # # #     private_key = os.getenv("WRITER_PRIVATE_KEY") or ""
# # # # #     if not private_key:
# # # # #         print("❌ WRITER_PRIVATE_KEY not found in environment")
# # # # #         return

# # # # #     # App details
# # # # #     app_id = "2229202"  # From your logs
# # # # #     print(f"🔑 Using App ID: {app_id}")
    
# # # # #     # Generate JWT
# # # # #     try:
# # # # #         payload = {
# # # # #             "iat": int(time.time()) - 60,  # Issued 60 seconds ago
# # # # #             "exp": int(time.time()) + 600,  # Expires in 10 minutes
# # # # #             "iss": app_id
# # # # #         }
        
# # # # #         # Generate JWT
# # # # #         encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")
# # # # #         print(f"✅ JWT generated successfully")
# # # # #         print(f"JWT: {encoded_jwt[:50]}...")
        
# # # # #         # Verify JWT can be decoded
# # # # #         try:
# # # # #             decoded = jwt.decode(encoded_jwt, private_key, algorithms=["RS256"], options={"verify_signature": False})
# # # # #             print("✅ JWT decoded successfully:")
# # # # #             print(f"   Issuer (iss): {decoded.get('iss')}")
# # # # #             print(f"   Issued At (iat): {decoded.get('iat')}")
# # # # #             print(f"   Expires (exp): {decoded.get('exp')}")
# # # # #         except Exception as e:
# # # # #             print(f"❌ JWT verification failed: {str(e)}")
# # # # #             return
            
# # # # #         # Test JWT with GitHub API
# # # # #         print("\n🔍 Testing JWT with GitHub API...")
# # # # #         headers = {
# # # # #             "Authorization": f"Bearer {encoded_jwt}",
# # # # #             "Accept": "application/vnd.github.v3+json"
# # # # #         }
        
# # # # #         # Get app info
# # # # #         response = requests.get(
# # # # #             "https://api.github.com/app",
# # # # #             headers=headers
# # # # #         )
        
# # # # #         if response.status_code == 200:
# # # # #             app_info = response.json()
# # # # #             print("✅ JWT is valid and accepted by GitHub!")
# # # # #             print(f"App Name: {app_info.get('name')}")
# # # # #             print(f"App URL: {app_info.get('html_url')}")
# # # # #         else:
# # # # #             print(f"❌ GitHub API returned {response.status_code}:")
# # # # #             print(response.text)
            
# # # # #     except Exception as e:
# # # # #         print(f"❌ Error: {str(e)}")

# # # # # if __name__ == "__main__":
# # # # #     verify_jwt()


# # # # import os
# # # # import jwt
# # # # import time
# # # # import requests
# # # # from pathlib import Path
# # # # from dotenv import load_dotenv

# # # # # Load environment
# # # # load_dotenv(Path(__file__).parent.parent / ".env")

# # # # def get_installation_token():
# # # #     """Get installation token for the GitHub App"""
# # # #     print("="*80)
# # # #     print("GITHUB INSTALLATION TOKEN TEST")
# # # #     print("="*80)
    
# # # #     # Get private key
# # # #     private_key = os.getenv("WRITER_PRIVATE_KEY") or ""
# # # #     if not private_key:
# # # #         print("❌ WRITER_PRIVATE_KEY not found in environment")
# # # #         return

# # # #     app_id = "2229202"  # From your logs
# # # #     installation_id = "93180288"  # Current installation ID
    
# # # #     # Generate JWT
# # # #     try:
# # # #         payload = {
# # # #             "iat": int(time.time()) - 60,
# # # #             "exp": int(time.time()) + 600,
# # # #             "iss": app_id
# # # #         }
# # # #         jwt_token = jwt.encode(payload, private_key, algorithm="RS256")
# # # #     except Exception as e:
# # # #         print(f"❌ JWT generation failed: {str(e)}")
# # # #         return

# # # #     # Get installation token
# # # #     headers = {
# # # #         "Authorization": f"Bearer {jwt_token}",
# # # #         "Accept": "application/vnd.github.v3+json"
# # # #     }

# # # #     try:
# # # #         print(f"🔑 Getting installation token for installation ID: {installation_id}...")
# # # #         response = requests.post(
# # # #             f"https://api.github.com/app/installations/{installation_id}/access_tokens",
# # # #             headers=headers
# # # #         )
        
# # # #         if response.status_code == 201:
# # # #             token_data = response.json()
# # # #             print("✅ Successfully obtained installation token!")
# # # #             print(f"Token: {token_data.get('token')[:10]}...")
# # # #             print(f"Expires at: {token_data.get('expires_at')}")
# # # #             print(f"Permissions: {token_data.get('permissions')}")
# # # #             return token_data.get('token')
# # # #         else:
# # # #             print(f"❌ Failed to get installation token. Status: {response.status_code}")
# # # #             print("Response:", response.text)
# # # #             return None

# # # #     except Exception as e:
# # # #         print(f"❌ Error getting installation token: {str(e)}")
# # # #         return None

# # # # def list_installations(jwt_token):
# # # #     """List all installations for the app"""
# # # #     print("\n" + "="*80)
# # # #     print("LISTING APP INSTALLATIONS")
# # # #     print("="*80)
    
# # # #     headers = {
# # # #         "Authorization": f"Bearer {jwt_token}",
# # # #         "Accept": "application/vnd.github.v3+json"
# # # #     }

# # # #     try:
# # # #         response = requests.get(
# # # #             "https://api.github.com/app/installations",
# # # #             headers=headers
# # # #         )
        
# # # #         if response.status_code == 200:
# # # #             installations = response.json()
# # # #             print(f"Found {len(installations)} installations:")
# # # #             for inst in installations:
# # # #                 print(f"\n🔹 ID: {inst.get('id')}")
# # # #                 print(f"   Account: {inst.get('account', {}).get('login')}")
# # # #                 print(f"   Type: {inst.get('account', {}).get('type')}")
# # # #                 print(f"   Permissions: {inst.get('permissions')}")
# # # #                 print(f"   Repositories URL: {inst.get('repositories_url')}")
# # # #         else:
# # # #             print(f"❌ Failed to list installations: {response.status_code}")
# # # #             print("Response:", response.text)

# # # #     except Exception as e:
# # # #         print(f"❌ Error listing installations: {str(e)}")

# # # # if __name__ == "__main__":
# # # #     # First get a valid JWT
# # # #     private_key = os.getenv("WRITER_PRIVATE_KEY")
# # # #     app_id = "2229202"
# # # #     jwt_token = jwt.encode(
# # # #         {
# # # #             "iat": int(time.time()) - 60,
# # # #             "exp": int(time.time()) + 600,
# # # #             "iss": app_id
# # # #         },
# # # #         private_key,
# # # #         algorithm="RS256"
# # # #     )
    
# # # #     # List all installations to verify the correct installation ID
# # # #     list_installations(jwt_token)
    
# # # #     # Then try to get an installation token
# # # #     get_installation_token()


# # # import os
# # # import requests
# # # from pathlib import Path
# # # from dotenv import load_dotenv

# # # # Load environment
# # # load_dotenv(Path(__file__).parent.parent / ".env")

# # # def test_repository_access(token):
# # #     """Test repository access with the installation token"""
# # #     print("\n" + "="*80)
# # #     print("TESTING REPOSITORY ACCESS")
# # #     print("="*80)
    
# # #     repo = "jai-mahakal-poc/pustak-docbook-jai-mahakal-poc"
# # #     headers = {
# # #         "Authorization": f"token {token}",
# # #         "Accept": "application/vnd.github.v3+json"
# # #     }

# # #     # Test 1: Get repository info
# # #     print(f"\n🔍 Testing access to {repo}...")
# # #     response = requests.get(
# # #         f"https://api.github.com/repos/{repo}",
# # #         headers=headers
# # #     )
    
# # #     if response.status_code == 200:
# # #         repo_info = response.json()
# # #         print("✅ Successfully accessed repository!")
# # #         print(f"Repository: {repo_info.get('full_name')}")
# # #         print(f"Private: {repo_info.get('private')}")
# # #         print(f"Permissions: {repo_info.get('permissions')}")
        
# # #         # Test 2: List repository contents
# # #         print("\n📂 Listing repository contents...")
# # #         response = requests.get(
# # #             f"https://api.github.com/repos/{repo}/contents/",
# # #             headers=headers
# # #         )
        
# # #         if response.status_code == 200:
# # #             contents = response.json()
# # #             print("✅ Repository contents:")
# # #             for item in contents:
# # #                 print(f"- {item.get('name')} ({item.get('type')})")
# # #         else:
# # #             print(f"❌ Failed to list contents: {response.status_code}")
# # #             print(response.text)
            
# # #     else:
# # #         print(f"❌ Failed to access repository: {response.status_code}")
# # #         print(response.text)

# # # def test_write_access(token):
# # #     """Test write access to the repository"""
# # #     print("\n" + "="*80)
# # #     print("TESTING WRITE ACCESS")
# # #     print("="*80)
    
# # #     repo = "jai-mahakal-poc/pustak-docbook-jai-mahakal-poc"
# # #     headers = {
# # #         "Authorization": f"token {token}",
# # #         "Accept": "application/vnd.github.v3+json"
# # #     }
    
# # #     # Test 3: Create a test file
# # #     test_file = {
# # #         "message": "Test write access from API",
# # #         "content": "VGhpcyBpcyBhIHRlc3QgZmlsZSBjcmVhdGVkIGJ5IHRoZSBhcGkK",  # "This is a test file created by the api"
# # #         "branch": "main"
# # #     }
    
# # #     print("\n✏️  Testing file creation...")
# # #     response = requests.put(
# # #         f"https://api.github.com/repos/{repo}/contents/TEST_WRITE_ACCESS.txt",
# # #         headers=headers,
# # #         json=test_file
# # #     )
    
# # #     if response.status_code == 201:
# # #         print("✅ Successfully created test file!")
# # #         print(f"Commit SHA: {response.json().get('content', {}).get('sha')}")
# # #     else:
# # #         print(f"❌ Failed to create file: {response.status_code}")
# # #         print(response.text)

# # # if __name__ == "__main__":
# # #     # Get the installation token (you can replace this with the token from the previous output)
# # #     token = "ghs_U91GR8..."  # Replace with your token
    
# # #     # Test repository access
# # #     test_repository_access(token)
    
# # #     # Test write access
# # #     test_write_access(token)

# # import os
# # import jwt
# # import time
# # import requests
# # from pathlib import Path
# # from dotenv import load_dotenv

# # # Load environment
# # load_dotenv(Path(__file__).parent.parent / ".env")

# # def get_installation_token():
# #     """Get installation token for the GitHub App"""
# #     print("="*80)
# #     print("GITHUB INSTALLATION TOKEN TEST")
# #     print("="*80)
    
# #     # Get private key
# #     private_key = os.getenv("WRITER_PRIVATE_KEY") or ""
# #     if not private_key:
# #         print("❌ WRITER_PRIVATE_KEY not found in environment")
# #         return

# #     app_id = "2229202"  # From your logs
# #     installation_id = "93180288"  # Current installation ID
    
# #     # Generate JWT
# #     try:
# #         payload = {
# #             "iat": int(time.time()) - 60,
# #             "exp": int(time.time()) + 600,
# #             "iss": app_id
# #         }
# #         jwt_token = jwt.encode(payload, private_key, algorithm="RS256")
# #     except Exception as e:
# #         print(f"❌ JWT generation failed: {str(e)}")
# #         return

# #     # Get installation token
# #     headers = {
# #         "Authorization": f"Bearer {jwt_token}",
# #         "Accept": "application/vnd.github.v3+json"
# #     }

# #     try:
# #         print(f"🔑 Getting installation token for installation ID: {installation_id}...")
# #         response = requests.post(
# #             f"https://api.github.com/app/installations/{installation_id}/access_tokens",
# #             headers=headers
# #         )
        
# #         if response.status_code == 201:
# #             token_data = response.json()
# #             print("✅ Successfully obtained installation token!")
# #             print(f"Token: {token_data.get('token')}")  # This is the important part
# #             print(f"Expires at: {token_data.get('expires_at')}")
# #             print(f"Permissions: {token_data.get('permissions')}")
# #             return token_data.get('token')
# #         else:
# #             print(f"❌ Failed to get installation token. Status: {response.status_code}")
# #             print("Response:", response.text)
# #             return None

# #     except Exception as e:
# #         print(f"❌ Error getting installation token: {str(e)}")
# #         return None

# # if __name__ == "__main__":
# #     token = get_installation_token()
# #     if token:
# #         print("\nUse this token in your test script:")
# #         print(f"token = \"{token}\"")


# import os
# import requests
# from pathlib import Path
# from dotenv import load_dotenv

# # Load environment
# load_dotenv(Path(__file__).parent.parent / ".env")

# def test_repository_access(token):
#     """Test repository access with the installation token"""
#     print("\n" + "="*80)
#     print("TESTING REPOSITORY ACCESS")
#     print("="*80)
    
#     repo = "jai-mahakal-poc/pustak-docbook-jai-mahakal-poc"
#     headers = {
#         "Authorization": f"token {token}",
#         "Accept": "application/vnd.github.v3+json"
#     }

#     # Test 1: Get repository info
#     print(f"\n🔍 Testing access to {repo}...")
#     response = requests.get(
#         f"https://api.github.com/repos/{repo}",
#         headers=headers
#     )
    
#     if response.status_code == 200:
#         repo_info = response.json()
#         print("✅ Successfully accessed repository!")
#         print(f"Repository: {repo_info.get('full_name')}")
#         print(f"Private: {repo_info.get('private')}")
#         print(f"Permissions: {repo_info.get('permissions')}")
#     else:
#         print(f"❌ Failed to access repository: {response.status_code}")
#         print(response.text)

# if __name__ == "__main__":
#     # Replace this with the token you just obtained
#     token = "ghs_wGin03derWzfEh5UyvLquu1WPOuAMD1Fm9sN"
    
#     # Test repository access
#     test_repository_access(token)



import jwt
import time
from pathlib import Path

# Configuration
KEY_PATH = "pustak-publisher-ai.private-key.pem"  # Relative path since we're in src/
APP_ID = "2229202"  # Your writer app ID

def test_jwt():
    try:
        print("🔍 Testing JWT generation...")
        
        # 1. Load the private key
        private_key = Path(KEY_PATH).read_text().strip()
        print("✅ Private key loaded successfully")
        
        # 2. Print key info (first and last 50 chars)
        print(f"\n🔑 Key info:")
        print(f"First 50 chars: {private_key[:50]}")
        print(f"Last 50 chars: {private_key[-50:]}")
        print(f"Key length: {len(private_key)} characters")
        
        # 3. Generate JWT
        payload = {
            'iat': int(time.time()) - 60,  # Issued 1 min ago
            'exp': int(time.time()) + 600,  # Expires in 10 mins
            'iss': APP_ID
        }
        
        token = jwt.encode(payload, private_key, algorithm='RS256')
        print("\n✅ JWT generated successfully!")
        print(f"Token (first 50 chars): {token[:50]}...")
        
        # 4. Try to decode (without verification)
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            print("\n🔍 Decoded JWT (without verification):")
            print(f"Issuer (iss): {decoded.get('iss')}")
            print(f"Issued At (iat): {decoded.get('iat')}")
            print(f"Expires (exp): {decoded.get('exp')}")
        except Exception as e:
            print(f"\n⚠️  Could not decode JWT: {e}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ JWT generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_jwt()