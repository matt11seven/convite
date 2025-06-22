#!/usr/bin/env python3
import requests
import json
import uuid
import sys

# Get backend URL from frontend .env file
BACKEND_URL = "https://a4db54da-b296-42be-9eb9-b8108a30fb67.preview.emergentagent.com"
API_BASE_URL = f"{BACKEND_URL}/api"

# Admin credentials from .env
ADMIN_USER = {
    "email": "admin@convites.com",
    "password": "SecureAdmin2024!"
}

def test_delete_template_auth():
    """Test DELETE /api/templates/{id} with authentication"""
    print("\n=== Testing DELETE Template Endpoint with Authentication ===")
    
    # Step 1: Login as admin
    print("\n1. Logging in as admin...")
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={
            "email": ADMIN_USER["email"],
            "password": ADMIN_USER["password"]
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to login as admin: {response.text}")
        return False
    
    admin_token = response.json()["access_token"]
    print(f"✅ Admin login successful")
    
    # Step 2: Create a template with admin authentication
    print("\n2. Creating a template with admin authentication...")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    template_data = {
        "name": "Admin Test Template",
        "elements": [
            {
                "type": "text",
                "content": "Admin Test",
                "x": 100,
                "y": 100,
                "fontSize": 24,
                "color": "#000000",
                "textAlign": "center"
            }
        ],
        "background": "#ffffff",
        "dimensions": {
            "width": 400,
            "height": 600
        },
        "is_public": False
    }
    
    response = requests.post(
        f"{API_BASE_URL}/templates",
        json=template_data,
        headers=admin_headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to create template: {response.text}")
        return False
    
    template_id = response.json()["id"]
    print(f"✅ Template created successfully with ID: {template_id}")
    
    # Step 3: Try to delete template WITHOUT authentication
    print("\n3. Attempting to delete template WITHOUT authentication...")
    response = requests.delete(f"{API_BASE_URL}/templates/{template_id}")
    
    if response.status_code in [401, 403]:
        print(f"✅ Delete without authentication correctly returned {response.status_code} (Unauthorized/Forbidden)")
    else:
        print(f"❌ Delete without authentication returned {response.status_code} instead of 401/403")
        print(f"Response: {response.text}")
        return False
    
    # Step 4: Delete template WITH admin authentication
    print("\n4. Deleting template WITH admin authentication...")
    response = requests.delete(
        f"{API_BASE_URL}/templates/{template_id}",
        headers=admin_headers
    )
    
    if response.status_code == 200:
        print(f"✅ Template deleted successfully with admin authentication")
    else:
        print(f"❌ Failed to delete template with admin authentication: {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    # Step 5: Verify template is deleted
    print("\n5. Verifying template is deleted...")
    response = requests.get(
        f"{API_BASE_URL}/templates/{template_id}",
        headers=admin_headers
    )
    
    if response.status_code == 404:
        print(f"✅ Template not found (404) - confirms deletion was successful")
    else:
        print(f"❌ Template still exists with status code {response.status_code}")
        return False
    
    print("\n=== DELETE Template Endpoint Test Complete ===")
    return True

if __name__ == "__main__":
    success = test_delete_template_auth()
    if success:
        print("\n✅ All tests passed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)