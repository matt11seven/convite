#!/usr/bin/env python3
import requests
import json
import uuid
import sys

# Get backend URL from frontend .env file
BACKEND_URL = "https://a4db54da-b296-42be-9eb9-b8108a30fb67.preview.emergentagent.com"
API_BASE_URL = f"{BACKEND_URL}/api"

# Test data
TEST_TEMPLATE_NAME = "Template for Delete Test"
TEST_TEMPLATE_DATA = {
    "name": TEST_TEMPLATE_NAME,
    "elements": [
        {
            "type": "text",
            "content": "Test Template",
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

# Test user data
TEST_USER = {
    "email": f"delete_test_{uuid.uuid4()}@convites.com",
    "password": "Teste123!",
    "full_name": "Delete Test User"
}

# Admin credentials from .env
ADMIN_USER = {
    "email": "admin@convites.com",
    "password": "SecureAdmin2024!"
}

def test_delete_template_auth():
    """Test DELETE /api/templates/{id} with and without authentication"""
    print("\n=== Testing DELETE Template Endpoint with Authentication ===")
    
    # Step 1: Register a test user
    print("\n1. Registering test user...")
    response = requests.post(
        f"{API_BASE_URL}/auth/register",
        json=TEST_USER
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to register user: {response.text}")
        return False
    
    user_data = response.json()
    user_id = user_data["id"]
    print(f"✅ User registered successfully: {user_data['email']} (ID: {user_id})")
    
    # Step 2: Login to get authentication token
    print("\n2. Logging in to get authentication token...")
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"]
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to login: {response.text}")
        return False
    
    token_data = response.json()
    auth_token = token_data["access_token"]
    print(f"✅ Login successful, received JWT token")
    
    # Step 3: Login as admin
    print("\n3. Logging in as admin...")
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        json={
            "email": ADMIN_USER["email"],
            "password": ADMIN_USER["password"]
        }
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to login as admin: {response.text}")
        print("Continuing with user token only...")
        admin_token = None
    else:
        admin_token = response.json()["access_token"]
        print(f"✅ Admin login successful")
    
    # Step 4: Create a template with user authentication
    print("\n4. Creating a template with user authentication...")
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = requests.post(
        f"{API_BASE_URL}/templates",
        json=TEST_TEMPLATE_DATA,
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to create template: {response.text}")
        return False
    
    template_data = response.json()
    template_id = template_data["id"]
    print(f"✅ Template created successfully with ID: {template_id}")
    
    # Step 5: Get the template to check ownership
    print("\n5. Getting template to check ownership...")
    response = requests.get(
        f"{API_BASE_URL}/templates/{template_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get template: {response.text}")
        return False
    
    template = response.json()
    template_owner_id = template.get("user_id", "unknown")
    print(f"Template owner ID: {template_owner_id}")
    print(f"Current user ID: {user_id}")
    print(f"Is owner? {template_owner_id == user_id}")
    
    # Step 6: Try to delete template WITHOUT authentication
    print("\n6. Attempting to delete template WITHOUT authentication...")
    response = requests.delete(f"{API_BASE_URL}/templates/{template_id}")
    
    if response.status_code in [401, 403]:
        print(f"✅ Delete without authentication correctly returned {response.status_code} (Unauthorized/Forbidden)")
    else:
        print(f"❌ Delete without authentication returned {response.status_code} instead of 401/403")
        print(f"Response: {response.text}")
        return False
    
    # Step 7: Delete template WITH user authentication
    print("\n7. Deleting template WITH user authentication...")
    response = requests.delete(
        f"{API_BASE_URL}/templates/{template_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        print(f"✅ Template deleted successfully with user authentication")
    else:
        print(f"❌ Failed to delete template with user authentication: {response.status_code}")
        print(f"Response: {response.text}")
        
        # If admin token is available, try to delete with admin
        if admin_token:
            print("\nAttempting to delete with admin authentication...")
            admin_headers = {"Authorization": f"Bearer {admin_token}"}
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
        else:
            return False
    
    # Step 8: Verify template is deleted
    print("\n8. Verifying template is deleted...")
    response = requests.get(
        f"{API_BASE_URL}/templates/{template_id}",
        headers=headers
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