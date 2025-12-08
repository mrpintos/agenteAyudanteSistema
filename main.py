from openai import OpenAI
from dotenv import load_dotenv
from agent import Agent
import sys
import os

# Habilitar colores ANSI en Windows
os.system('') if sys.platform == 'win32' else None

load_dotenv()
MODEL="openai/gpt-oss-20b"

print(f"Mi primer agente de IA ({MODEL})")

agent = Agent()

# --- CONFIGURACIÓN DEL CLIENTE (SIN CAMBIOS) ---
# Apunta al servidor local de LM Studio (por defecto: puerto 1234)
client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"  # Clave de API de marcador de posición
)

# Códigos ANSI para colores
GREEN = "\033[92m"
RESET = "\033[0m"

while True:
    user_input = input(f"\n{GREEN}Tú: {RESET}").strip()
    
    # Validaciones
    if not user_input:
        continue
    
    if user_input.lower() in ("salir", "exit", "bye", "sayonara"):
        print("Hasta luego!")
        break
    
    # Agregar nuestro mensaje al historial
    agent.messages.append({"role": "user", "content": user_input})
    
    while True:
        response = client.chat.completions.create(
            model=MODEL,
            messages=agent.messages,
            tools=agent.tools,
            temperature=0.7,
            max_tokens=4000
        )
        
        called_tool = agent.process_response(response)
        
        # Si no se llamó herramienta, tenemos la respuesta final
        if not called_tool:
            break
        
        