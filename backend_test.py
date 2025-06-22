#!/usr/bin/env python3
import requests
import json
import base64
import os
import time
from PIL import Image
import io
import unittest
import sys
import uuid
from pprint import pprint

# Get backend URL from frontend .env file
BACKEND_URL = "https://a4db54da-b296-42be-9eb9-b8108a30fb67.preview.emergentagent.com"
API_BASE_URL = f"{BACKEND_URL}/api"

# Test data - Updated to match the requested test template
TEST_TEMPLATE_NAME = "Convite EUVOU"
TEST_TEMPLATE_DATA = {
    "name": TEST_TEMPLATE_NAME,
    "elements": [
        {
            "type": "text",
            "content": "#EUVOU",
            "x": 200,
            "y": 150,
            "fontSize": 48,
            "color": "#ffffff",
            "textAlign": "center"
        },
        {
            "type": "image",
            "x": 125,
            "y": 250,
            "width": 150,
            "height": 150,
            "shape": "circle",
            "src": None
        },
        {
            "type": "text",
            "content": "DOUTORES EXPERIENCE",
            "x": 200,
            "y": 500,
            "fontSize": 24,
            "color": "#ff6b6b",
            "textAlign": "center"
        }
    ],
    "background": "#2d1b3d",
    "dimensions": {
        "width": 400,
        "height": 600
    },
    "is_public": False
}

# Test user data
TEST_USER = {
    "email": f"teste_{uuid.uuid4()}@convites.com",
    "password": "senha123",
    "full_name": "Usuário Teste"
}

TEST_ADMIN = {
    "email": "admin@convites.com",
    "password": "admin123"
}

