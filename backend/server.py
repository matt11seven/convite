from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import uuid
import base64
import json
from datetime import datetime
import io
from PIL import Image, ImageDraw, ImageFont
import requests

# Environment variables
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')

# MongoDB setup
client = MongoClient(MONGO_URL)
db = client.convites_db
templates_collection = db.templates
generated_collection = db.generated_invites

app = FastAPI(title="Sistema de Convites Personalizados", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class TemplateElement(BaseModel):
    type: str  # 'text' or 'image'
    x: int
    y: int
    content: Optional[str] = None  # For text elements
    src: Optional[str] = None  # For image elements (base64)
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
    background: str  # Color hex or base64 image
    dimensions: TemplateDimensions

class GenerateRequest(BaseModel):
    template_id: str
    customizations: Dict[str, Any]  # Key-value pairs for customization

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Sistema de Convites Personalizados API", "version": "1.0.0"}

# Health check
@app.get("/api/health")
async def health_check():
    try:
        # Test database connection
        db.list_collection_names()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

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

# Generate personalized invite
@app.post("/api/generate/{template_id}")
async def generate_invite(template_id: str, customizations: Dict[str, Any]):
    """Generate a personalized invite based on template and customizations"""
    try:
        # Get template
        template = templates_collection.find_one({"id": template_id}, {"_id": 0})
        if not template:
            raise HTTPException(status_code=404, detail="Template não encontrado")
        
        # Create a copy of the template with customizations applied
        personalized_elements = []
        
        for element in template['elements']:
            new_element = element.copy()
            
            # Apply customizations based on element type and content
            if element['type'] == 'text':
                # Check if there's a customization for this text element
                for key, value in customizations.items():
                    if key in element.get('content', '').lower() or key == 'text':
                        new_element['content'] = str(value)
                        break
            
            elif element['type'] == 'image':
                # Check if there's a customization for this image element
                for key, value in customizations.items():
                    if key == 'image' or key == 'photo':
                        # If value is a base64 image, use it
                        if isinstance(value, str) and value.startswith('data:image'):
                            new_element['src'] = value
                        break
            
            personalized_elements.append(new_element)
        
        # Generate unique ID for this personalized invite
        invite_id = str(uuid.uuid4())
        
        # Save the generated invite
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
        
        generated_collection.insert_one(generated_invite)
        
        return {
            "id": invite_id,
            "template_id": template_id,
            "elements": personalized_elements,
            "background": template['background'],
            "dimensions": template['dimensions'],
            "message": "Convite personalizado gerado com sucesso"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar convite: {str(e)}")

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