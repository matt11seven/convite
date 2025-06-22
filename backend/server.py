from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from pymongo import MongoClient
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Any, Optional
import os
import uuid
import base64
import json
from datetime import datetime, timedelta
import io
from PIL import Image

# Import our security modules
from auth import (
    create_user, authenticate_user, get_current_user, get_current_active_user, 
    require_admin, create_access_token, UserCreate, UserLogin, UserResponse, 
    TokenResponse, init_admin_user, create_session, cleanup_expired_sessions
)
from b2_storage import storage_service
from security import SecurityMiddleware, security_monitor, sanitize_input, validate_email

# Environment variables
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')
JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '24'))

# MongoDB setup
client = MongoClient(MONGO_URL)
db = client.convites_secure_db
templates_collection = db.templates
generated_collection = db.generated_invites
audit_logs_collection = db.audit_logs

app = FastAPI(
    title="Sistema de Convites Personalizados - Enterprise Edition",
    description="Sistema seguro de criação e personalização de convites com autenticação JWT e armazenamento B2",
    version="2.0.0"
)

# Add security middleware
app.add_middleware(SecurityMiddleware)

# CORS configuration (restrictive for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict to specific domains in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Security setup
security = HTTPBearer()

# Enhanced Pydantic models
class TemplateElement(BaseModel):
    type: str  # 'text' or 'image'
    x: int
    y: int
    content: Optional[str] = None  # For text elements
    src: Optional[str] = None  # For image elements (B2 URL)
    width: Optional[int] = None
    height: Optional[int] = None
    fontSize: Optional[int] = None
    fontFamily: Optional[str] = None
    color: Optional[str] = None
    textAlign: Optional[str] = None
    shape: Optional[str] = None  # 'circle' or 'rectangle' for images

class TemplateDimensions(BaseModel):
    width: int
    height: int

class Template(BaseModel):
    name: str
    elements: List[TemplateElement]
    background: str  # Color hex or B2 URL
    dimensions: TemplateDimensions
    is_public: Optional[bool] = False

class GenerateRequest(BaseModel):
    template_id: str
    customizations: Dict[str, Any]  # Key-value pairs for customization

class AuditLog(BaseModel):
    user_id: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Dict[str, Any]
    ip_address: str
    user_agent: str
    timestamp: datetime

# Utility functions
def log_audit_event(user_id: str, action: str, resource_type: str, request: Request, 
                   resource_id: str = None, details: Dict[str, Any] = None):
    """Log audit event for security monitoring."""
    try:
        audit_log = {
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("User-Agent", ""),
            "timestamp": datetime.utcnow()
        }
        audit_logs_collection.insert_one(audit_log)
    except Exception as e:
        print(f"Failed to log audit event: {e}")

def get_user_templates_filter(user: Dict[str, Any]) -> Dict[str, Any]:
    """Get MongoDB filter for user's accessible templates."""
    if user.get("role") == "admin":
        return {}  # Admin can see all templates
    else:
        return {"$or": [{"user_id": user["id"]}, {"is_public": True}]}

# Initialize admin user and cleanup
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    try:
        init_admin_user()
        cleanup_expired_sessions()
        print("✅ Application initialized successfully")
    except Exception as e:
        print(f"❌ Startup error: {e}")

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Sistema de Convites Personalizados - Enterprise Edition",
        "version": "2.0.0",
        "features": ["JWT Authentication", "B2 Storage", "Rate Limiting", "Audit Logging"],
        "security": "Enterprise Grade"
    }

