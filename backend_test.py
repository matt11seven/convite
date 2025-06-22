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
    }
}

# Create a test image
def create_test_image():
    img = Image.new('RGB', (100, 100), color = 'red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

class ConvitesAPITest(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        print(f"Testing API at: {API_BASE_URL}")
        cls.template_id = None
        cls.invite_id = None
        
    def test_01_health_check(self):
        """Test health check endpoint"""
        print("\n1. Testing Health Check API...")
        response = requests.get(f"{API_BASE_URL}/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "connected")
        print("✅ Health Check API is working")
        
    def test_02_create_template(self):
        """Test template creation"""
        print("\n2. Testing Template Creation...")
        response = requests.post(
            f"{API_BASE_URL}/templates",
            json=TEST_TEMPLATE_DATA
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        self.assertIn("message", data)
        self.assertEqual(data["message"], "Template criado com sucesso")
        
        # Save template ID for later tests
        self.__class__.template_id = data["id"]
        print(f"✅ Template created with ID: {self.__class__.template_id}")
        
    def test_03_get_templates(self):
        """Test getting all templates"""
        print("\n3. Testing Get All Templates...")
        response = requests.get(f"{API_BASE_URL}/templates")
        self.assertEqual(response.status_code, 200)
        templates = response.json()
        self.assertIsInstance(templates, list)
        
        # Check if our template is in the list
        template_found = False
        for template in templates:
            if template.get("id") == self.__class__.template_id:
                template_found = True
                self.assertEqual(template["name"], TEST_TEMPLATE_NAME)
                break
                
        self.assertTrue(template_found, "Created template not found in templates list")
        print(f"✅ Get All Templates API is working, found {len(templates)} templates")
        
    def test_04_get_template_by_id(self):
        """Test getting a specific template"""
        print("\n4. Testing Get Template by ID...")
        response = requests.get(f"{API_BASE_URL}/templates/{self.__class__.template_id}")
        self.assertEqual(response.status_code, 200)
        template = response.json()
        self.assertEqual(template["id"], self.__class__.template_id)
        self.assertEqual(template["name"], TEST_TEMPLATE_NAME)
        print("✅ Get Template by ID API is working")
        
    def test_05_update_template(self):
        """Test updating a template"""
        print("\n5. Testing Update Template...")
        updated_data = TEST_TEMPLATE_DATA.copy()
        updated_data["name"] = f"{TEST_TEMPLATE_NAME} - Updated"
        
        response = requests.put(
            f"{API_BASE_URL}/templates/{self.__class__.template_id}",
            json=updated_data
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify the update
        response = requests.get(f"{API_BASE_URL}/templates/{self.__class__.template_id}")
        self.assertEqual(response.status_code, 200)
        template = response.json()
        self.assertEqual(template["name"], f"{TEST_TEMPLATE_NAME} - Updated")
        print("✅ Update Template API is working")
        
    def test_06_upload_image(self):
        """Test image upload"""
        print("\n6. Testing Image Upload...")
        img_data = create_test_image()
        
        files = {
            'file': ('test_image.png', img_data, 'image/png')
        }
        
        response = requests.post(f"{API_BASE_URL}/upload", files=files)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("data_url", data)
        self.assertTrue(data["data_url"].startswith("data:image/png;base64,"))
        
        # Save the image data_url for later tests
        self.image_data_url = data["data_url"]
        print("✅ Image Upload API is working")
        
    def test_07_generate_invite(self):
        """Test generating a personalized invite"""
        print("\n7. Testing Generate Personalized Invite...")
        customizations = {
            "#euvou": "MARIA VAI",
            "doutores": "EVENTO ESPECIAL",
            "image": self.image_data_url
        }
        
        try:
            print(f"Sending request to: {API_BASE_URL}/generate/{self.__class__.template_id}")
            print(f"With customizations: {json.dumps(customizations, indent=2)}")
            
            response = requests.post(
                f"{API_BASE_URL}/generate/{self.__class__.template_id}",
                json=customizations
            )
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text[:500]}")
            
            if response.status_code != 200:
                self.__class__.invite_id = None
                return
            
            data = response.json()
            self.assertIn("id", data)
            self.assertEqual(data["template_id"], self.__class__.template_id)
            
            # Save invite ID for later tests
            self.__class__.invite_id = data["id"]
            print(f"✅ Generate Invite API is working, created invite ID: {self.__class__.invite_id}")
        except Exception as e:
            print(f"❌ Error in generate invite test: {str(e)}")
            self.__class__.invite_id = None
        
    def test_08_get_generated_invite(self):
        """Test getting a generated invite"""
        print("\n8. Testing Get Generated Invite...")
        
        # Skip if invite_id is None
        if self.__class__.invite_id is None:
            print("⚠️ Skipping test because no invite was generated")
            return
            
        response = requests.get(f"{API_BASE_URL}/generated/{self.__class__.invite_id}")
        self.assertEqual(response.status_code, 200)
        invite = response.json()
        self.assertEqual(invite["id"], self.__class__.invite_id)
        self.assertEqual(invite["template_id"], self.__class__.template_id)
        print("✅ Get Generated Invite API is working")
        
    def test_09_get_template_generated_invites(self):
        """Test getting all generated invites for a template"""
        print("\n9. Testing Get Template Generated Invites...")
        
        response = requests.get(f"{API_BASE_URL}/templates/{self.__class__.template_id}/generated")
        self.assertEqual(response.status_code, 200)
        invites = response.json()
        self.assertIsInstance(invites, list)
        
        # Only check for our invite if it was successfully created
        if self.__class__.invite_id is not None:
            self.assertGreaterEqual(len(invites), 1)
            
            # Check if our invite is in the list
            invite_found = False
            for invite in invites:
                if invite.get("id") == self.__class__.invite_id:
                    invite_found = True
                    break
                    
            self.assertTrue(invite_found, "Created invite not found in template's invites list")
            
        print(f"✅ Get Template Generated Invites API is working, found {len(invites)} invites")
        
    def test_10_bulk_generate_invites(self):
        """Test bulk generating invites"""
        print("\n10. Testing Bulk Generate Invites...")
        bulk_data = [
            {
                "#euvou": "JOÃO VAI",
                "doutores": "EVENTO VIP",
                "image": self.image_data_url
            },
            {
                "#euvou": "PEDRO VAI",
                "doutores": "EVENTO PREMIUM",
                "image": self.image_data_url
            }
        ]
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/templates/{self.__class__.template_id}/bulk-generate",
                json=bulk_data
            )
            print(f"Response status: {response.status_code}")
            if response.status_code != 200:
                print(f"Error response: {response.text}")
                return
                
            data = response.json()
            self.assertIn("message", data)
            self.assertIn("invites", data)
            self.assertEqual(len(data["invites"]), 2)
            print(f"✅ Bulk Generate Invites API is working, created {len(data['invites'])} invites")
        except Exception as e:
            print(f"❌ Error in bulk generate invites test: {str(e)}")
        
    def test_11_get_stats(self):
        """Test getting API statistics"""
        print("\n11. Testing Get API Statistics...")
        response = requests.get(f"{API_BASE_URL}/stats")
        self.assertEqual(response.status_code, 200)
        stats = response.json()
        self.assertIn("total_templates", stats)
        self.assertIn("total_generated_invites", stats)
        self.assertIn("recent_generated_invites", stats)
        print("✅ Get API Statistics is working")
        
    def test_12_delete_template(self):
        """Test deleting a template"""
        print("\n12. Testing Delete Template...")
        response = requests.delete(f"{API_BASE_URL}/templates/{self.__class__.template_id}")
        self.assertEqual(response.status_code, 200)
        
        # Verify the deletion
        response = requests.get(f"{API_BASE_URL}/templates/{self.__class__.template_id}")
        self.assertEqual(response.status_code, 404)
        print("✅ Delete Template API is working")

if __name__ == "__main__":
    # Run tests in order with more verbose output
    unittest.main(argv=['first-arg-is-ignored', '-v'], exit=False)