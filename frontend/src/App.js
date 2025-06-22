import React, { useState, useRef, useEffect } from 'react';
import './App.css';

const App = () => {
  const canvasRef = useRef(null);
  const [templates, setTemplates] = useState([]);
  const [currentTemplate, setCurrentTemplate] = useState(null);
  const [selectedElement, setSelectedElement] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('templates');
  
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
        ctx.font = `${element.fontSize || 24}px ${element.fontFamily || 'Arial'}`;
        ctx.textAlign = element.textAlign || 'center';
        ctx.fillText(element.content, element.x, element.y);
        
        // Draw selection border if selected
        if (selectedElement === index) {
          ctx.strokeStyle = '#00ff00';
          ctx.lineWidth = 2;
          const metrics = ctx.measureText(element.content);
          ctx.strokeRect(element.x - metrics.width/2 - 5, element.y - (element.fontSize || 24) - 5, 
                        metrics.width + 10, (element.fontSize || 24) + 10);
        }
      } else if (element.type === 'image') {
        if (element.src) {
          const img = new Image();
          img.onload = () => {
            ctx.save();
            if (element.shape === 'circle') {
              ctx.beginPath();
              ctx.arc(element.x + element.width/2, element.y + element.height/2, element.width/2, 0, 2 * Math.PI);
              ctx.clip();
            }
            ctx.drawImage(img, element.x, element.y, element.width, element.height);
            ctx.restore();
            
            // Draw selection border if selected
            if (selectedElement === index) {
              ctx.strokeStyle = '#00ff00';
              ctx.lineWidth = 2;
              if (element.shape === 'circle') {
                ctx.beginPath();
                ctx.arc(element.x + element.width/2, element.y + element.height/2, element.width/2 + 2, 0, 2 * Math.PI);
                ctx.stroke();
              } else {
                ctx.strokeRect(element.x - 2, element.y - 2, element.width + 4, element.height + 4);
              }
            }
          };
          img.src = element.src;
        } else {
          // Draw placeholder
          ctx.fillStyle = element.shape === 'circle' ? '#ffffff' : '#cccccc';
          if (element.shape === 'circle') {
            ctx.beginPath();
            ctx.arc(element.x + element.width/2, element.y + element.height/2, element.width/2, 0, 2 * Math.PI);
            ctx.fill();
          } else {
            ctx.fillRect(element.x, element.y, element.width, element.height);
          }
          
          // Placeholder text
          ctx.fillStyle = '#666666';
          ctx.font = '12px Arial';
          ctx.textAlign = 'center';
          ctx.fillText('Clique para adicionar imagem', element.x + element.width/2, element.y + element.height/2);
          
          // Selection border
          if (selectedElement === index) {
            ctx.strokeStyle = '#00ff00';
            ctx.lineWidth = 2;
            if (element.shape === 'circle') {
              ctx.beginPath();
              ctx.arc(element.x + element.width/2, element.y + element.height/2, element.width/2 + 2, 0, 2 * Math.PI);
              ctx.stroke();
            } else {
              ctx.strokeRect(element.x - 2, element.y - 2, element.width + 4, element.height + 4);
            }
          }
        }
      }
    });
  };

  const handleCanvasClick = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    // Check if clicked on an element
    let clickedElement = -1;
    templateElements.forEach((element, index) => {
      if (element.type === 'text') {
        const ctx = canvas.getContext('2d');
        ctx.font = `${element.fontSize || 24}px ${element.fontFamily || 'Arial'}`;
        const metrics = ctx.measureText(element.content);
        if (x >= element.x - metrics.width/2 && x <= element.x + metrics.width/2 &&
            y >= element.y - (element.fontSize || 24) && y <= element.y) {
          clickedElement = index;
        }
      } else if (element.type === 'image') {
        if (element.shape === 'circle') {
          const centerX = element.x + element.width/2;
          const centerY = element.y + element.height/2;
          const distance = Math.sqrt((x - centerX)**2 + (y - centerY)**2);
          if (distance <= element.width/2) {
            clickedElement = index;
          }
        } else {
          if (x >= element.x && x <= element.x + element.width &&
              y >= element.y && y <= element.y + element.height) {
            clickedElement = index;
          }
        }
      }
    });
    
    setSelectedElement(clickedElement >= 0 ? clickedElement : null);
  };

  const addTextElement = () => {
    const newElement = {
      type: 'text',
      content: 'Novo Texto',
      x: canvasWidth / 2,
      y: canvasHeight / 2,
      fontSize: 24,
      fontFamily: 'Arial',
      color: '#ffffff',
      textAlign: 'center'
    };
    setTemplateElements([...templateElements, newElement]);
    setSelectedElement(templateElements.length);
  };

  const addImageElement = () => {
    const newElement = {
      type: 'image',
      x: canvasWidth / 2 - 50,
      y: canvasHeight / 2 - 50,
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
      x: canvasWidth / 2 - 75,
      y: canvasHeight / 2 - 75,
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
  };

  const deleteElement = () => {
    if (selectedElement !== null) {
      const updated = templateElements.filter((_, index) => index !== selectedElement);
      setTemplateElements(updated);
      setSelectedElement(null);
    }
  };

  return (
    <div className="app">
      <div className="header">
        <h1>Editor de Convites Personalizados</h1>
        <div className="header-actions">
          <button 
            className="btn btn-primary"
            onClick={createNewTemplate}
          >
            Novo Template
          </button>
          <button 
            className="btn btn-success"
            onClick={saveTemplate}
            disabled={isLoading}
          >
            {isLoading ? 'Salvando...' : 'Salvar Template'}
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
                      onClick={() => loadTemplate(template.id)}
                    >
                      <div className="template-preview">
                        <span>{template.name}</span>
                      </div>
                    </div>
                  ))}
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

            {activeTab === 'properties' && selectedElement !== null && (
              <div className="properties-panel">
                <h3>Propriedades do Elemento</h3>
                
                {templateElements[selectedElement]?.type === 'text' && (
                  <div className="property-group">
                    <label>Texto:</label>
                    <input 
                      type="text"
                      value={templateElements[selectedElement].content}
                      onChange={(e) => updateSelectedElement('content', e.target.value)}
                    />
                    
                    <label>Tamanho da Fonte:</label>
                    <input 
                      type="number"
                      value={templateElements[selectedElement].fontSize || 24}
                      onChange={(e) => updateSelectedElement('fontSize', parseInt(e.target.value))}
                    />
                    
                    <label>Cor:</label>
                    <input 
                      type="color"
                      value={templateElements[selectedElement].color || '#ffffff'}
                      onChange={(e) => updateSelectedElement('color', e.target.value)}
                    />
                  </div>
                )}

                {templateElements[selectedElement]?.type === 'image' && (
                  <div className="property-group">
                    <label>Carregar Imagem:</label>
                    <input 
                      type="file"
                      accept="image/*"
                      onChange={handleImageUpload}
                    />
                    
                    <label>Largura:</label>
                    <input 
                      type="number"
                      value={templateElements[selectedElement].width}
                      onChange={(e) => updateSelectedElement('width', parseInt(e.target.value))}
                    />
                    
                    <label>Altura:</label>
                    <input 
                      type="number"
                      value={templateElements[selectedElement].height}
                      onChange={(e) => updateSelectedElement('height', parseInt(e.target.value))}
                    />
                  </div>
                )}

                <button className="btn btn-danger" onClick={deleteElement}>
                  Excluir Elemento
                </button>
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
                <span>ID: {currentTemplate.id}</span>
                <span>API: {backendUrl}/api/generate/{currentTemplate.id}</span>
              </div>
            )}
          </div>
          
          <div className="canvas-container">
            <canvas
              ref={canvasRef}
              width={canvasWidth}
              height={canvasHeight}
              onClick={handleCanvasClick}
              className="design-canvas"
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