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

# Test data - Template with placeholders
TEST_TEMPLATE_WITH_PLACEHOLDERS = {
    "name": "Template com Placeholders",
    "elements": [
        {
            "type": "text",
            "content": "Olá {nome}!",
            "x": 50,
            "y": 50,
            "fontSize": 24,
            "color": "#000000",
            "textAlign": "left"
        },
        {
            "type": "text",
            "content": "Você está convidado para {evento}",
            "x": 50,
            "y": 100,
            "fontSize": 18,
            "color": "#333333",
            "textAlign": "left"
        },
        {
            "type": "image",
            "x": 150,
            "y": 150,
            "width": 200,
            "height": 200,
            "shape": "rectangle",
            "src": None  # Placeholder for image
        }
    ],
    "background": "#ffffff",
    "dimensions": {
        "width": 500,
        "height": 400
    }
}

# Test data - Template with only text
TEST_TEMPLATE_TEXT_ONLY = {
    "name": "Template Texto Simples",
    "elements": [
        {
            "type": "text",
            "content": "Texto simples sem placeholders",
            "x": 50,
            "y": 50,
            "fontSize": 24,
            "color": "#000000",
            "textAlign": "left"
        }
    ],
    "background": "#f5f5f5",
    "dimensions": {
        "width": 500,
        "height": 200
    }
}

# Test data - Template with only image
TEST_TEMPLATE_IMAGE_ONLY = {
    "name": "Template Apenas Imagem",
    "elements": [
        {
            "type": "image",
            "x": 100,
            "y": 50,
            "width": 300,
            "height": 300,
            "shape": "circle",
            "src": None  # Placeholder for image
        }
    ],
    "background": "#e0e0e0",
    "dimensions": {
        "width": 500,
        "height": 400
    }
}

# Test data - Template with multiple placeholders
TEST_TEMPLATE_MULTIPLE_PLACEHOLDERS = {
    "name": "Template Múltiplos Placeholders",
    "elements": [
        {
            "type": "text",
            "content": "Nome: {nome}",
            "x": 50,
            "y": 50,
            "fontSize": 18,
            "color": "#000000",
            "textAlign": "left"
        },
        {
            "type": "text",
            "content": "Evento: {evento}",
            "x": 50,
            "y": 80,
            "fontSize": 18,
            "color": "#000000",
            "textAlign": "left"
        },
        {
            "type": "text",
            "content": "Data: {data}",
            "x": 50,
            "y": 110,
            "fontSize": 18,
            "color": "#000000",
            "textAlign": "left"
        },
        {
            "type": "text",
            "content": "Local: {local}",
            "x": 50,
            "y": 140,
            "fontSize": 18,
            "color": "#000000",
            "textAlign": "left"
        },
        {
            "type": "image",
            "x": 300,
            "y": 50,
            "width": 150,
            "height": 150,
            "shape": "rectangle",
            "src": None  # Placeholder for image
        }
    ],
    "background": "#f0f8ff",
    "dimensions": {
        "width": 500,
        "height": 250
    }
}

# Sample base64 image for testing
SAMPLE_BASE64_IMAGE = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

