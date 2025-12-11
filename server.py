from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv
import os
import json

from agent import Agent

load_dotenv()

APP = FastAPI(title="Agent API")

APP.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# servir carpeta estática
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.isdir(static_dir):
    os.makedirs(static_dir, exist_ok=True)
APP.mount("/static", StaticFiles(directory=static_dir), name="static")

# Cliente OpenAI (apunta a LM Studio por defecto)
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

# Modelo activo (valor por defecto)
MODEL = os.environ.get("AGENT_MODEL", "deepseek-r1-0528-qwen3-8b")

agent = Agent()


@APP.get("/")
def index():
    # Redirige a la página estática
    return RedirectResponse(url="/static/index.html")


@APP.get("/api/models")
def list_models():
    """Lista modelos desde la API (intenta client.models.list(), si falla usa /v1/models)."""
    try:
        models = client.models.list()
        ids = [m.id for m in models.data]
        return JSONResponse({"models": ids, "source": "client.models.list()"})
    except Exception:
        # Fallback: petición HTTP directa
        try:
            import requests
            resp = requests.get("http://localhost:1234/v1/models", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            items = []
            for item in data.get("data", []) or data.get("models", []):
                if isinstance(item, dict):
                    items.append(item.get("id") or item.get("name"))
                else:
                    items.append(str(item))
            return JSONResponse({"models": items, "source": "http://localhost:1234/v1/models"})
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"No se pudieron listar los modelos: {e}")


@APP.post("/api/model")
def change_model(payload: dict):
    """Cambia el modelo activo en el servidor (cliente solo actualiza variable y limpia historial).

    Payload: { "model": "model-name" }
    """
    global MODEL, agent
    model = payload.get("model") if payload else None
    if not model:
        raise HTTPException(status_code=400, detail="Campo 'model' requerido")

    # Actualizar variable y resetear la conversación
    old = MODEL
    MODEL = model
    agent.messages = [agent.messages[0]]
    return JSONResponse({"ok": True, "model": MODEL, "old_model": old, "cleared_history": True})


@APP.post("/api/chat")
def chat(payload: dict):
    """Enviar prompt y devolver la respuesta final. Mantiene el loop de tool-calls igual que main.py."""
    global MODEL, agent
    prompt = payload.get("prompt") if payload else None
    if prompt is None:
        raise HTTPException(status_code=400, detail="Campo 'prompt' requerido")

    # Añadir mensaje de usuario
    agent.messages.append({"role": "user", "content": prompt})

    # Llamadas repetidas si el modelo invoca herramientas
    last_assistant = None
    try:
        while True:
            # Ajuste simple de max_tokens para modelos grandes
            max_tokens = 2048 if "gemma" in MODEL.lower() or "gemma" in MODEL.lower() else 4000
            response = client.chat.completions.create(
                model=MODEL,
                messages=agent.messages,
                tools=agent.tools,
                temperature=0.7,
                max_tokens=max_tokens,
            )

            called_tool = agent.process_response(response)
            # Si no se llamó herramienta, la respuesta final ya está en agent.messages
            if not called_tool:
                # Buscar último mensaje assistant
                for m in reversed(agent.messages):
                    if m.get("role") == "assistant" and m.get("content"):
                        last_assistant = m.get("content")
                        break
                break

        # Filtrar historial para enviar al cliente: eliminar 'system', combinar múltiples 'tool' en uno
        filtered_messages = []
        last_tool_msg = None
        for msg in agent.messages:
            if msg.get("role") == "system":
                continue
            elif msg.get("role") == "tool":
                # Guardar el primer tool message; los posteriores se combinan
                if last_tool_msg is None:
                    last_tool_msg = msg.copy()
                else:
                    # Combinar contenido de múltiples tool messages
                    last_tool_msg["content"] = last_tool_msg.get("content", "") + "\n\n" + msg.get("content", "")
            else:
                # Antes de añadir mensaje no-tool, agregar el tool pendiente
                if last_tool_msg is not None:
                    filtered_messages.append(last_tool_msg)
                    last_tool_msg = None
                filtered_messages.append(msg)
        
        # Agregar último tool message si existe
        if last_tool_msg is not None:
            filtered_messages.append(last_tool_msg)
        
        return JSONResponse({"ok": True, "model": MODEL, "response": last_assistant, "messages": filtered_messages})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:APP", host="0.0.0.0", port=8000, reload=True)
