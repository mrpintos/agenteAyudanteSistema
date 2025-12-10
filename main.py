from openai import OpenAI
from dotenv import load_dotenv
from agent import Agent
import sys
import os




# Habilitar colores ANSI en Windows
os.system('') if sys.platform == 'win32' else None

load_dotenv()
MODEL="openai/gpt-oss-20b"  # Modelo por defecto

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
    
    if user_input.strip() == "/models":
        # Intentar con el cliente OpenAI primero
        try:
            models = client.models.list()
            i=0
            for m in models.data:
                activo=" (activo)" if m.id == MODEL else ""
                print(f"    {i} - {m.id}{GREEN}{activo}{RESET}")
                i+=1
            new_model = input(f"\n{GREEN}Si quiere cambiar de Modelo introduzca (0..{i-1}): {RESET}").strip()
            
            if new_model.isdigit() and 0 <= int(new_model) < i:
                
                MODEL = models.data[int(new_model)].id
                print(f"Modelo cambiado a: {MODEL}")
                agent.messages = [agent.messages[0]]  # Mantener solo system message
                print("✅ Historial limpiado. Nueva conversación con el modelo " + MODEL)
            else:
                print("Entrada no válida, no se cambió el modelo.")
            continue

        except Exception as e:
            print("No se pudieron listar los modelos:", e)
        continue

    # Agregar nuestro mensaje al historial
    agent.messages.append({"role": "user", "content": user_input})
    
    while True:
        response = client.chat.completions.create(
            model=MODEL,
            messages=agent.messages,
            tools=agent.tools,
            temperature=0.7,
            max_tokens=4096, 
            stream=False
        )
        
        called_tool = agent.process_response(response)
        
        # Si no se llamó herramienta, tenemos la respuesta final
        if not called_tool:
            break
        
        