# Health check with enhanced monitoring
@app.get("/api/health")
async def health_check(current_user: Dict[str, Any] = Depends(get_current_active_user)):
    """Enhanced health check with user authentication."""
    try:
        # Test database connection
        db.list_collection_names()
        
        # Test B2 storage
        storage_status = "healthy" if storage_service else "unavailable"
        
        # Get basic stats for admins
        stats = {}
        if current_user.get("role") == "admin":
            stats = {
                "total_users": db.users.count_documents({}),
                "total_templates": templates_collection.count_documents({}),
                "total_generated": generated_collection.count_documents({}),
                "storage_status": storage_status
            }
        
        return {
            "status": "healthy",
            "database": "connected",
            "storage": storage_status,
            "timestamp": datetime.utcnow(),
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

# Authentication endpoints
@app.post("/api/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate, request: Request):
    """Register a new user with comprehensive validation."""
    try:
        # Sanitize inputs
        user_data.email = sanitize_input(user_data.email.lower())
        user_data.full_name = sanitize_input(user_data.full_name)
        
        # Validate email format
        if not validate_email(user_data.email):
            raise HTTPException(status_code=400, detail="Invalid email format")
        
        # Create user
        user = create_user(user_data)
        
        # Log audit event
        log_audit_event(
            user_id=user["id"],
            action="user_registered",
            resource_type="user",
            request=request,
            details={"email": user["email"]}
        )
        
        return UserResponse(**user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(user_credentials: UserLogin, request: Request):
    """Authenticate user and return JWT token."""
    try:
        # Sanitize email
        email = sanitize_input(user_credentials.email.lower())
        
        # Authenticate user
        user = authenticate_user(email, user_credentials.password)
        if not user:
            # Log failed login
            security_monitor.log_failed_login(
                ip=request.client.host if request.client else "unknown",
                email=email
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Create access token
        token_data = {"sub": user["id"], "email": user["email"], "role": user["role"]}
        access_token = create_access_token(token_data)
        
        # Create session
        session_id = create_session(
            user_id=user["id"],
            token=access_token,
            ip_address=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("User-Agent", "")
        )
        
        # Log successful login
        log_audit_event(
            user_id=user["id"],
            action="user_login",
            resource_type="session",
            request=request,
            resource_id=session_id
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=JWT_EXPIRATION_HOURS * 3600,
            user=UserResponse(**user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_active_user)):
    """Get current user information."""
    return UserResponse(**current_user)

# Template CRUD endpoints
@app.get("/api/templates")
async def get_templates():
    """Get all templates"""
    try:
        templates = list(templates_collection.find({}, {"_id": 0}))
        return templates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar templates: {str(e)}")

@app.get("/api/templates/{template_id}")
async def get_template(template_id: str):
    """Get a specific template by ID"""
    try:
        template = templates_collection.find_one({"id": template_id}, {"_id": 0})
        if not template:
            raise HTTPException(status_code=404, detail="Template não encontrado")
        return template
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar template: {str(e)}")

@app.post("/api/templates")
async def create_template(template: Template):
    """Create a new template"""
    try:
        template_id = str(uuid.uuid4())
        template_data = {
            "id": template_id,
            "name": template.name,
            "elements": [element.dict() for element in template.elements],
            "background": template.background,
            "dimensions": template.dimensions.dict(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        templates_collection.insert_one(template_data)
        
        return {
            "id": template_id,
            "message": "Template criado com sucesso",
            "api_endpoint": f"/api/generate/{template_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar template: {str(e)}")

@app.put("/api/templates/{template_id}")
async def update_template(template_id: str, template: Template):
    """Update an existing template"""
    try:
        template_data = {
            "name": template.name,
            "elements": [element.dict() for element in template.elements],
            "background": template.background,
            "dimensions": template.dimensions.dict(),
            "updated_at": datetime.utcnow()
        }
        
        result = templates_collection.update_one(
            {"id": template_id}, 
            {"$set": template_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Template não encontrado")
        
        return {"message": "Template atualizado com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar template: {str(e)}")

@app.delete("/api/templates/{template_id}")
async def delete_template(template_id: str):
    """Delete a template"""
    try:
        result = templates_collection.delete_one({"id": template_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Template não encontrado")
        
        return {"message": "Template excluído com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao excluir template: {str(e)}")

# Image upload endpoint
@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    """Upload an image and return base64 encoded data"""
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Arquivo deve ser uma imagem")
        
        # Read file content
        content = await file.read()
        
        # Convert to base64
        base64_data = base64.b64encode(content).decode('utf-8')
        data_url = f"data:{file.content_type};base64,{base64_data}"
        
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(content),
            "data_url": data_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao fazer upload: {str(e)}")

@app.post("/api/generate/{template_id}")
async def generate_invite(template_id: str, customizations: Dict[str, Any]):
    """Generate a personalized invite based on template and customizations"""
    try:
        # Validate template_id format (basic security)
        if not template_id or len(template_id) < 10:
            raise HTTPException(status_code=400, detail="ID de template inválido")
        
        # Sanitize customizations to prevent injection
        sanitized_customizations = {}
        for key, value in customizations.items():
            # Only allow alphanumeric keys and reasonable string values
            if isinstance(key, str) and key.replace('_', '').replace('-', '').isalnum():
                if isinstance(value, str) and len(value) <= 1000:  # Limit string length
                    sanitized_customizations[key] = value
                elif isinstance(value, (int, float)) and -1000000 <= value <= 1000000:
                    sanitized_customizations[key] = value
        
        # Get template
        template = templates_collection.find_one({"id": template_id}, {"_id": 0})
        if not template:
            raise HTTPException(status_code=404, detail="Template não encontrado")
        
        # Create a copy of the template with customizations applied
        personalized_elements = []
        
        for element in template['elements']:
            new_element = element.copy()
            element_index = template['elements'].index(element)
            
            # Apply customizations based on element type and content
            if element['type'] == 'text':
                # Check for placeholder patterns like {nome}, {evento}
                content = element.get('content', '')
                original_content = content
                
                # Replace placeholders
                for key, value in sanitized_customizations.items():
                    placeholder = f"{{{key}}}"
                    if placeholder in content:
                        content = content.replace(placeholder, str(value))
                
                # Check for common text patterns
                content_lower = content.lower()
                for key, value in sanitized_customizations.items():
                    if key.lower() in ['nome', 'name'] and ('nome' in content_lower or 'name' in content_lower):
                        new_element['content'] = str(value)
                        break
                    elif key.lower() in ['evento', 'event'] and ('evento' in content_lower or 'event' in content_lower):
                        new_element['content'] = str(value)
                        break
                    elif key.lower() in ['data', 'date'] and ('data' in content_lower or 'date' in content_lower):
                        new_element['content'] = str(value)
                        break
                    elif key.lower() in ['local', 'location'] and ('local' in content_lower or 'location' in content_lower):
                        new_element['content'] = str(value)
                        break
                    elif key == f'texto_{element_index + 1}':
                        new_element['content'] = str(value)
                        break
                
                # Update content if it was modified via placeholders
                if content != original_content:
                    new_element['content'] = content
            
            elif element['type'] == 'image':
                # Check if there's a customization for this image element
                for key, value in sanitized_customizations.items():
                    if key == f'imagem_{element_index + 1}' or key.lower() in ['imagem', 'image', 'photo', 'foto']:
                        if isinstance(value, str):
                            # If value is a base64 image, use it
                            if value.startswith('data:image'):
                                new_element['src'] = value
                            # If value is a URL, convert to base64 for processing
                            elif value.startswith('http'):
                                try:
                                    import requests
                                    print(f"Downloading image from URL: {value}")
                                    
                                    # Add headers to mimic a browser request
                                    headers = {
                                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                                        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                                        'Accept-Language': 'en-US,en;q=0.9',
                                        'Accept-Encoding': 'gzip, deflate, br',
                                        'Connection': 'keep-alive',
                                    }
                                    
                                    response = requests.get(value, headers=headers, timeout=10, verify=False)
                                    print(f"Response status: {response.status_code}")
                                    print(f"Response headers: {response.headers}")
                                    
                                    if response.status_code == 200:
                                        import base64
                                        img_data = base64.b64encode(response.content).decode('utf-8')
                                        # Detect content type from response headers or URL
                                        content_type = response.headers.get('content-type', 'image/jpeg')
                                        if not content_type.startswith('image/'):
                                            # Fallback based on URL extension
                                            if value.lower().endswith('.png'):
                                                content_type = 'image/png'
                                            elif value.lower().endswith('.gif'):
                                                content_type = 'image/gif'
                                            elif value.lower().endswith('.webp'):
                                                content_type = 'image/webp'
                                            else:
                                                content_type = 'image/jpeg'
                                        
                                        data_url = f"data:{content_type};base64,{img_data}"
                                        new_element['src'] = data_url
                                        print(f"Successfully converted image to base64, size: {len(img_data)} chars")
                                    else:
                                        print(f"Failed to download image: HTTP {response.status_code}")
                                except Exception as e:
                                    print(f"Error downloading image from URL: {e}")
                                    import traceback
                                    traceback.print_exc()
                        break
            
            personalized_elements.append(new_element)
        
        # Generate the image
        image_url = await generate_invite_image(template, personalized_elements, template_id)
        
        # Generate unique ID for this personalized invite
        invite_id = str(uuid.uuid4())
        
        # Save the generated invite (with all data for internal use)
        generated_invite = {
            "id": invite_id,
            "template_id": template_id,
            "template_name": template['name'],
            "elements": personalized_elements,
            "background": template['background'],
            "dimensions": template['dimensions'],
            "customizations": sanitized_customizations,
            "image_url": image_url,
            "created_at": datetime.utcnow()
        }
        
        generated_collection.insert_one(generated_invite)
        
        # Construct full HTTPS URL for the image
        # In production, this should be your actual domain
        request_url = "https://a4db54da-b296-42be-9eb9-b8108a30fb67.preview.emergentagent.com"
        full_image_url = f"{request_url}{image_url}"
        
        # Return only essential, safe information
        return {
            "invite_id": invite_id,
            "template_id": template_id,
            "image_url": full_image_url,
            "customizations": sanitized_customizations
        }
    
    except Exception as e:
        # Log error internally but don't expose sensitive details
        print(f"Error generating invite: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

async def generate_invite_image(template, elements, template_id):
    """Generate the actual image from template and elements"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import base64
        import io
        import os
        
        # Get template dimensions
        width = template['dimensions']['width']
        height = template['dimensions']['height']
        
        # Create image
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw background
        background = template.get('background', '#ffffff')
        if background.startswith('#'):
            # Solid color background
            img = Image.new('RGB', (width, height), color=background)
            draw = ImageDraw.Draw(img)
        elif background.startswith('data:image'):
            # Image background
            try:
                bg_data = background.split(',')[1]
                bg_image_data = base64.b64decode(bg_data)
                bg_image = Image.open(io.BytesIO(bg_image_data))
                bg_image = bg_image.resize((width, height))
                img.paste(bg_image)
                draw = ImageDraw.Draw(img)
            except Exception as e:
                print(f"Error loading background image: {e}")
        
        # Draw elements
        for element in elements:
            if element['type'] == 'text':
                # Draw text
                x = element.get('x', 0)
                y = element.get('y', 0)
                content = element.get('content', '')
                font_size = element.get('fontSize', 24)
                color = element.get('color', '#000000')
                
                # Try to load font, fallback to default
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
                except:
                    try:
                        font = ImageFont.truetype("arial.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
                
                # Handle multiline text
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    line_y = y + (i * font_size)
                    draw.text((x, line_y), line, fill=color, font=font)
            
            elif element['type'] == 'image' and element.get('src'):
                # Draw image
                try:
                    x = element.get('x', 0)
                    y = element.get('y', 0)
                    img_width = element.get('width', 100)
                    img_height = element.get('height', 100)
                    shape = element.get('shape', 'rectangle')
                    
                    # Decode base64 image
                    img_data = element['src'].split(',')[1]
                    img_bytes = base64.b64decode(img_data)
                    element_img = Image.open(io.BytesIO(img_bytes))
                    
                    # Resize image
                    element_img = element_img.resize((img_width, img_height))
                    
                    if shape == 'circle':
                        # Create circular mask
                        mask = Image.new('L', (img_width, img_height), 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.ellipse((0, 0, img_width, img_height), fill=255)
                        
                        # Apply mask
                        element_img.putalpha(mask)
                    
                    # Paste image onto main image
                    if element_img.mode == 'RGBA':
                        img.paste(element_img, (x, y), element_img)
                    else:
                        img.paste(element_img, (x, y))
                        
                except Exception as e:
                    print(f"Error processing image element: {e}")
        
        # Save image
        os.makedirs('/app/generated_images', exist_ok=True)
        image_filename = f"invite_{template_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}.png"
        image_path = f"/app/generated_images/{image_filename}"
        img.save(image_path, 'PNG', quality=95)
        
        # Return relative URL path (will be combined with full domain in the API response)
        image_url = f"/api/images/{image_filename}"
        return image_url
        
    except Exception as e:
        print(f"Error generating image: {e}")
        return None

# Serve generated images
@app.get("/api/images/{filename}")
async def get_generated_image(filename: str):
    """Serve generated images"""
    try:
        image_path = f"/app/generated_images/{filename}"
        if os.path.exists(image_path):
            from fastapi.responses import FileResponse
            return FileResponse(image_path, media_type="image/png")
        else:
            raise HTTPException(status_code=404, detail="Imagem não encontrada")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao servir imagem: {str(e)}")

# Get generated invite
@app.get("/api/generated/{invite_id}")
async def get_generated_invite(invite_id: str):
    """Get a generated invite by ID"""
    try:
        invite = generated_collection.find_one({"id": invite_id}, {"_id": 0})
        if not invite:
            raise HTTPException(status_code=404, detail="Convite gerado não encontrado")
        return invite
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar convite: {str(e)}")

# List generated invites for a template
@app.get("/api/templates/{template_id}/generated")
async def get_template_generated_invites(template_id: str):
    """Get all generated invites for a specific template"""
    try:
        invites = list(generated_collection.find(
            {"template_id": template_id}, 
            {"_id": 0, "elements": 0}  # Exclude elements to reduce response size
        ).sort("created_at", -1))
        return invites
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar convites gerados: {str(e)}")

# Bulk generate invites
@app.post("/api/templates/{template_id}/bulk-generate")
async def bulk_generate_invites(template_id: str, bulk_data: List[Dict[str, Any]]):
    """Generate multiple personalized invites at once"""
    try:
        # Get template
        template = templates_collection.find_one({"id": template_id}, {"_id": 0})
        if not template:
            raise HTTPException(status_code=404, detail="Template não encontrado")
        
        generated_invites = []
        
        for customizations in bulk_data:
            # Generate personalized invite (similar to single generate)
            personalized_elements = []
            
            for element in template['elements']:
                new_element = element.copy()
                
                if element['type'] == 'text':
                    for key, value in customizations.items():
                        if key in element.get('content', '').lower() or key == 'text':
                            new_element['content'] = str(value)
                            break
                
                elif element['type'] == 'image':
                    for key, value in customizations.items():
                        if key == 'image' or key == 'photo':
                            if isinstance(value, str) and value.startswith('data:image'):
                                new_element['src'] = value
                            break
                
                personalized_elements.append(new_element)
            
            # Generate unique ID for this invite
            invite_id = str(uuid.uuid4())
            
            generated_invite = {
                "id": invite_id,
                "template_id": template_id,
                "template_name": template['name'],
                "elements": personalized_elements,
                "background": template['background'],
                "dimensions": template['dimensions'],
                "customizations": customizations,
                "created_at": datetime.utcnow()
            }
            
            generated_invites.append(generated_invite)
        
        # Insert all at once
        if generated_invites:
            generated_collection.insert_many(generated_invites)
        
        return {
            "message": f"{len(generated_invites)} convites gerados com sucesso",
            "invites": [{"id": invite["id"], "customizations": invite["customizations"]} 
                       for invite in generated_invites]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar convites em lote: {str(e)}")

# Get API usage statistics
@app.get("/api/stats")
async def get_stats():
    """Get API usage statistics"""
    try:
        total_templates = templates_collection.count_documents({})
        total_generated = generated_collection.count_documents({})
        
        # Recent activity (last 7 days)
        from datetime import timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_generated = generated_collection.count_documents({"created_at": {"$gte": week_ago}})
        
        return {
            "total_templates": total_templates,
            "total_generated_invites": total_generated,
            "recent_generated_invites": recent_generated,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)