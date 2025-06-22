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
    print(f"✅ User registered successfully: {user_data['email']}")
    
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
    
    # Step 3: Create a template to delete
    print("\n3. Creating a template to delete...")
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
    
    # Step 4: Try to delete template WITHOUT authentication
    print("\n4. Attempting to delete template WITHOUT authentication...")
    response = requests.delete(f"{API_BASE_URL}/templates/{template_id}")
    
    if response.status_code == 401:
        print(f"✅ Delete without authentication correctly returned 401 Unauthorized")
    else:
        print(f"❌ Delete without authentication returned {response.status_code} instead of 401")
        print(f"Response: {response.text}")
        return False
    
    # Step 5: Delete template WITH authentication
    print("\n5. Deleting template WITH authentication...")
    response = requests.delete(
        f"{API_BASE_URL}/templates/{template_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to delete template: {response.text}")
        return False
    
    print(f"✅ Template deleted successfully")
    
    # Step 6: Verify template is deleted
    print("\n6. Verifying template is deleted...")
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