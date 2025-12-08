# Tu primer Agente de IA
Este repositorio es el código para el video "Tu primer agente de IA" inspirado del canal Ringa Tech

## Configuración
Para ejecutar el proyecto es necesario:
- Descargar el repositorio
- Opcional: Crea un ambiente virtual
- Instala las dependencias ejecutando 
	- ```  pip install -r requirements.txt ```
	
## 🔎 Resumen general

Un resumen claro y visual del propósito y la arquitectura del proyecto.

- 🧭 **Propósito:** agente REPL que envía el historial de la conversación a una API tipo OpenAI / LM Studio y permite que el modelo invoque "herramientas" (funciones del sistema) para leer/editar archivos y ejecutar comandos bash. Los resultados de las herramientas se reinyectan en el historial para que el modelo genere la respuesta final.
- 🚪 **Entrypoint:** `main.py` — configura el cliente `OpenAI`, crea la instancia `Agent()` y ejecuta el REPL de usuario.
- 🧩 **Componente principal:** `Agent` (archivo `agent.py`) — mantiene `self.messages` (historial), `self.tools` (esquema JSON pasado al cliente) y `self.TOOLS_FUNCTIONS` (mapeo nombre → función Python).
- 🔁 **Flujo de datos:** usuario → `agent.messages` → llamada a `client.chat.completions.create(messages=..., tools=...)` → `Agent.process_response(response)` → si el modelo pidió una herramienta, `Agent` la ejecuta, añade el resultado a `messages` con `role: "tool"` y el ciclo repite; si no llamó herramienta, se imprime la respuesta final.

---

## 📁 Archivos clave

- `main.py`
	- Inicializa el cliente `OpenAI` apuntando a LM Studio (`base_url="http://localhost:1234/v1"`) y gestiona el REPL.
	- Lee la entrada del usuario, la añade a `agent.messages` y llama a la API con `messages` + `tools`.
	- Si `Agent.process_response()` indica que se ejecutó una herramienta, repite la llamada para que el modelo vea el resultado.

- `agent.py` (clase `Agent`)
	- Implementa las herramientas, mantiene el historial y procesa las respuestas del modelo.

---

## 🧠 Agent — atributos importantes

- **`self.messages`**: lista del historial de mensajes. El primer elemento es un `system` con instrucciones en español.
- **`self.tools`**: lista de definiciones (JSON Schema) que describen las herramientas disponibles para que el modelo pueda invocarlas.
- **`self.TOOLS_FUNCTIONS`**: diccionario que mapea nombres de herramienta a funciones Python (por ejemplo: `"read_file": self.read_file`).
- **`self.MAX_MESSAGES`**: entero que limita el número de mensajes guardados para evitar que el contexto crezca indefinidamente.

---

## 🔧 Métodos principales (qué hacen y notas)

- `__init__(self)`
	- Inicializa `messages` con un `system` prompt, llama a `setup_tools()` y configura el mapeo de funciones.

- `setup_tools(self)`
	- Construye `self.tools` con la estructura que se pasa a la API (cada entrada describe `name`, `description` y `parameters`).
	- Nota: la estructura exacta debe coincidir con la versión del SDK/LM Studio en uso.

- `read_file(self, path)`
	- Lee el archivo `path` en UTF-8. Si el archivo es muy grande, devuelve un fragmento con aviso de truncado (protección contra respuestas gigantes).
	- Devuelve `string` con contenido o mensaje de error.

- `edit_file(self, path, prev_text, new_text)`
	- Reemplaza `prev_text` por `new_text` si existe (o crea/sobrescribe el archivo si `prev_text` está vacío).
	- Crea directorios padres si es necesario y devuelve un mensaje de resultado.
	- Riesgo: operaciones destructivas — el `system` prompt pide confirmar acciones peligrosas.

- `execute_bash_command(self, command)`
	- Ejecuta un comando en el sistema y devuelve su salida (truncada si es muy larga).
	- Riesgo de seguridad: ejecución arbitraria de comandos; considerar validación o confirmación.

- `_cleanup_messages(self)`
	- Mantiene el historial acotado: conserva el mensaje `system` y las últimas `N` interacciones cuando se supera `MAX_MESSAGES`.

- `handle_tool_call(self, tool_name, tool_input)`
	- Valida y ejecuta la herramienta solicitada; captura `TypeError` y excepciones generales para devolver errores legibles.

- `process_response(self, response)`
	- Analiza la respuesta del modelo (resultado de `client.chat.completions.create`).
	- Si el modelo solicita una herramienta (`tool_calls`):
		- Parsea los argumentos JSON, ejecuta la herramienta con `handle_tool_call`, añade al historial un `role: "assistant"` indicando la intención de llamada y luego un `role: "tool"` con el resultado.
		- Devuelve `True` para que `main.py` repita la llamada y el modelo vea el resultado.
	- Si no hubo `tool_calls`: añade la respuesta final como `role: "assistant"`, imprime el texto y devuelve `False`.
