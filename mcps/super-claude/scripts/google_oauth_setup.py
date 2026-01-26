#!/usr/bin/env python3
"""
Google OAuth Setup Script - Per-Service Tokens

Supports both automatic (browser) and manual (headless) authorization flows.

Usage:
    python google_oauth_setup.py status            # Show all token status
    python google_oauth_setup.py gmail             # Authorize Gmail (tries browser)
    python google_oauth_setup.py gmail --manual    # Authorize Gmail (headless/manual)
    python google_oauth_setup.py calendar --force  # Re-authorize Calendar
"""

import argparse
import sys
from pathlib import Path

CREDENTIALS_FILE = Path("/data/config/gdrive_credentials.json")
CONFIG_DIR = Path("/data/config")

# Service configurations
SERVICES = {
    "drive": {
        "token_file": "gdrive_token.json",
        "scopes": [
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/drive.file",
        ],
        "description": "Google Drive - file storage"
    },
    "gmail": {
        "token_file": "gmail_token.json",
        "scopes": [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.labels",
        ],
        "description": "Gmail - email"
    },
    "calendar": {
        "token_file": "gcal_token.json",
        "scopes": [
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
        ],
        "description": "Google Calendar - events"
    },
    "contacts": {
        "token_file": "gcontacts_token.json",
        "scopes": [
            "https://www.googleapis.com/auth/contacts.readonly",
            "https://www.googleapis.com/auth/contacts",
        ],
        "description": "Google Contacts - people"
    },
}


def check_token(service_name: str) -> dict:
    """Check status of a service token."""
    config = SERVICES[service_name]
    token_path = CONFIG_DIR / config["token_file"]
    
    result = {
        "service": service_name,
        "token_file": config["token_file"],
        "exists": token_path.exists(),
        "valid": False,
        "scopes": [],
        "expired": None
    }
    
    if not token_path.exists():
        return result
    
    try:
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(str(token_path))
        result["valid"] = creds.valid
        result["scopes"] = list(creds.scopes) if creds.scopes else []
        result["expired"] = creds.expired
        
        # Check if we have all required scopes
        required = set(config["scopes"])
        have = set(result["scopes"])
        result["has_required_scopes"] = required.issubset(have)
    except Exception as e:
        result["error"] = str(e)
    
    return result


def status_all():
    """Show status of all service tokens."""
    print("🔐 Google Service Token Status\n")
    print(f"   Credentials file: {CREDENTIALS_FILE}")
    print(f"   Exists: {'✅' if CREDENTIALS_FILE.exists() else '❌'}\n")
    
    for service_name, config in SERVICES.items():
        status = check_token(service_name)
        
        icon = "✅" if status.get("has_required_scopes") and not status.get("expired", True) else "❌"
        if status.get("has_required_scopes") and status.get("expired"):
            icon = "🔄"  # Will auto-refresh
            
        print(f"{icon} {service_name}: {config['description']}")
        print(f"   Token: {config['token_file']}")
        
        if not status["exists"]:
            print(f"   Status: Not configured")
        elif status.get("error"):
            print(f"   Status: Error - {status['error']}")
        elif not status.get("has_required_scopes"):
            print(f"   Status: Missing scopes (re-auth needed)")
        elif status["expired"]:
            print(f"   Status: Expired (will auto-refresh)")
        else:
            print(f"   Status: Ready")
        print()