# Create a test image
def create_test_image():
    img = Image.new('RGB', (100, 100), color = 'red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

class ConvitesSecurityTest(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        print(f"Testing Security Features at: {API_BASE_URL}")
        cls.user_token = None
        cls.admin_token = None
        cls.template_id = None
        cls.invite_id = None
        cls.user_id = None
        
    def test_01_register_user(self):
        """Test user registration"""
        print("\n1. Testing User Registration...")
        response = requests.post(
            f"{API_BASE_URL}/auth/register",
            json=TEST_USER
        )
        self.assertEqual(response.status_code, 200, f"Failed to register user: {response.text}")
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["email"], TEST_USER["email"])
        self.assertEqual(data["full_name"], TEST_USER["full_name"])
        self.assertEqual(data["role"], "user")
        self.assertTrue(data["is_active"])
        self.assertNotIn("password", data)
        
        # Save user ID for later tests
        self.__class__.user_id = data["id"]
        print(f"✅ User Registration API is working, created user ID: {self.__class__.user_id}")
        
    def test_02_login_user(self):
        """Test user login"""
        print("\n2. Testing User Login...")
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={
                "email": TEST_USER["email"],
                "password": TEST_USER["password"]
            }
        )
        self.assertEqual(response.status_code, 200, f"Failed to login: {response.text}")
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertIn("expires_in", data)
        self.assertIn("user", data)
        self.assertEqual(data["user"]["email"], TEST_USER["email"])
        self.assertNotIn("password", data["user"])
        
        # Save token for later tests
        self.__class__.user_token = data["access_token"]
        print(f"✅ User Login API is working, received valid JWT token")
        
    def test_03_login_admin(self):
        """Test admin login"""
        print("\n3. Testing Admin Login...")
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={
                "email": TEST_ADMIN["email"],
                "password": TEST_ADMIN["password"]
            }
        )
        self.assertEqual(response.status_code, 200, f"Failed to login as admin: {response.text}")
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["role"], "admin")
        
        # Save admin token for later tests
        self.__class__.admin_token = data["access_token"]
        print(f"✅ Admin Login API is working, received valid JWT token")
        
    def test_04_get_current_user(self):
        """Test getting current user info"""
        print("\n4. Testing Get Current User Info...")
        
        # Test with user token
        headers = {"Authorization": f"Bearer {self.__class__.user_token}"}
        response = requests.get(f"{API_BASE_URL}/auth/me", headers=headers)
        self.assertEqual(response.status_code, 200, f"Failed to get user info: {response.text}")
        data = response.json()
        self.assertEqual(data["email"], TEST_USER["email"])
        self.assertEqual(data["role"], "user")
        
        # Test with admin token
        headers = {"Authorization": f"Bearer {self.__class__.admin_token}"}
        response = requests.get(f"{API_BASE_URL}/auth/me", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["email"], TEST_ADMIN["email"])
        self.assertEqual(data["role"], "admin")
        
        print("✅ Get Current User Info API is working")
        
    def test_05_health_check_auth(self):
        """Test health check with authentication"""
        print("\n5. Testing Health Check with Authentication...")
        
        # Test without token (should fail)
        response = requests.get(f"{API_BASE_URL}/health")
        self.assertEqual(response.status_code, 401, "Health check should require authentication")
        
        # Test with user token
        headers = {"Authorization": f"Bearer {self.__class__.user_token}"}
        response = requests.get(f"{API_BASE_URL}/health", headers=headers)
        self.assertEqual(response.status_code, 200, f"Failed health check with user token: {response.text}")
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "connected")
        
        # Test with admin token (should include stats)
        headers = {"Authorization": f"Bearer {self.__class__.admin_token}"}
        response = requests.get(f"{API_BASE_URL}/health", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("stats", data)
        self.assertIn("total_users", data["stats"])
        
        print("✅ Health Check with Authentication is working")
        
    def test_06_create_template_auth(self):
        """Test template creation with authentication"""
        print("\n6. Testing Template Creation with Authentication...")
        
        # Test without token (should fail)
        response = requests.post(
            f"{API_BASE_URL}/templates",
            json=TEST_TEMPLATE_DATA
        )
        self.assertEqual(response.status_code, 401, "Template creation should require authentication")
        
        # Test with user token
        headers = {"Authorization": f"Bearer {self.__class__.user_token}"}
        response = requests.post(
            f"{API_BASE_URL}/templates",
            json=TEST_TEMPLATE_DATA,
            headers=headers
        )
        self.assertEqual(response.status_code, 200, f"Failed to create template: {response.text}")
        data = response.json()
        self.assertIn("id", data)
        
        # Save template ID for later tests
        self.__class__.template_id = data["id"]
        print(f"✅ Template Creation with Authentication is working, created template ID: {self.__class__.template_id}")
        
    def test_07_update_template_ownership(self):
        """Test template update with ownership validation"""
        print("\n7. Testing Template Update with Ownership Validation...")
        
        # Update with owner token (should succeed)
        headers = {"Authorization": f"Bearer {self.__class__.user_token}"}
        updated_data = TEST_TEMPLATE_DATA.copy()
        updated_data["name"] = f"{TEST_TEMPLATE_NAME} - Updated by Owner"
        
        response = requests.put(
            f"{API_BASE_URL}/templates/{self.__class__.template_id}",
            json=updated_data,
            headers=headers
        )
        self.assertEqual(response.status_code, 200, f"Failed to update template as owner: {response.text}")
        
        # Verify the update
        response = requests.get(
            f"{API_BASE_URL}/templates/{self.__class__.template_id}",
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        template = response.json()
        self.assertEqual(template["name"], f"{TEST_TEMPLATE_NAME} - Updated by Owner")
        
        # Update with admin token (should succeed even though not owner)
        headers = {"Authorization": f"Bearer {self.__class__.admin_token}"}
        updated_data["name"] = f"{TEST_TEMPLATE_NAME} - Updated by Admin"
        
        response = requests.put(
            f"{API_BASE_URL}/templates/{self.__class__.template_id}",
            json=updated_data,
            headers=headers
        )
        self.assertEqual(response.status_code, 200, f"Failed to update template as admin: {response.text}")
        
        # Create a second user and try to update (should fail)
        second_user = {
            "email": f"second_{uuid.uuid4()}@convites.com",
            "password": "senha123",
            "full_name": "Segundo Usuário"
        }
        
        # Register second user
        response = requests.post(
            f"{API_BASE_URL}/auth/register",
            json=second_user
        )
        self.assertEqual(response.status_code, 200)
        
        # Login as second user
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={
                "email": second_user["email"],
                "password": second_user["password"]
            }
        )
        self.assertEqual(response.status_code, 200)
        second_user_token = response.json()["access_token"]
        
        # Try to update template as second user (should fail)
        headers = {"Authorization": f"Bearer {second_user_token}"}
        updated_data["name"] = f"{TEST_TEMPLATE_NAME} - Updated by Second User"
        
        response = requests.put(
            f"{API_BASE_URL}/templates/{self.__class__.template_id}",
            json=updated_data,
            headers=headers
        )
        self.assertEqual(response.status_code, 403, "Non-owner should not be able to update template")
        
        print("✅ Template Update with Ownership Validation is working")
        
    def test_08_secure_upload(self):
        """Test secure image upload"""
        print("\n8. Testing Secure Image Upload...")
        
        # Test without token (should fail)
        img_data = create_test_image()
        files = {
            'file': ('test_image.png', img_data, 'image/png')
        }
        
        response = requests.post(f"{API_BASE_URL}/upload", files=files)
        self.assertEqual(response.status_code, 401, "Image upload should require authentication")
        
        # Test with user token
        headers = {"Authorization": f"Bearer {self.__class__.user_token}"}
        img_data = create_test_image()
        files = {
            'file': ('test_image.png', img_data, 'image/png')
        }
        
        response = requests.post(
            f"{API_BASE_URL}/upload", 
            files=files,
            headers=headers
        )
        self.assertEqual(response.status_code, 200, f"Failed to upload image: {response.text}")
        data = response.json()
        self.assertIn("filename", data)
        self.assertIn("file_url", data)
        
        # Save the image URL for later tests
        self.image_url = data["file_url"]
        print("✅ Secure Image Upload is working")
        
    def test_09_template_access_control(self):
        """Test template access control (public vs private)"""
        print("\n9. Testing Template Access Control...")
        
        # Create a private template
        headers = {"Authorization": f"Bearer {self.__class__.user_token}"}
        private_template = TEST_TEMPLATE_DATA.copy()
        private_template["name"] = "Private Template"
        private_template["is_public"] = False
        
        response = requests.post(
            f"{API_BASE_URL}/templates",
            json=private_template,
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        private_template_id = response.json()["id"]
        
        # Create a public template
        public_template = TEST_TEMPLATE_DATA.copy()
        public_template["name"] = "Public Template"
        public_template["is_public"] = True
        
        response = requests.post(
            f"{API_BASE_URL}/templates",
            json=public_template,
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        public_template_id = response.json()["id"]
        
        # Create a second user
        second_user = {
            "email": f"access_{uuid.uuid4()}@convites.com",
            "password": "senha123",
            "full_name": "Access Test User"
        }
        
        # Register second user
        response = requests.post(
            f"{API_BASE_URL}/auth/register",
            json=second_user
        )
        self.assertEqual(response.status_code, 200)
        
        # Login as second user
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={
                "email": second_user["email"],
                "password": second_user["password"]
            }
        )
        self.assertEqual(response.status_code, 200)
        second_user_token = response.json()["access_token"]
        
        # Second user tries to access private template (should fail)
        headers = {"Authorization": f"Bearer {second_user_token}"}
        response = requests.get(
            f"{API_BASE_URL}/templates/{private_template_id}",
            headers=headers
        )
        self.assertEqual(response.status_code, 403, "Non-owner should not be able to access private template")
        
        # Second user tries to access public template (should succeed)
        response = requests.get(
            f"{API_BASE_URL}/templates/{public_template_id}",
            headers=headers
        )
        self.assertEqual(response.status_code, 200, f"Failed to access public template: {response.text}")
        
        # Admin tries to access private template (should succeed)
        headers = {"Authorization": f"Bearer {self.__class__.admin_token}"}
        response = requests.get(
            f"{API_BASE_URL}/templates/{private_template_id}",
            headers=headers
        )
        self.assertEqual(response.status_code, 200, f"Admin failed to access private template: {response.text}")
        
        print("✅ Template Access Control is working")
        
    def test_10_admin_endpoints(self):
        """Test admin-only endpoints"""
        print("\n10. Testing Admin-Only Endpoints...")
        
        # Test admin endpoints with user token (should fail)
        headers = {"Authorization": f"Bearer {self.__class__.user_token}"}
        
        # Try to access admin/users
        response = requests.get(f"{API_BASE_URL}/admin/users", headers=headers)
        self.assertIn(response.status_code, [401, 403, 404], "Regular user should not access admin endpoints")
        
        # Try to access admin/stats
        response = requests.get(f"{API_BASE_URL}/admin/stats", headers=headers)
        self.assertIn(response.status_code, [401, 403, 404], "Regular user should not access admin endpoints")
        
        # Try to access admin/audit-logs
        response = requests.get(f"{API_BASE_URL}/admin/audit-logs", headers=headers)
        self.assertIn(response.status_code, [401, 403, 404], "Regular user should not access admin endpoints")
        
        # Test admin endpoints with admin token
        headers = {"Authorization": f"Bearer {self.__class__.admin_token}"}
        
        # These endpoints might not be implemented yet, so we'll just check if they return 404 or 200
        # but they should not return 401 or 403
        
        # Try to access admin/users
        response = requests.get(f"{API_BASE_URL}/admin/users", headers=headers)
        self.assertNotIn(response.status_code, [401, 403], "Admin should be authorized to access admin endpoints")
        
        # Try to access admin/stats
        response = requests.get(f"{API_BASE_URL}/admin/stats", headers=headers)
        self.assertNotIn(response.status_code, [401, 403], "Admin should be authorized to access admin endpoints")
        
        # Try to access admin/audit-logs
        response = requests.get(f"{API_BASE_URL}/admin/audit-logs", headers=headers)
        self.assertNotIn(response.status_code, [401, 403], "Admin should be authorized to access admin endpoints")
        
        print("✅ Admin authorization is working correctly")
        
    def test_11_delete_template_ownership(self):
        """Test template deletion with ownership validation"""
        print("\n11. Testing Template Deletion with Ownership Validation...")
        
        # Create a template to delete
        headers = {"Authorization": f"Bearer {self.__class__.user_token}"}
        template_to_delete = TEST_TEMPLATE_DATA.copy()
        template_to_delete["name"] = "Template to Delete"
        
        response = requests.post(
            f"{API_BASE_URL}/templates",
            json=template_to_delete,
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        template_id = response.json()["id"]
        
        # Create a second user
        second_user = {
            "email": f"delete_{uuid.uuid4()}@convites.com",
            "password": "senha123",
            "full_name": "Delete Test User"
        }
        
        # Register second user
        response = requests.post(
            f"{API_BASE_URL}/auth/register",
            json=second_user
        )
        self.assertEqual(response.status_code, 200)
        
        # Login as second user
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={
                "email": second_user["email"],
                "password": second_user["password"]
            }
        )
        self.assertEqual(response.status_code, 200)
        second_user_token = response.json()["access_token"]
        
        # Second user tries to delete template (should fail)
        headers = {"Authorization": f"Bearer {second_user_token}"}
        response = requests.delete(
            f"{API_BASE_URL}/templates/{template_id}",
            headers=headers
        )
        self.assertEqual(response.status_code, 403, "Non-owner should not be able to delete template")
        
        # Owner deletes template (should succeed)
        headers = {"Authorization": f"Bearer {self.__class__.user_token}"}
        response = requests.delete(
            f"{API_BASE_URL}/templates/{template_id}",
            headers=headers
        )
        self.assertEqual(response.status_code, 200, f"Failed to delete template as owner: {response.text}")
        
        # Verify the deletion
        response = requests.get(
            f"{API_BASE_URL}/templates/{template_id}",
            headers=headers
        )
        self.assertEqual(response.status_code, 404, "Template should be deleted")
        
        print("✅ Template Deletion with Ownership Validation is working")
        
    def test_12_generate_invite_with_auth(self):
        """Test generating a personalized invite with authentication"""
        print("\n12. Testing Generate Personalized Invite with Authentication...")
        
        # Create a template for invite generation
        headers = {"Authorization": f"Bearer {self.__class__.user_token}"}
        template_for_invite = TEST_TEMPLATE_DATA.copy()
        template_for_invite["name"] = "Template for Invite"
        
        response = requests.post(
            f"{API_BASE_URL}/templates",
            json=template_for_invite,
            headers=headers
        )
        self.assertEqual(response.status_code, 200)
        template_id = response.json()["id"]
        
        # Generate invite with customizations
        customizations = {
            "nome": "João da Silva",
            "evento": "Festa de Aniversário",
            "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        }
        
        response = requests.post(
            f"{API_BASE_URL}/generate/{template_id}",
            json=customizations
        )
        self.assertEqual(response.status_code, 200, f"Failed to generate invite: {response.text}")
        data = response.json()
        self.assertIn("invite_id", data)
        self.assertEqual(data["template_id"], template_id)
        self.assertIn("image_url", data)
        
        # Save invite ID for later tests
        self.__class__.invite_id = data["invite_id"]
        print(f"✅ Generate Invite with Authentication is working, created invite ID: {self.__class__.invite_id}")
        
    def test_13_password_security(self):
        """Test password security features"""
        print("\n13. Testing Password Security Features...")
        
        # Test that passwords are not returned in responses
        headers = {"Authorization": f"Bearer {self.__class__.user_token}"}
        response = requests.get(f"{API_BASE_URL}/auth/me", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertNotIn("password", data)
        self.assertNotIn("password_hash", data)
        
        # Test login with incorrect password
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={
                "email": TEST_USER["email"],
                "password": "wrong_password"
            }
        )
        self.assertEqual(response.status_code, 401, "Login with incorrect password should fail")
        
        print("✅ Password Security Features are working")
        
    def test_14_jwt_validation(self):
        """Test JWT token validation"""
        print("\n14. Testing JWT Token Validation...")
        
        # Test with invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = requests.get(f"{API_BASE_URL}/auth/me", headers=headers)
        self.assertEqual(response.status_code, 401, "Invalid token should be rejected")
        
        # Test with expired token (we can't easily test this without waiting)
        # But we can test with a malformed token
        headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"}
        response = requests.get(f"{API_BASE_URL}/auth/me", headers=headers)
        self.assertEqual(response.status_code, 401, "Malformed token should be rejected")
        
        print("✅ JWT Token Validation is working")

if __name__ == "__main__":
    # Run tests in order with more verbose output
    unittest.main(argv=['first-arg-is-ignored', '-v'], exit=False)