class TemplateImageTest(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        print(f"Testing Template Image API at: {API_BASE_URL}")
        cls.template_ids = {}
        cls.invite_ids = {}
        cls.image_urls = {}
        
    def test_01_create_template_with_placeholders(self):
        """Test creating a template with placeholders"""
        print("\n1. Testing Template Creation with Placeholders...")
        response = requests.post(
            f"{API_BASE_URL}/templates",
            json=TEST_TEMPLATE_WITH_PLACEHOLDERS
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        self.assertIn("message", data)
        self.assertEqual(data["message"], "Template criado com sucesso")
        
        # Save template ID for later tests
        self.__class__.template_ids["placeholders"] = data["id"]
        print(f"✅ Template with placeholders created with ID: {self.__class__.template_ids['placeholders']}")
        
    def test_02_create_template_text_only(self):
        """Test creating a template with text only"""
        print("\n2. Testing Template Creation with Text Only...")
        response = requests.post(
            f"{API_BASE_URL}/templates",
            json=TEST_TEMPLATE_TEXT_ONLY
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        
        # Save template ID for later tests
        self.__class__.template_ids["text_only"] = data["id"]
        print(f"✅ Template with text only created with ID: {self.__class__.template_ids['text_only']}")
        
    def test_03_create_template_image_only(self):
        """Test creating a template with image only"""
        print("\n3. Testing Template Creation with Image Only...")
        response = requests.post(
            f"{API_BASE_URL}/templates",
            json=TEST_TEMPLATE_IMAGE_ONLY
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        
        # Save template ID for later tests
        self.__class__.template_ids["image_only"] = data["id"]
        print(f"✅ Template with image only created with ID: {self.__class__.template_ids['image_only']}")
        
    def test_04_create_template_multiple_placeholders(self):
        """Test creating a template with multiple placeholders"""
        print("\n4. Testing Template Creation with Multiple Placeholders...")
        response = requests.post(
            f"{API_BASE_URL}/templates",
            json=TEST_TEMPLATE_MULTIPLE_PLACEHOLDERS
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        
        # Save template ID for later tests
        self.__class__.template_ids["multiple_placeholders"] = data["id"]
        print(f"✅ Template with multiple placeholders created with ID: {self.__class__.template_ids['multiple_placeholders']}")
        
    def test_05_generate_invite_with_placeholders(self):
        """Test generating an invite with placeholders and image"""
        print("\n5. Testing Generate Invite with Placeholders and Image...")
        
        customizations = {
            "nome": "João Silva",
            "evento": "Casamento",
            "imagem": SAMPLE_BASE64_IMAGE
        }
        
        try:
            template_id = self.__class__.template_ids["placeholders"]
            print(f"Sending request to: {API_BASE_URL}/generate/{template_id}")
            
            response = requests.post(
                f"{API_BASE_URL}/generate/{template_id}",
                json=customizations
            )
            print(f"Response status: {response.status_code}")
            
            self.assertEqual(response.status_code, 200, f"Failed to generate invite: {response.text}")
            
            data = response.json()
            self.assertIn("id", data)
            self.assertIn("image_url", data, "Response does not include image_url")
            self.assertTrue(data["image_url"].startswith("/api/images/"), "Invalid image URL format")
            
            # Save invite ID and image URL for later tests
            self.__class__.invite_ids["placeholders"] = data["id"]
            self.__class__.image_urls["placeholders"] = data["image_url"]
            
            print(f"✅ Generate Invite API is working with placeholders")
            print(f"   - Invite ID: {self.__class__.invite_ids['placeholders']}")
            print(f"   - Image URL: {self.__class__.image_urls['placeholders']}")
        except Exception as e:
            print(f"❌ Error in generate invite test: {str(e)}")
            raise
        
    def test_06_generate_invite_text_only(self):
        """Test generating an invite with text only"""
        print("\n6. Testing Generate Invite with Text Only...")
        
        customizations = {
            "text": "Texto personalizado sem placeholders"
        }
        
        try:
            template_id = self.__class__.template_ids["text_only"]
            
            response = requests.post(
                f"{API_BASE_URL}/generate/{template_id}",
                json=customizations
            )
            
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("id", data)
            self.assertIn("image_url", data)
            
            # Save invite ID and image URL for later tests
            self.__class__.invite_ids["text_only"] = data["id"]
            self.__class__.image_urls["text_only"] = data["image_url"]
            
            print(f"✅ Generate Invite API is working with text only")
        except Exception as e:
            print(f"❌ Error in generate invite test: {str(e)}")
            raise
        
    def test_07_generate_invite_image_only(self):
        """Test generating an invite with image only"""
        print("\n7. Testing Generate Invite with Image Only...")
        
        customizations = {
            "image": SAMPLE_BASE64_IMAGE
        }
        
        try:
            template_id = self.__class__.template_ids["image_only"]
            
            response = requests.post(
                f"{API_BASE_URL}/generate/{template_id}",
                json=customizations
            )
            
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("id", data)
            self.assertIn("image_url", data)
            
            # Save invite ID and image URL for later tests
            self.__class__.invite_ids["image_only"] = data["id"]
            self.__class__.image_urls["image_only"] = data["image_url"]
            
            print(f"✅ Generate Invite API is working with image only")
        except Exception as e:
            print(f"❌ Error in generate invite test: {str(e)}")
            raise
        
    def test_08_generate_invite_multiple_placeholders(self):
        """Test generating an invite with multiple placeholders"""
        print("\n8. Testing Generate Invite with Multiple Placeholders...")
        
        customizations = {
            "nome": "Maria Oliveira",
            "evento": "Aniversário",
            "data": "15/12/2025",
            "local": "Salão de Festas",
            "imagem": SAMPLE_BASE64_IMAGE
        }
        
        try:
            template_id = self.__class__.template_ids["multiple_placeholders"]
            
            response = requests.post(
                f"{API_BASE_URL}/generate/{template_id}",
                json=customizations
            )
            
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("id", data)
            self.assertIn("image_url", data)
            
            # Save invite ID and image URL for later tests
            self.__class__.invite_ids["multiple_placeholders"] = data["id"]
            self.__class__.image_urls["multiple_placeholders"] = data["image_url"]
            
            print(f"✅ Generate Invite API is working with multiple placeholders")
        except Exception as e:
            print(f"❌ Error in generate invite test: {str(e)}")
            raise
        
    def test_09_verify_image_endpoint(self):
        """Test if the image endpoint returns the generated image"""
        print("\n9. Testing Image Endpoint...")
        
        for template_type, image_url in self.__class__.image_urls.items():
            try:
                print(f"Testing image URL for {template_type}: {image_url}")
                
                response = requests.get(f"{BACKEND_URL}{image_url}")
                
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["Content-Type"], "image/png")
                
                # Try to open the image to verify it's valid
                image = Image.open(io.BytesIO(response.content))
                self.assertIsNotNone(image)
                
                print(f"✅ Image endpoint is working for {template_type}")
            except Exception as e:
                print(f"❌ Error testing image endpoint for {template_type}: {str(e)}")
                raise
        
    def test_10_verify_persistence(self):
        """Test if the generated invite was saved with image_url"""
        print("\n10. Testing Persistence of Generated Invites...")
        
        for template_type, invite_id in self.__class__.invite_ids.items():
            try:
                print(f"Testing persistence for {template_type} invite: {invite_id}")
                
                response = requests.get(f"{API_BASE_URL}/generated/{invite_id}")
                
                self.assertEqual(response.status_code, 200)
                
                data = response.json()
                self.assertEqual(data["id"], invite_id)
                self.assertIn("image_url", data)
                self.assertEqual(data["image_url"], self.__class__.image_urls[template_type])
                
                print(f"✅ Persistence verified for {template_type}")
            except Exception as e:
                print(f"❌ Error verifying persistence for {template_type}: {str(e)}")
                raise
        
    def test_11_verify_generated_images_folder(self):
        """Test if the generated_images folder was created and contains images"""
        print("\n11. Testing Generated Images Folder...")
        
        # This test is informational only since we can't directly access the filesystem
        # through the API. We'll check if the images are accessible via the API instead.
        
        for template_type, image_url in self.__class__.image_urls.items():
            try:
                filename = image_url.split('/')[-1]
                print(f"Image file for {template_type}: {filename}")
                
                response = requests.get(f"{BACKEND_URL}{image_url}")
                self.assertEqual(response.status_code, 200)
                
                print(f"✅ Image file is accessible for {template_type}")
            except Exception as e:
                print(f"❌ Error accessing image file for {template_type}: {str(e)}")
                raise
        
        print("✅ All generated images are accessible via the API")
        
    def test_12_cleanup(self):
        """Clean up created templates"""
        print("\n12. Cleaning up created templates...")
        
        for template_type, template_id in self.__class__.template_ids.items():
            try:
                response = requests.delete(f"{API_BASE_URL}/templates/{template_id}")
                self.assertEqual(response.status_code, 200)
                print(f"✅ Deleted template for {template_type}")
            except Exception as e:
                print(f"❌ Error deleting template for {template_type}: {str(e)}")

if __name__ == "__main__":
    # Run tests in order with more verbose output
    unittest.main(argv=['first-arg-is-ignored', '-v'], exit=False)