def authorize_manual(service_name: str) -> int:
    """Manual OAuth flow for headless environments."""
    config = SERVICES[service_name]
    token_path = CONFIG_DIR / config["token_file"]
    scopes = config["scopes"]
    
    try:
        from google_auth_oauthlib.flow import Flow
        from google.oauth2.credentials import Credentials
    except ImportError:
        print("❌ Required libraries not installed. Run:")
        print("   pip install google-auth-oauthlib google-api-python-client")
        return 1
    
    if not CREDENTIALS_FILE.exists():
        print(f"❌ Credentials file not found: {CREDENTIALS_FILE}")
        return 1
    
    print(f"\n🔧 Manual OAuth Setup: {service_name}")
    print(f"   {config['description']}\n")
    
    # Create flow with OOB redirect
    flow = Flow.from_client_secrets_file(
        str(CREDENTIALS_FILE),
        scopes=scopes,
        redirect_uri="http://localhost:8085"
    )
    
    # Generate authorization URL
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    print("=" * 60)
    print("STEP 1: Open this URL in a browser:\n")
    print(auth_url)
    print("\n" + "=" * 60)
    print("\nSTEP 2: After authorizing, you'll be redirected to localhost")
    print("        (the page won't load - that's expected)")
    print("\nSTEP 3: Copy the FULL URL from your browser's address bar")
    print("        It will look like: http://localhost:8085/?state=...&code=...")
    print("\n" + "=" * 60)
    
    redirect_response = input("\nPaste the full redirect URL here: ").strip()
    
    if not redirect_response:
        print("❌ No URL provided")
        return 1
    
    try:
        # Extract code from URL
        flow.fetch_token(authorization_response=redirect_response)
        creds = flow.credentials
        
        # Save token
        with open(token_path, 'w') as f:
            f.write(creds.to_json())
        
        print(f"\n✅ Token saved: {token_path}")
        print(f"   Scopes: {', '.join(s.split('/')[-1] for s in creds.scopes)}")
        return 0
        
    except Exception as e:
        print(f"\n❌ Failed to exchange code: {e}")
        return 1


def authorize_service(service_name: str, force: bool = False, manual: bool = False) -> int:
    """Authorize a specific service."""
    if service_name not in SERVICES:
        print(f"❌ Unknown service: {service_name}")
        print(f"   Available: {', '.join(SERVICES.keys())}")
        return 1
    
    config = SERVICES[service_name]
    token_path = CONFIG_DIR / config["token_file"]
    scopes = config["scopes"]
    
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError:
        print("❌ Required libraries not installed. Run:")
        print("   pip install google-auth-oauthlib google-api-python-client")
        return 1
    
    if not CREDENTIALS_FILE.exists():
        print(f"❌ Credentials file not found: {CREDENTIALS_FILE}")
        return 1
    
    print(f"🔧 Setting up: {service_name} ({config['description']})")
    print(f"   Token file: {token_path}")
    
    creds = None
    
    # Check existing token (unless forcing)
    if token_path.exists() and not force:
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), scopes)
            required = set(scopes)
            have = set(creds.scopes or [])
            
            if required.issubset(have):
                if creds.expired and creds.refresh_token:
                    print("🔄 Refreshing expired token...")
                    creds.refresh(Request())
                    with open(token_path, 'w') as f:
                        f.write(creds.to_json())
                print(f"✅ Token ready: {token_path.name}")
                return 0
            else:
                print(f"⚠️  Token missing scopes, need to re-authorize")
                creds = None
        except Exception as e:
            print(f"⚠️  Existing token invalid: {e}")
            creds = None
    
    # Use manual flow if requested
    if manual:
        return authorize_manual(service_name)
    
    # Try automatic browser flow
    print("\n🌐 Starting OAuth flow (browser)...")
    
    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_FILE),
        scopes,
        redirect_uri="http://localhost:8085"
    )
    
    try:
        creds = flow.run_local_server(
            port=8085,
            prompt="consent",
            access_type="offline"
        )
    except Exception as e:
        print(f"\n⚠️  Browser flow failed: {e}")
        print("   Falling back to manual flow...\n")
        return authorize_manual(service_name)
    
    # Save token
    with open(token_path, 'w') as f:
        f.write(creds.to_json())
    
    print(f"\n✅ Token saved: {token_path}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Google OAuth Setup - Per-Service Tokens",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Services:
  drive     Google Drive (file storage)
  gmail     Gmail (email)  
  calendar  Google Calendar (events)
  
Examples:
  %(prog)s status              Show all token status
  %(prog)s gmail               Authorize Gmail (browser)
  %(prog)s gmail --manual      Authorize Gmail (headless)
  %(prog)s calendar --force    Re-authorize Calendar
"""
    )
    parser.add_argument(
        "service",
        nargs="?",
        default="status",
        help="Service to authorize (or 'status' to show all)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-authorization even if token exists"
    )
    parser.add_argument(
        "--manual",
        action="store_true",
        help="Use manual flow (for headless environments)"
    )
    args = parser.parse_args()
    
    if args.service == "status":
        status_all()
        return 0
    
    return authorize_service(args.service, args.force, args.manual)


if __name__ == "__main__":
    sys.exit(main())
