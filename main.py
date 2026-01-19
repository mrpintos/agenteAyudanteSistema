from openai import OpenAI
from dotenv import load_dotenv
from agent import Agent
import sys
import os
import json

# Habilitar colores ANSI en Windows
os.system('') if sys.platform == 'win32' else None

load_dotenv()
MODEL=os.getenv("MODEL_NAME_DEFAULT") # Modelo por defecto

print(f"Mi primer agente de IA ({MODEL})")

agent = Agent()

# --- CONFIGURACIÓN DEL CLIENTE (SIN CAMBIOS) ---
# Apunta al servidor local de LM Studio (por defecto: puerto 1234)
client = OpenAI(
    base_url = os.environ.get("BASE_URL"),
    api_key = os.environ.get("OPENAI_API_KEY")
)

# Códigos ANSI para colores
GREEN = "\033[92m"
RESET = "\033[0m"

while True:
    user_input = input(f"\n👦 {GREEN}Tú: {RESET}").strip()
    
    # Validaciones básicas
    if not user_input:
        continue

    # Si hay una confirmación pendiente, tratamos el input como respuesta a la confirmación
    if agent.pending_confirmation:
        ans = user_input.strip().lower()
        if ans in ("si", "sí", "s", "yes", "y"):
            cmd = agent.pending_confirmation.get("command")
            print("Confirmación recibida: ejecutando comando pendiente...")
            # Ejecutar inmediatamente y añadir el resultado como un mensaje 'tool'
            result = agent.handle_tool_call("execute_terminal_command", {"command": cmd, "_confirmed": True})
            try:
                params_json = json.dumps({"command": cmd}, ensure_ascii=False, indent=2)
            except Exception:
                params_json = str({"command": cmd})
            combined = f"== execute_terminal_command ==\nParámetros: {params_json}\n{result}"
            agent.messages.append({
                "role": "tool",
                "content": combined,
                "display_as": "code",
                "tool_calls": [{
                    "type": "function",
                    "function": {"name": "execute_terminal_command", "arguments": json.dumps({"command": cmd}, ensure_ascii=False)}
                }]
            })
            agent.pending_confirmation = None
            # Ahora dejamos que el flujo normal continúe para que el modelo reciba la salida y responda
        elif ans in ("no", "n"):
            agent.messages.append({"role": "assistant", "content": "Operación cancelada por el usuario."})
            agent.pending_confirmation = None
            # pedimos otro prompt
            continue
        else:
            print("Por favor responde 'sí' o 'no' para confirmar la operación.")
            # no añadimos user_input al historial, pedimos de nuevo
            continue

    # Comandos especiales
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

    # Agregar nuestro mensaje al historial como entrada de usuario
    agent.messages.append({"role": "user", "content": user_input})
    
    # Bucle que permite que, si el modelo invoca herramientas, procesarlas y luego repetir
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

        # Si se generó una confirmación pendiente, salimos del bucle interior para esperar la confirmación del usuario
        if agent.pending_confirmation is not None:
            # El mensaje con la petición de confirmación ya fue agregado por process_response/handle_tool_call
            break
        
        # Si no se llamó herramienta, tenemos la respuesta final
        if not called_tool:
            break
