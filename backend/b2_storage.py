"""
Backblaze B2 Storage Service
Secure file upload, validation, and CDN integration
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import os
import uuid
import magic
import hashlib
import logging
from typing import Optional, Dict, Any, List
from PIL import Image
import io
from datetime import datetime
import mimetypes

# Environment variables
B2_ENDPOINT = os.environ.get('B2_ENDPOINT', 'https://s3.us-east-005.backblazeb2.com')
B2_ACCESS_KEY_ID = os.environ.get('B2_ACCESS_KEY_ID')
B2_SECRET_ACCESS_KEY = os.environ.get('B2_SECRET_ACCESS_KEY')
B2_BUCKET_NAME = os.environ.get('B2_BUCKET_NAME')
B2_REGION = os.environ.get('B2_REGION', 'us-east-005')
MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', '5242880'))  # 5MB
ALLOWED_EXTENSIONS = os.environ.get('ALLOWED_EXTENSIONS', 'jpg,jpeg,png,gif,webp').split(',')

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class B2StorageService:
    """Secure Backblaze B2 storage service with comprehensive validation."""
    
    def __init__(self):
        """Initialize B2 client."""
        if not all([B2_ACCESS_KEY_ID, B2_SECRET_ACCESS_KEY, B2_BUCKET_NAME]):
            raise ValueError("Missing required B2 credentials in environment variables")
        
        try:
            self.client = boto3.client(
                's3',
                endpoint_url=B2_ENDPOINT,
                aws_access_key_id=B2_ACCESS_KEY_ID,
                aws_secret_access_key=B2_SECRET_ACCESS_KEY,
                region_name=B2_REGION
            )
            # Test connection
            self.client.head_bucket(Bucket=B2_BUCKET_NAME)
            logger.info("✅ B2 Storage initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize B2 Storage: {e}")
            raise
    
    def validate_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Comprehensive file validation.
        Returns validation result with details.
        """
        validation_result = {
            "valid": False,
            "errors": [],
            "file_info": {}
        }
        
        try:
            # 1. File size validation
            if len(file_content) > MAX_FILE_SIZE:
                validation_result["errors"].append(
                    f"File size {len(file_content)} exceeds maximum {MAX_FILE_SIZE} bytes"
                )
                return validation_result
            
            if len(file_content) == 0:
                validation_result["errors"].append("File is empty")
                return validation_result
            
            # 2. File extension validation
            file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
            if file_ext not in ALLOWED_EXTENSIONS:
                validation_result["errors"].append(
                    f"File extension '{file_ext}' not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
                )
                return validation_result
            
            # 3. MIME type validation using mimetypes (fallback without python-magic)
            mime_type = mimetypes.guess_type(filename)[0]
            if not mime_type:
                # Try to determine from file extension
                ext_to_mime = {
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg', 
                    'png': 'image/png',
                    'gif': 'image/gif',
                    'webp': 'image/webp'
                }
                mime_type = ext_to_mime.get(file_ext, 'image/jpeg')
            
            allowed_mime_types = [
                'image/jpeg', 'image/jpg', 'image/png', 
                'image/gif', 'image/webp'
            ]
            
            if mime_type not in allowed_mime_types:
                validation_result["errors"].append(
                    f"MIME type '{mime_type}' not allowed"
                )
                return validation_result
            
            # 4. Image validation using PIL
            try:
                image = Image.open(io.BytesIO(file_content))
                image.verify()  # Verify it's a valid image
                
                # Get image info
                image = Image.open(io.BytesIO(file_content))  # Reopen after verify
                validation_result["file_info"] = {
                    "format": image.format,
                    "mode": image.mode,
                    "size": image.size,
                    "width": image.width,
                    "height": image.height,
                    "mime_type": mime_type,
                    "file_size": len(file_content)
                }
                
                # Additional image validations
                if image.width > 4096 or image.height > 4096:
                    validation_result["errors"].append(
                        f"Image dimensions {image.width}x{image.height} exceed maximum 4096x4096"
                    )
                    return validation_result
                
                if image.width < 10 or image.height < 10:
                    validation_result["errors"].append(
                        f"Image dimensions {image.width}x{image.height} below minimum 10x10"
                    )
                    return validation_result
                
            except Exception as e:
                validation_result["errors"].append(f"Invalid image file: {str(e)}")
                return validation_result
            
            # 5. Security scan for malicious content
            if self._scan_for_malicious_content(file_content):
                validation_result["errors"].append("File contains potentially malicious content")
                return validation_result
            
            validation_result["valid"] = True
            logger.info(f"✅ File validation passed: {filename}")
            
        except Exception as e:
            validation_result["errors"].append(f"Validation error: {str(e)}")
            logger.error(f"❌ File validation error: {e}")
        
        return validation_result
    
    def _scan_for_malicious_content(self, file_content: bytes) -> bool:
        """
        Basic malicious content detection.
        In production, integrate with proper antivirus/security services.
        """
        # Check for suspicious patterns
        suspicious_patterns = [
            b'<script',
            b'javascript:',
            b'eval(',
            b'<?php',
            b'<%',
            b'<iframe'
        ]
        
        content_lower = file_content.lower()
        for pattern in suspicious_patterns:
            if pattern in content_lower:
                logger.warning(f"🚨 Suspicious pattern detected: {pattern}")
                return True
        
        return False
    
    def generate_secure_filename(self, original_filename: str, user_id: str) -> str:
        """Generate secure, unique filename."""
        # Extract extension
        ext = original_filename.lower().split('.')[-1] if '.' in original_filename else 'jpg'
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        
        return f"uploads/{user_id}/{timestamp}_{unique_id}.{ext}"
    
    def upload_file(self, file_content: bytes, filename: str, user_id: str, content_type: str = None) -> Dict[str, Any]:
        """
        Upload file to B2 with comprehensive security.
        """
        try:
            # 1. Validate file
            validation = self.validate_file(file_content, filename)
            if not validation["valid"]:
                return {
                    "success": False,
                    "errors": validation["errors"]
                }
            
            # 2. Generate secure filename
            secure_filename = self.generate_secure_filename(filename, user_id)
            
            # 3. Generate file hash for integrity
            file_hash = hashlib.sha256(file_content).hexdigest()
            
            # 4. Determine content type
            if not content_type:
                content_type = validation["file_info"].get("mime_type", "image/jpeg")
            
            # 5. Prepare metadata
            metadata = {
                'original-filename': filename,
                'user-id': user_id,
                'upload-timestamp': datetime.now().isoformat(),
                'file-hash': file_hash,
                'file-size': str(len(file_content))
            }
            
            # 6. Upload to B2
            response = self.client.put_object(
                Bucket=B2_BUCKET_NAME,
                Key=secure_filename,
                Body=file_content,
                ContentType=content_type,
                Metadata=metadata,
                ACL='private'  # Keep files private
            )
            
            # 7. Generate public URL
            file_url = f"{B2_ENDPOINT}/{B2_BUCKET_NAME}/{secure_filename}"
            
            upload_result = {
                "success": True,
                "file_key": secure_filename,
                "file_url": file_url,
                "file_hash": file_hash,
                "file_info": validation["file_info"],
                "metadata": metadata,
                "etag": response.get('ETag', '').strip('"')
            }
            
            logger.info(f"✅ File uploaded successfully: {secure_filename}")
            return upload_result
            
        except ClientError as e:
            error_msg = f"B2 upload error: {e}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "errors": [error_msg]
            }
        except Exception as e:
            error_msg = f"Upload error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "errors": [error_msg]
            }
    
    def delete_file(self, file_key: str) -> bool:
        """Delete file from B2."""
        try:
            self.client.delete_object(Bucket=B2_BUCKET_NAME, Key=file_key)
            logger.info(f"✅ File deleted: {file_key}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete file {file_key}: {e}")
            return False
    
    def get_file_url(self, file_key: str, expires_in: int = 3600) -> Optional[str]:
        """Generate signed URL for private file access."""
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': B2_BUCKET_NAME, 'Key': file_key},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            logger.error(f"❌ Failed to generate URL for {file_key}: {e}")
            return None
    
    def list_user_files(self, user_id: str) -> List[Dict[str, Any]]:
        """List all files for a specific user."""
        try:
            response = self.client.list_objects_v2(
                Bucket=B2_BUCKET_NAME,
                Prefix=f"uploads/{user_id}/"
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'],
                    "url": f"{B2_ENDPOINT}/{B2_BUCKET_NAME}/{obj['Key']}"
                })
            
            return files
        except Exception as e:
            logger.error(f"❌ Failed to list files for user {user_id}: {e}")
            return []

# Initialize storage service
try:
    storage_service = B2StorageService()
except Exception as e:
    logger.error(f"❌ Failed to initialize storage service: {e}")
    storage_service = None