import React, { useState, useRef, useEffect } from 'react';
import './App.css';

const App = () => {
  const canvasRef = useRef(null);
  const [templates, setTemplates] = useState([]);
  const [currentTemplate, setCurrentTemplate] = useState(null);
  const [selectedElement, setSelectedElement] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('templates');
  const [showElementsList, setShowElementsList] = useState(true);
  const [templateInfoExpanded, setTemplateInfoExpanded] = useState(true);
  
  // Template structure
  const [templateElements, setTemplateElements] = useState([]);
  const [templateBackground, setTemplateBackground] = useState('#2d1b3d');
  const [templateName, setTemplateName] = useState('Novo Convite');

  // Canvas dimensions (portrait - similar to the example)
  const canvasWidth = 400;
  const canvasHeight = 600;

  // Drag and resize state
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [resizeHandle, setResizeHandle] = useState(null);
  const [lastClickPos, setLastClickPos] = useState({ x: canvasWidth / 2, y: canvasHeight / 2 });
  
  // Endpoint details state
  const [isEndpointExpanded, setIsEndpointExpanded] = useState(false);
  const [isFirstTimeCreated, setIsFirstTimeCreated] = useState(false);

  const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

  useEffect(() => {
    loadTemplates();
    drawCanvas();
  }, [templateElements, templateBackground]);

  const loadTemplates = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/templates`);
      const data = await response.json();
      setTemplates(data);
    } catch (error) {
      console.error('Erro ao carregar templates:', error);
    }
  };

  const drawCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Clear canvas
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);
    
    // Draw background
    if (templateBackground.startsWith('#')) {
      ctx.fillStyle = templateBackground;
      ctx.fillRect(0, 0, canvasWidth, canvasHeight);
    } else if (templateBackground.startsWith('data:image')) {
      const img = new Image();
      img.onload = () => {
        ctx.drawImage(img, 0, 0, canvasWidth, canvasHeight);
        drawElements(ctx);
      };
      img.src = templateBackground;
      return;
    }
    
    drawElements(ctx);
  };

  const drawElements = (ctx) => {
    templateElements.forEach((element, index) => {
      if (element.type === 'text') {
        ctx.fillStyle = element.color || '#ffffff';
        
        // Build font string with weight and style
        let fontString = '';
        if (element.fontStyle === 'italic') fontString += 'italic ';
        if (element.fontWeight === 'bold') fontString += 'bold ';
        fontString += `${element.fontSize || 24}px ${element.fontFamily || 'Arial'}`;
        
        ctx.font = fontString;
        ctx.textAlign = element.textAlign || 'left';
        
        // Draw text
        const lines = element.content.split('\n');
        lines.forEach((line, lineIndex) => {
          ctx.fillText(line, element.x, element.y + (lineIndex * (element.fontSize || 24)));
        });
        
        // Calculate text bounds for selection
        const metrics = ctx.measureText(element.content);
        const textWidth = Math.max(metrics.width, 50); // Minimum width for easier selection
        const textHeight = (element.fontSize || 24) * lines.length;
        
        // Store bounds for hit detection
        element._bounds = {
          x: element.x - 5,
          y: element.y - (element.fontSize || 24) - 5,
          width: textWidth + 10,
          height: textHeight + 10
        };
        
        // Draw selection border and handles if selected
        if (selectedElement === index) {
          ctx.strokeStyle = '#10B981';
          ctx.lineWidth = 2;
          ctx.strokeRect(element._bounds.x, element._bounds.y, element._bounds.width, element._bounds.height);
          
          // Resize handles
          drawResizeHandles(ctx, element._bounds.x, element._bounds.y, element._bounds.width, element._bounds.height);
        }
      } else if (element.type === 'image') {
        // Store bounds for hit detection
        element._bounds = {
          x: element.x,
          y: element.y,
          width: element.width,
          height: element.height
        };
        
        if (element.src) {
          const img = new Image();
          img.onload = () => {
            ctx.save();
            if (element.shape === 'circle') {
              ctx.beginPath();
              ctx.arc(element.x + element.width/2, element.y + element.height/2, 
                     Math.min(element.width, element.height)/2, 0, 2 * Math.PI);
              ctx.clip();
            }
            ctx.drawImage(img, element.x, element.y, element.width, element.height);
            ctx.restore();
            
            // Draw selection border and handles if selected
            if (selectedElement === index) {
              ctx.strokeStyle = '#10B981';
              ctx.lineWidth = 2;
              if (element.shape === 'circle') {
                ctx.beginPath();
                ctx.arc(element.x + element.width/2, element.y + element.height/2, 
                       Math.min(element.width, element.height)/2 + 2, 0, 2 * Math.PI);
                ctx.stroke();
              } else {
                ctx.strokeRect(element.x - 2, element.y - 2, element.width + 4, element.height + 4);
              }
              drawResizeHandles(ctx, element.x, element.y, element.width, element.height);
            }
          };
          img.src = element.src;
        } else {
          // Draw placeholder
          ctx.fillStyle = element.shape === 'circle' ? '#ffffff' : '#cccccc';
          if (element.shape === 'circle') {
            ctx.beginPath();
            ctx.arc(element.x + element.width/2, element.y + element.height/2, 
                   Math.min(element.width, element.height)/2, 0, 2 * Math.PI);
            ctx.fill();
          } else {
            ctx.fillRect(element.x, element.y, element.width, element.height);
          }
          
          // Placeholder text
          ctx.fillStyle = '#666666';
          ctx.font = '12px Arial';
          ctx.textAlign = 'center';
          ctx.fillText('Clique para adicionar imagem', 
                      element.x + element.width/2, element.y + element.height/2);
          
          // Selection border and handles
          if (selectedElement === index) {
            ctx.strokeStyle = '#10B981';
            ctx.lineWidth = 2;
            if (element.shape === 'circle') {
              ctx.beginPath();
              ctx.arc(element.x + element.width/2, element.y + element.height/2, 
                     Math.min(element.width, element.height)/2 + 2, 0, 2 * Math.PI);
              ctx.stroke();
            } else {
              ctx.strokeRect(element.x - 2, element.y - 2, element.width + 4, element.height + 4);
            }
            drawResizeHandles(ctx, element.x, element.y, element.width, element.height);
          }
        }
      }
    });
  };

  const drawResizeHandles = (ctx, x, y, width, height) => {
    const handleSize = 10;
    ctx.fillStyle = '#10B981';
    ctx.strokeStyle = '#059669';
    ctx.lineWidth = 2;
    
    // Corner and side handles
    const handles = [
      { x: x - handleSize/2, y: y - handleSize/2 }, // top-left
      { x: x + width - handleSize/2, y: y - handleSize/2 }, // top-right
      { x: x - handleSize/2, y: y + height - handleSize/2 }, // bottom-left
      { x: x + width - handleSize/2, y: y + height - handleSize/2 }, // bottom-right
      { x: x + width/2 - handleSize/2, y: y - handleSize/2 }, // top-center
      { x: x + width/2 - handleSize/2, y: y + height - handleSize/2 }, // bottom-center
      { x: x - handleSize/2, y: y + height/2 - handleSize/2 }, // left-center
      { x: x + width - handleSize/2, y: y + height/2 - handleSize/2 }, // right-center
    ];
    
    handles.forEach(handle => {
      ctx.fillRect(handle.x, handle.y, handleSize, handleSize);
      ctx.strokeRect(handle.x, handle.y, handleSize, handleSize);
    });
  };

  const getResizeHandle = (x, y, element) => {
    if (!element._bounds) return null;
    
    const handleSize = 10;
    const bounds = element._bounds;
    
    const handles = [
      { name: 'nw', x: bounds.x - handleSize/2, y: bounds.y - handleSize/2 },
      { name: 'ne', x: bounds.x + bounds.width - handleSize/2, y: bounds.y - handleSize/2 },
      { name: 'sw', x: bounds.x - handleSize/2, y: bounds.y + bounds.height - handleSize/2 },
      { name: 'se', x: bounds.x + bounds.width - handleSize/2, y: bounds.y + bounds.height - handleSize/2 },
      { name: 'n', x: bounds.x + bounds.width/2 - handleSize/2, y: bounds.y - handleSize/2 },
      { name: 's', x: bounds.x + bounds.width/2 - handleSize/2, y: bounds.y + bounds.height - handleSize/2 },
      { name: 'w', x: bounds.x - handleSize/2, y: bounds.y + bounds.height/2 - handleSize/2 },
      { name: 'e', x: bounds.x + bounds.width - handleSize/2, y: bounds.y + bounds.height/2 - handleSize/2 },
    ];
    
    for (let handle of handles) {
      if (x >= handle.x && x <= handle.x + handleSize && 
          y >= handle.y && y <= handle.y + handleSize) {
        console.log('Handle detected:', handle.name); // Debug log
        return handle.name;
      }
    }
    return null;
  };

  const isPointInElement = (x, y, element) => {
    if (!element._bounds) return false;
    
    if (element.type === 'image' && element.shape === 'circle') {
      // Check if point is inside circle
      const centerX = element.x + element.width/2;
      const centerY = element.y + element.height/2;
      const radius = Math.min(element.width, element.height)/2;
      const distance = Math.sqrt((x - centerX)**2 + (y - centerY)**2);
      return distance <= radius;
    } else {
      // Check if point is inside rectangle bounds
      return x >= element._bounds.x && x <= element._bounds.x + element._bounds.width &&
             y >= element._bounds.y && y <= element._bounds.y + element._bounds.height;
    }
  };

  const handleCanvasClick = (e) => {
    // This function now only handles selection, drag starts on mousedown
    // This prevents the element from getting "stuck" selected
  };

  const handleCanvasMouseMove = (e) => {
    if (!isDragging && !isResizing) return;
    
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    if (isDragging && selectedElement !== null) {
      // Drag element
      const updated = [...templateElements];
      const element = updated[selectedElement];
      
      const newX = Math.max(0, Math.min(canvasWidth - (element.width || 100), x - dragStart.x));
      const newY = Math.max(0, Math.min(canvasHeight - (element.height || 50), y - dragStart.y));
      
      updated[selectedElement] = {
        ...element,
        x: newX,
        y: newY
      };
      setTemplateElements(updated);
      
    } else if (isResizing && selectedElement !== null && resizeHandle) {
      // Resize element
      const updated = [...templateElements];
      const element = updated[selectedElement];
      const initialDragPos = dragStart;
      const deltaX = x - initialDragPos.x;
      const deltaY = y - initialDragPos.y;
      
      if (element.type === 'text') {
        // For text, adjust font size based on handle direction
        let sizeMultiplier = 1;
        
        if (resizeHandle.includes('e') || resizeHandle.includes('se') || resizeHandle.includes('ne')) {
          sizeMultiplier = 1 + (deltaX / 100); // Right side handles increase with right movement
        } else if (resizeHandle.includes('w') || resizeHandle.includes('sw') || resizeHandle.includes('nw')) {
          sizeMultiplier = 1 - (deltaX / 100); // Left side handles decrease with right movement
        }
        
        if (resizeHandle.includes('s') || resizeHandle.includes('se') || resizeHandle.includes('sw')) {
          sizeMultiplier *= 1 + (deltaY / 100); // Bottom handles increase with down movement
        } else if (resizeHandle.includes('n') || resizeHandle.includes('ne') || resizeHandle.includes('nw')) {
          sizeMultiplier *= 1 - (deltaY / 100); // Top handles decrease with down movement
        }
        
        const originalSize = element.fontSize || 24;
        const newSize = Math.max(8, Math.min(120, originalSize * sizeMultiplier));
        element.fontSize = Math.round(newSize);
        
      } else if (element.type === 'image') {
        // Store original dimensions for reference
        const originalWidth = element.width;
        const originalHeight = element.height;
        const originalX = element.x;
        const originalY = element.y;
        
        let newWidth = originalWidth;
        let newHeight = originalHeight;
        let newX = originalX;
        let newY = originalY;
        
        // Calculate new dimensions based on handle
        switch (resizeHandle) {
          case 'se': // bottom-right
            newWidth = Math.max(20, originalWidth + deltaX);
            newHeight = Math.max(20, originalHeight + deltaY);
            break;
          case 'sw': // bottom-left
            newWidth = Math.max(20, originalWidth - deltaX);
            newHeight = Math.max(20, originalHeight + deltaY);
            if (newWidth >= 20) newX = originalX + deltaX;
            break;
          case 'ne': // top-right
            newWidth = Math.max(20, originalWidth + deltaX);
            newHeight = Math.max(20, originalHeight - deltaY);
            if (newHeight >= 20) newY = originalY + deltaY;
            break;
          case 'nw': // top-left
            newWidth = Math.max(20, originalWidth - deltaX);
            newHeight = Math.max(20, originalHeight - deltaY);
            if (newWidth >= 20) newX = originalX + deltaX;
            if (newHeight >= 20) newY = originalY + deltaY;
            break;
          case 'e': // right
            newWidth = Math.max(20, originalWidth + deltaX);
            break;
          case 'w': // left
            newWidth = Math.max(20, originalWidth - deltaX);
            if (newWidth >= 20) newX = originalX + deltaX;
            break;
          case 's': // bottom
            newHeight = Math.max(20, originalHeight + deltaY);
            break;
          case 'n': // top
            newHeight = Math.max(20, originalHeight - deltaY);
            if (newHeight >= 20) newY = originalY + deltaY;
            break;
        }
        
        // Keep circle shape square
        if (element.shape === 'circle') {
          const size = Math.min(newWidth, newHeight);
          newWidth = size;
          newHeight = size;
        }
        
        // Ensure element stays within canvas bounds
        newX = Math.max(0, Math.min(canvasWidth - newWidth, newX));
        newY = Math.max(0, Math.min(canvasHeight - newHeight, newY));
        
        element.x = newX;
        element.y = newY;
        element.width = newWidth;
        element.height = newHeight;
      }
      
      setTemplateElements(updated);
    }
  };

  const handleCanvasMouseUp = (e) => {
    setIsDragging(false);
    setIsResizing(false);
    setResizeHandle(null);
  };

  const handleCanvasMouseDown = (e) => {
    e.preventDefault();
    
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    // Store last click position for new elements
    setLastClickPos({ x, y });
    
    // Check if clicked on an element (in reverse order for top-to-bottom selection)
    let clickedElement = -1;
    let handle = null;
    
    for (let i = templateElements.length - 1; i >= 0; i--) {
      const element = templateElements[i];
      
      // Check if clicked on resize handle first (only for selected element)
      if (selectedElement === i) {
        handle = getResizeHandle(x, y, element);
        if (handle) {
          clickedElement = i;
          setResizeHandle(handle);
          setIsResizing(true);
          setDragStart({ x, y });
          return; // Exit early for resize
        }
      }
      
      // Check if clicked on element
      if (isPointInElement(x, y, element)) {
        clickedElement = i;
        break;
      }
    }
    
    if (clickedElement >= 0) {
      // Start dragging
      setSelectedElement(clickedElement);
      setIsDragging(true);
      const element = templateElements[clickedElement];
      setDragStart({ 
        x: x - element.x, 
        y: y - element.y 
      });
    } else {
      // Clicked on empty space - deselect
      setSelectedElement(null);
      setIsDragging(false);
      setIsResizing(false);
    }
  };

  const addTextElement = () => {
    const newElement = {
      type: 'text',
      content: 'Novo Texto',
      x: lastClickPos.x,
      y: lastClickPos.y,
      fontSize: 24,
      fontFamily: 'Arial',
      color: '#ffffff',
      textAlign: 'left',
      fontWeight: 'normal',
      fontStyle: 'normal'
    };
    setTemplateElements([...templateElements, newElement]);
    setSelectedElement(templateElements.length);
  };

  const addImageElement = () => {
    const newElement = {
      type: 'image',
      x: lastClickPos.x - 50,
      y: lastClickPos.y - 50,
      width: 100,
      height: 100,
      shape: 'rectangle',
      src: null
    };
    setTemplateElements([...templateElements, newElement]);
    setSelectedElement(templateElements.length);
  };

  const addCircleImageElement = () => {
    const newElement = {
      type: 'image',
      x: lastClickPos.x - 75,
      y: lastClickPos.y - 75,
      width: 150,
      height: 150,
      shape: 'circle',
      src: null
    };
    setTemplateElements([...templateElements, newElement]);
    setSelectedElement(templateElements.length);
  };

  const updateSelectedElement = (property, value) => {
    if (selectedElement !== null) {
      const updated = [...templateElements];
      updated[selectedElement] = { ...updated[selectedElement], [property]: value };
      setTemplateElements(updated);
    }
  };

  const handleImageUpload = async (e) => {
    const file = e.target.files[0];
    if (!file || selectedElement === null) return;
    
    const reader = new FileReader();
    reader.onload = (event) => {
      updateSelectedElement('src', event.target.result);
    };
    reader.readAsDataURL(file);
  };

  const handleBackgroundUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (event) => {
      setTemplateBackground(event.target.result);
    };
    reader.readAsDataURL(file);
  };

  const saveTemplate = async () => {
    if (!templateName.trim()) {
      alert('Por favor, insira um nome para o template');
      return;
    }
    
    setIsLoading(true);
    try {
      const templateData = {
        name: templateName,
        elements: templateElements,
        background: templateBackground,
        dimensions: { width: canvasWidth, height: canvasHeight }
      };
      
      const response = await fetch(`${backendUrl}/api/templates`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(templateData),
      });
      
      if (response.ok) {
        const result = await response.json();
        alert(`Template salvo com sucesso! ID: ${result.id}`);
        loadTemplates();
        setCurrentTemplate(result);
        setIsFirstTimeCreated(true);
        setIsEndpointExpanded(true); // Expand when first created
      } else {
        alert('Erro ao salvar template');
      }
    } catch (error) {
      alert('Erro ao salvar template: ' + error.message);
    }
    setIsLoading(false);
  };

  const loadTemplate = async (templateId) => {
    try {
      const response = await fetch(`${backendUrl}/api/templates/${templateId}`);
      if (response.ok) {
        const template = await response.json();
        setCurrentTemplate(template);
        setTemplateElements(template.elements);
        setTemplateBackground(template.background);
        setTemplateName(template.name);
        setSelectedElement(null);
        setIsFirstTimeCreated(false);
        setIsEndpointExpanded(false); // Minimize when loading existing template
      }
    } catch (error) {
      console.error('Erro ao carregar template:', error);
    }
  };

  const createNewTemplate = () => {
    setCurrentTemplate(null);
    setTemplateElements([]);
    setTemplateBackground('#2d1b3d');
    setTemplateName('Novo Convite');
    setSelectedElement(null);
    setIsFirstTimeCreated(false);
    setIsEndpointExpanded(false);
  };

  const deleteTemplate = async (templateId, templateName) => {
    console.log('deleteTemplate chamado:', { templateId, templateName }); // Debug
    
    if (!window.confirm(`Tem certeza que deseja excluir o template "${templateName}"?\n\nEsta ação não pode ser desfeita.`)) {
      console.log('Exclusão cancelada pelo usuário'); // Debug
      return;
    }
    
    console.log('Iniciando exclusão...'); // Debug
    setIsLoading(true);
    try {
      const response = await fetch(`${backendUrl}/api/templates/${templateId}`, {
        method: 'DELETE',
      });
      
      console.log('Resposta do delete:', response.status); // Debug
      
      if (response.ok) {
        alert('Template excluído com sucesso!');
        // If the deleted template was the current one, clear it
        if (currentTemplate && currentTemplate.id === templateId) {
          setCurrentTemplate(null);
          createNewTemplate();
        }
        loadTemplates();
      } else {
        const errorData = await response.json();
        console.error('Erro na resposta:', errorData); // Debug
        alert(`Erro ao excluir template: ${errorData.detail || 'Erro desconhecido'}`);
      }
    } catch (error) {
      console.error('Erro na requisição:', error); // Debug
      alert('Erro ao excluir template: ' + error.message);
    }
    setIsLoading(false);
  };

  const deleteElement = () => {
    if (selectedElement !== null) {
      const updated = templateElements.filter((_, index) => index !== selectedElement);
      setTemplateElements(updated);
      setSelectedElement(null);
    }
  };

  const getCustomizableFields = (template) => {
    // Use current template elements if template is not provided
    const elements = template ? template.elements : templateElements;
    if (!elements || elements.length === 0) return [];
    
    const fields = new Set();
    elements.forEach((element, index) => {
      if (element.type === 'text' && element.content) {
        // Look for placeholder patterns like {nome}, {evento}, etc.
        const matches = element.content.match(/\{([^}]+)\}/g);
        if (matches) {
          matches.forEach(match => {
            fields.add(match.slice(1, -1));
          });
        }
        
        // Also add common text identifiers
        const content = element.content.toLowerCase();
        if (content.includes('nome') || content.includes('name')) {
          fields.add('nome');
        } else if (content.includes('evento') || content.includes('event')) {
          fields.add('evento');
        } else if (content.includes('data') || content.includes('date')) {
          fields.add('data');
        } else if (content.includes('local') || content.includes('location')) {
          fields.add('local');
        } else {
          // For any text element without specific keywords, create a generic field
          fields.add(`texto_${index + 1}`);
        }
      }
      
      // Only add 'imagem' if there's actually an image element without src
      if (element.type === 'image') {
        if (!element.src) {
          fields.add(`imagem_${index + 1}`);
        } else {
          // Even if it has src, allow replacement
          fields.add(`imagem_${index + 1}`);
        }
      }
    });
    
    // Don't add default fields - only show actual customizable fields
    return Array.from(fields);
  };

  const getExampleRequestBody = (template) => {
    const fields = getCustomizableFields(template);
    if (fields.length === 0) return {};
    
    const exampleBody = {};
    
    fields.forEach(field => {
      if (field.startsWith('imagem_')) {
        exampleBody[field] = 'https://example.com/path/to/image.jpg';
      } else if (field.startsWith('texto_')) {
        exampleBody[field] = 'Texto personalizado';
      } else if (field === 'nome') {
        exampleBody[field] = 'João Silva';
      } else if (field === 'evento') {
        exampleBody[field] = 'Casamento';
      } else if (field === 'data') {
        exampleBody[field] = '25/12/2024';
      } else if (field === 'local') {
        exampleBody[field] = 'Igreja São José';
      } else {
        exampleBody[field] = `Exemplo ${field}`;
      }
    });
    
    return exampleBody;
  };



  return (
    <div className="app">
      <div className="header">
        <div className="header-brand">
          <div className="header-logo">
            ✨
          </div>
          <div>
            <h1>Canva de Convites</h1>
            <div className="header-subtitle">Design para convites personalizados</div>
          </div>
        </div>
        
        <div className="header-stats">
          <div className="stat-item">
            <span className="stat-number">{templates.length}</span>
            <span className="stat-label">Templates</span>
          </div>
          <div className="stat-item">
            <span className="stat-number">∞</span>
            <span className="stat-label">Possibilidades</span>
          </div>
        </div>

        <div className="header-actions">
          <button 
            className="btn btn-primary btn-medium"
            onClick={createNewTemplate}
          >
            ✨ Novo Template
          </button>
          <button 
            className="btn btn-success btn-medium"
            onClick={saveTemplate}
            disabled={isLoading}
          >
            {isLoading ? '💾 Salvando...' : '💾 Salvar Template'}
          </button>
        </div>
      </div>

      <div className="main-content">
        <div className="sidebar">
          <div className="tabs">
            <button 
              className={`tab ${activeTab === 'templates' ? 'active' : ''}`}
              onClick={() => setActiveTab('templates')}
            >
              Templates
            </button>
            <button 
              className={`tab ${activeTab === 'elements' ? 'active' : ''}`}
              onClick={() => setActiveTab('elements')}
            >
              Elementos
            </button>
            <button 
              className={`tab ${activeTab === 'properties' ? 'active' : ''}`}
              onClick={() => setActiveTab('properties')}
            >
              Propriedades
            </button>
          </div>

          <div className="tab-content">
            {activeTab === 'templates' && (
              <div className="templates-panel">
                <h3>Meus Templates</h3>
                <div className="templates-grid">
                  {templates.map((template) => (
                    <div 
                      key={template.id} 
                      className="template-card"
                    >
                      <div className="template-card-content">
                        <div 
                          className="template-preview"
                          onClick={() => loadTemplate(template.id)}
                        >
                          <span>{template.name}</span>
                        </div>
                        <div className="template-actions">
                          <button 
                            className="btn-icon btn-edit"
                            onClick={() => loadTemplate(template.id)}
                            title="Editar template"
                          >
                            ✏️
                          </button>
                          <button 
                            className="btn-icon btn-delete"
                            onClick={(e) => {
                              console.log('Botão de delete clicado', { templateId: template.id, templateName: template.name }); // Debug
                              e.preventDefault();
                              e.stopPropagation();
                              deleteTemplate(template.id, template.name);
                            }}
                            title="Excluir template"
                            disabled={isLoading}
                          >
                            🗑️
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                  {templates.length === 0 && (
                    <div className="no-templates">
                      <p>Nenhum template criado ainda.</p>
                      <p>Crie seu primeiro template usando o editor!</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'elements' && (
              <div className="elements-panel">
                <h3>Adicionar Elementos</h3>
                
                <div className="element-group">
                  <h4>Texto</h4>
                  <button className="element-btn" onClick={addTextElement}>
                    + Adicionar Texto
                  </button>
                </div>

                <div className="element-group">
                  <h4>Imagens</h4>
                  <button className="element-btn" onClick={addImageElement}>
                    + Imagem Retangular
                  </button>
                  <button className="element-btn" onClick={addCircleImageElement}>
                    + Imagem Circular
                  </button>
                </div>

                <div className="element-group">
                  <h4>Background</h4>
                  <input 
                    type="color" 
                    value={templateBackground.startsWith('#') ? templateBackground : '#2d1b3d'}
                    onChange={(e) => setTemplateBackground(e.target.value)}
                  />
                  <input 
                    type="file" 
                    accept="image/*"
                    onChange={handleBackgroundUpload}
                    style={{ marginTop: '10px' }}
                  />
                </div>
              </div>
            )}

            {activeTab === 'properties' && (
              <div className="properties-panel">
                <h3>⚙️ Propriedades</h3>
                
                {/* Elements List - New Clean Design */}
                <div className="elements-manager">
                  <div className="elements-header">
                    <span className="elements-title">
                      📋 Elementos ({templateElements.length})
                    </span>
                    {templateElements.length > 0 && (
                      <button 
                        className="btn-clear-all"
                        onClick={() => {
                          if (window.confirm('Remover todos os elementos?')) {
                            setTemplateElements([]);
                            setSelectedElement(null);
                          }
                        }}
                        title="Limpar todos"
                      >
                        🗑️ Limpar
                      </button>
                    )}
                  </div>
                  
                  {showElementsList && (
                    <div className="elements-dropdown">
                      {templateElements.length === 0 ? (
                        <div className="no-elements-compact">
                          Use a aba "Elementos" para adicionar
                        </div>
                      ) : (
                        templateElements.map((element, index) => (
                          <div 
                            key={index}
                            className={`element-item-compact ${selectedElement === index ? 'selected' : ''}`}
                            onClick={() => setSelectedElement(index)}
                          >
                            <span className="element-icon-small">
                              {element.type === 'text' ? '📝' : '🖼️'}
                            </span>
                            <div className="element-info-compact">
                              <span className="element-name-compact">
                                {element.type === 'text' ? 'Texto' : 'Imagem'} {index + 1}
                              </span>
                              <span className="element-preview-compact">
                                {element.type === 'text' 
                                  ? (element.content || 'Vazio').substring(0, 20) + (element.content && element.content.length > 20 ? '...' : '')
                                  : element.src ? 'Com imagem' : 'Placeholder'
                                }
                              </span>
                            </div>
                            <div className="element-actions-compact">
                              <button 
                                className="btn-micro"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  const duplicated = { ...element };
                                  duplicated.x += 10;
                                  duplicated.y += 10;
                                  const updated = [...templateElements];
                                  updated.splice(index + 1, 0, duplicated);
                                  setTemplateElements(updated);
                                  setSelectedElement(index + 1);
                                }}
                                title="Duplicar"
                              >
                                📋
                              </button>
                              <button 
                                className="btn-micro btn-delete"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (window.confirm('Remover elemento?')) {
                                    const updated = templateElements.filter((_, i) => i !== index);
                                    setTemplateElements(updated);
                                    setSelectedElement(selectedElement === index ? null : 
                                      selectedElement > index ? selectedElement - 1 : selectedElement);
                                  }
                                }}
                                title="Remover"
                              >
                                ❌
                              </button>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>

                {/* Element Properties */}
                {selectedElement !== null && templateElements[selectedElement] && (
                  <div className="element-properties">
                    <div className="properties-header-compact">
                      <span className="editing-indicator">
                        ⚙️ {templateElements[selectedElement].type === 'text' ? 'Texto' : 'Imagem'} {selectedElement + 1}
                      </span>
                    </div>
                
                    {templateElements[selectedElement]?.type === 'text' && (
                      <div className="property-group">
                        <label>Texto:</label>
                        <textarea 
                          value={templateElements[selectedElement].content}
                          onChange={(e) => updateSelectedElement('content', e.target.value)}
                          rows="2"
                          placeholder="Digite seu texto..."
                        />
                        
                        <label>Fonte:</label>
                        <div className="font-controls">
                          <select 
                            value={templateElements[selectedElement].fontFamily || 'Arial'}
                            onChange={(e) => updateSelectedElement('fontFamily', e.target.value)}
                            className="font-select"
                          >
                            <option value="Arial">Arial</option>
                            <option value="Helvetica">Helvetica</option>
                            <option value="Times New Roman">Times</option>
                            <option value="Georgia">Georgia</option>
                            <option value="Verdana">Verdana</option>
                            <option value="Impact">Impact</option>
                          </select>
                          <div className="range-compact">
                            <input 
                              type="range"
                              min="8"
                              max="80"
                              value={templateElements[selectedElement].fontSize || 24}
                              onChange={(e) => updateSelectedElement('fontSize', parseInt(e.target.value))}
                            />
                            <span className="range-value-compact">{templateElements[selectedElement].fontSize || 24}px</span>
                          </div>
                        </div>
                        
                        <label>Estilo:</label>
                        <div className="style-controls-compact">
                          <input 
                            type="color"
                            value={templateElements[selectedElement].color || '#ffffff'}
                            onChange={(e) => updateSelectedElement('color', e.target.value)}
                            className="color-picker-compact"
                          />
                          <div className="alignment-compact">
                            <button 
                              className={`btn-style ${templateElements[selectedElement].textAlign === 'left' ? 'active' : ''}`}
                              onClick={() => updateSelectedElement('textAlign', 'left')}
                            >←</button>
                            <button 
                              className={`btn-style ${templateElements[selectedElement].textAlign === 'center' ? 'active' : ''}`}
                              onClick={() => updateSelectedElement('textAlign', 'center')}
                            >↔</button>
                            <button 
                              className={`btn-style ${templateElements[selectedElement].textAlign === 'right' ? 'active' : ''}`}
                              onClick={() => updateSelectedElement('textAlign', 'right')}
                            >→</button>
                          </div>
                          <div className="text-style-compact">
                            <button 
                              className={`btn-style ${templateElements[selectedElement].fontWeight === 'bold' ? 'active' : ''}`}
                              onClick={() => updateSelectedElement('fontWeight', 
                                templateElements[selectedElement].fontWeight === 'bold' ? 'normal' : 'bold')}
                            ><strong>B</strong></button>
                            <button 
                              className={`btn-style ${templateElements[selectedElement].fontStyle === 'italic' ? 'active' : ''}`}
                              onClick={() => updateSelectedElement('fontStyle', 
                                templateElements[selectedElement].fontStyle === 'italic' ? 'normal' : 'italic')}
                            ><em>I</em></button>
                          </div>
                        </div>

                        <label>Posição:</label>
                        <div className="position-compact">
                          <input 
                            type="number"
                            value={Math.round(templateElements[selectedElement].x)}
                            onChange={(e) => updateSelectedElement('x', parseInt(e.target.value))}
                            placeholder="X"
                          />
                          <input 
                            type="number"
                            value={Math.round(templateElements[selectedElement].y)}
                            onChange={(e) => updateSelectedElement('y', parseInt(e.target.value))}
                            placeholder="Y"
                          />
                        </div>
                      </div>
                    )}

                    {templateElements[selectedElement]?.type === 'image' && (
                      <div className="property-group">
                        <label>Imagem:</label>
                        <input 
                          type="file"
                          accept="image/*"
                          onChange={handleImageUpload}
                          className="file-input-compact"
                        />
                        
                        <label>Tamanho:</label>
                        <div className="size-controls">
                          <div className="range-compact">
                            <span className="range-label">W:</span>
                            <input 
                              type="range"
                              min="20"
                              max="400"
                              value={templateElements[selectedElement].width}
                              onChange={(e) => updateSelectedElement('width', parseInt(e.target.value))}
                            />
                            <span className="range-value-compact">{templateElements[selectedElement].width}</span>
                          </div>
                          <div className="range-compact">
                            <span className="range-label">H:</span>
                            <input 
                              type="range"
                              min="20"
                              max="400"
                              value={templateElements[selectedElement].height}
                              onChange={(e) => updateSelectedElement('height', parseInt(e.target.value))}
                            />
                            <span className="range-value-compact">{templateElements[selectedElement].height}</span>
                          </div>
                        </div>

                        <label>Forma & Posição:</label>
                        <div className="shape-position-compact">
                          <div className="shape-buttons-compact">
                            <button 
                              className={`btn-style ${templateElements[selectedElement].shape === 'rectangle' ? 'active' : ''}`}
                              onClick={() => updateSelectedElement('shape', 'rectangle')}
                            >⬜</button>
                            <button 
                              className={`btn-style ${templateElements[selectedElement].shape === 'circle' ? 'active' : ''}`}
                              onClick={() => updateSelectedElement('shape', 'circle')}
                            >⚫</button>
                          </div>
                          <div className="position-compact">
                            <input 
                              type="number"
                              value={Math.round(templateElements[selectedElement].x)}
                              onChange={(e) => updateSelectedElement('x', parseInt(e.target.value))}
                              placeholder="X"
                            />
                            <input 
                              type="number"
                              value={Math.round(templateElements[selectedElement].y)}
                              onChange={(e) => updateSelectedElement('y', parseInt(e.target.value))}
                              placeholder="Y"
                            />
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {selectedElement === null && (
                  <div className="no-selection-compact">
                    <span>👆 Selecione um elemento para editar</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="canvas-area">
          <div className="canvas-header">
            <input 
              type="text"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              className="template-name-input"
              placeholder="Nome do template"
            />
            {currentTemplate && (
              <div className="template-info">
                <div 
                  className="endpoint-header"
                  onClick={() => setIsEndpointExpanded(!isEndpointExpanded)}
                >
                  <span className="endpoint-title">
                    ✨ Detalhes da API Premium
                  </span>
                  <span className={`expand-icon ${isEndpointExpanded ? 'expanded' : ''}`}>
                    ▼
                  </span>
                </div>
                
                {isEndpointExpanded && (
                  <div className="endpoint-details">
                    <div className="endpoint-item">
                      <strong>🆔 Template ID:</strong>
                      <div className="code-container">
                        <code className="endpoint-code">{currentTemplate.id}</code>
                        <button 
                          className="copy-btn"
                          onClick={() => {
                            navigator.clipboard.writeText(currentTemplate.id);
                            // Add visual feedback
                            const btn = document.activeElement;
                            const originalText = btn.innerHTML;
                            btn.innerHTML = '<span class="copy-icon">✅</span><span class="copy-text">Copiado!</span>';
                            setTimeout(() => {
                              btn.innerHTML = originalText;
                            }, 1500);
                          }}
                          title="Copiar Template ID"
                        >
                          <span className="copy-icon">📋</span>
                          <span className="copy-text">Copiar</span>
                        </button>
                      </div>
                    </div>
                    
                    <div className="endpoint-item">
                      <strong>🚀 API Endpoint:</strong>
                      <div className="code-container">
                        <code className="endpoint-code">
                          POST {backendUrl}/api/generate/{currentTemplate.id}
                        </code>
                        <button 
                          className="copy-btn"
                          onClick={() => {
                            navigator.clipboard.writeText(`${backendUrl}/api/generate/${currentTemplate.id}`);
                            const btn = document.activeElement;
                            const originalText = btn.innerHTML;
                            btn.innerHTML = '<span class="copy-icon">✅</span><span class="copy-text">Copiado!</span>';
                            setTimeout(() => {
                              btn.innerHTML = originalText;
                            }, 1500);
                          }}
                          title="Copiar URL da API"
                        >
                          <span className="copy-icon">📋</span>
                          <span className="copy-text">Copiar</span>
                        </button>
                      </div>
                    </div>
                    
                    <div className="endpoint-item">
                      <strong>⚙️ Campos Personalizáveis:</strong>
                      <div className="customizable-fields">
                        {templateElements.map((element, index) => (
                          <div key={index} className="field-item">
                            <span className="field-icon">
                              {element.type === 'text' ? '📝' : '🖼️'}
                            </span>
                            <code>{element.type}_{index + 1}</code>
                            <span className="field-type">
                              ({element.type === 'text' ? 'string' : 'image_url'})
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                    
                    <div className="endpoint-item">
                      <strong>🎯 Exemplo de Payload:</strong>
                      <div className="json-container">
                        <pre className="json-example">
{`{
${templateElements.map((element, index) => 
  `  "${element.type}_${index + 1}": "${element.type === 'text' ? 'Novo texto personalizado' : 'https://example.com/image.jpg'}"`
).join(',\n')}
}`}
                        </pre>
                        <button 
                          className="copy-json-btn"
                          onClick={() => {
                            const payload = `{\n${templateElements.map((element, index) => 
                              `  "${element.type}_${index + 1}": "${element.type === 'text' ? 'Novo texto personalizado' : 'https://example.com/image.jpg'}"`
                            ).join(',\n')}\n}`;
                            navigator.clipboard.writeText(payload);
                          }}
                          title="Copiar JSON completo"
                        >
                          <span className="copy-icon">📋</span>
                          <span className="copy-text">Copiar JSON</span>
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
            {!currentTemplate && console.log('currentTemplate é null/undefined')}
            {currentTemplate && console.log('currentTemplate existe:', currentTemplate)}
          </div>
          
          <div className="canvas-container">
            <canvas
              ref={canvasRef}
              width={canvasWidth}
              height={canvasHeight}
              onMouseDown={handleCanvasMouseDown}
              onClick={handleCanvasClick}
              onMouseMove={handleCanvasMouseMove}
              onMouseUp={handleCanvasMouseUp}
              onMouseLeave={handleCanvasMouseUp}
              className="design-canvas"
              style={{ 
                cursor: isDragging ? 'grabbing' : (isResizing ? 'nw-resize' : (selectedElement !== null ? 'grab' : 'default'))
              }}
            />
          </div>
          
          <div className="canvas-info">
            <p>Clique nos elementos para selecioná-los e editá-los no painel lateral</p>
            {selectedElement !== null && (
              <p>Elemento selecionado: {templateElements[selectedElement]?.type}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;