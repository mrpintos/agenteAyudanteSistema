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

- 🧭 **Propósito:** agente REPL que envía el historial de la conversación a una API tipo OpenAI / LM Studio y permite que el modelo invoque "herramientas" para ejecutar comandos del sistema y consultar información del SO. Los resultados se reinyectan en el historial para que el modelo genere la respuesta final.
- 🚪 **Entrypoint:** `main.py` — configura el cliente `OpenAI`, crea la instancia `Agent()`, gestiona colores ANSI en el prompt (verde para "Tú:") y ejecuta el REPL de usuario.
- 🧩 **Componente principal:** `Agent` (archivo `agent.py`) — mantiene `self.messages` (historial), `self.tools` (esquema JSON pasado al cliente) y `self.TOOLS_FUNCTIONS` (mapeo nombre → función Python).
- 🖥️ **Herramientas disponibles:**
  - `get_system_os`: obtiene información básica del SO (plataforma, versión, arquitectura, hostname, Python).
  - `execute_terminal_command`: ejecuta comandos del sistema con soporte mejorado (bash -lc en Unix, cmd/PowerShell en Windows) y timeout adaptativo.
- 🔒 **Seguridad y confirmaciones:** detección automática de comandos destructivos (rm, dd, sudo, pip install, chmod 777, curl | bash, etc.) — el agente solicita confirmación explícita del usuario antes de ejecutarlos.
- 🔁 **Flujo de datos:** usuario → `agent.messages` → llamada a `client.chat.completions.create(messages=..., tools=...)` → `Agent.process_response(response)` → si el modelo pidió una herramienta, `Agent` la ejecuta, añade el resultado a `messages` con `role: "tool"` y el ciclo repite; si no llamó herramienta, se imprime la respuesta final.

---

## 📁 Archivos clave

- `main.py`
	- Inicializa el cliente `OpenAI` apuntando a LM Studio (`base_url="http://localhost:1234/v1"`) y gestiona el REPL.
	- Lee la entrada del usuario, la añade a `agent.messages` y llama a la API con `messages` + `tools`.
	- Si `Agent.process_response()` indica que se ejecutó una herramienta, repite la llamada para que el modelo vea el resultado.

- `agent.py` (clase `Agent`)
	- Implementa todas las herramientas disponibles, mantiene el historial de mensajes, detecta comandos destructivos y procesa respuestas del modelo con soporte para múltiples llamadas a herramientas y fusión de comandos.

- `server.py` (servidor Web con FastAPI)
	- Interfaz Web del agente basada en FastAPI + carpeta `static/`.
	- Expone tres endpoints principales:
	  - `GET /`: redirige a `static/index.html`.
	  - `GET /api/models`: lista los modelos disponibles en LM Studio.
	  - `POST /api/model`: cambia el modelo activo y limpia el historial.
	  - `POST /api/chat`: envía un prompt al agente y devuelve la respuesta con historial filtrado.
	- Maneja confirmaciones pendientes para comandos destructivos (acepta "sí", "no" del usuario).
	- Filtra el historial antes de enviar al cliente (elimina `system`, agrupa múltiples `tool` messages).

---

## 🌐 Interfaz Web

La carpeta `static/` contiene la interfaz web moderna con soporte para chat interactivo:

- **`index.html`**
	- Estructura HTML5 con tres secciones: topbar (header con selector de modelos), chat log (zona de mensajes con scroll), footer (composer con textarea y botones).
	- Importa `style.css` y `script.js` para interactividad y estilos.

- **`script.js`**
	- Lógica del cliente JavaScript (ES6+).
	- Funcionalidades principales:
	  - `fetchModels()`: obtiene lista de modelos desde `GET /api/models` y los carga en el selector.
	  - Envío de prompts: captura el texto, lo envía a `POST /api/chat` y re-renderiza el historial.
	  - Cambio de modelo: envía el modelo seleccionado a `POST /api/model` con confirmación.
	  - Renderizado inteligente de mensajes: soporte para tablas tipo pipe (|---|), **negrita**, indicador de escritura (tres puntos animados), y salidas de herramientas con encabezados y parámetros colapsables.
	  - Scroll automático al final del chat tras cada mensaje.

- **`style.css`**
	- Diseño responsivo con variables CSS (`--bg`, `--card`, `--accent`, etc.).
	- Componentes principales:
	  - `.topbar`: barra fija en la parte superior con marca y controles de modelo.
	  - `.chat-log`: contenedor de mensajes con scroll propio.
	  - `.msg`: estilos para mensajes de usuario (fondo azul claro) y asistente (fondo blanco).
	  - `.code-block`: bloque de código con fondo negro y monoespaciado.
	  - `.pipe-table`: tablas generadas automáticamente con bordes y alternancia de filas.
	  - `.tool-container`: renderizado especial para salidas de herramientas con encabezado, parámetros colapsables y código.
	  - `.typing-indicator`: indicador de escritura (tres puntos pulsantes).

---

## 🧠 Agent — atributos importantes

- **`self.messages`**: lista del historial de mensajes. El primer elemento es un `system` con instrucciones detalladas en español.
- **`self.tools`**: lista de definiciones (JSON Schema) que describen las herramientas disponibles para que el modelo pueda invocarlas.
- **`self.TOOLS_FUNCTIONS`**: diccionario que mapea nombres de herramienta a funciones Python (por ejemplo: `"execute_terminal_command": self.execute_terminal_command`).
- **`self.MAX_MESSAGES`**: entero que limita el número de mensajes guardados para evitar que el contexto crezca indefinidamente (actual: 150).
- **`self.pending_confirmation`**: variable que mantiene el estado de un comando destructivo pendiente de confirmación por el usuario.

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

- `execute_terminal_command(self, command)`
	- Ejecuta un comando en el terminal del sistema con manejo intelligent del shell según el SO:
	  - **Windows:** ejecuta mediante `shell=True` con `subprocess.run` (timeout: 60s).
	  - **Unix/Linux/Mac:** ejecuta mediante `bash -lc` para permitir encadenar comandos con `&&` y usar `source` en la misma invocación (timeout: 600s).
	- Devuelve salida stdout si es exitosa, o mensajes de error estructurados si falla (código de error + stderr).
	- **Integración con seguridad:** detecta comandos potencialmente destructivos y solicita confirmación explícita del usuario antes de ejecutarlos.

- `get_system_os(self)`
	- Devuelve un diccionario con información básica del entorno donde corre el programa: `platform`, `platform_release`, `platform_version`, `architecture`, `hostname`, `python_version`.
	- Uso seguro: es solo lectura y no modifica el sistema — útil para que el modelo adapte comandos según el SO.

- `_is_destructive_command(self, command: str)`
	- Heurística que detecta patrones de comandos potencialmente peligrosos (rm, dd, sudo, mkfs, chmod 777, pip install, curl | bash, etc.).
	- Devuelve una tupla `(bool, motivo)` indicando si el comando es destructivo y por qué.

- `_cleanup_messages(self)`
	- Mantiene el historial acotado: conserva el mensaje `system` y las últimas `N` interacciones cuando se supera `MAX_MESSAGES`.

- `handle_tool_call(self, tool_name, tool_input)`
	- Valida y ejecuta la herramienta solicitada.
	- Para `execute_terminal_command`: detecta comandos destructivos y, si no están confirmados, genera un mensaje de alerta y pausa la ejecución esperando confirmación del usuario.
	- Captura errores de tipo y excepciones generales para devolver mensajes de error legibles.

- `process_response(self, response)`
	- Analiza la respuesta del modelo (resultado de `client.chat.completions.create`).
	- Características avanzadas:
	  - **Fusión de comandos:** si el modelo solicita múltiples `execute_terminal_command` consecutivos, los fusiona con `&&` en una sola llamada para mantener estado entre pasos.
	  - **Deduplicación:** elimina llamadas a herramientas duplicadas consecutivas (mismo nombre + mismos argumentos).
	  - **Parseo robusto:** tolera variaciones en JSON malformado (comillas simples vs dobles) en los argumentos.
	  - **Formato estructurado:** organiza las salidas de múltiples herramientas con encabezados claros (`== nombre ==`).
	- Si el modelo solicita una herramienta (`tool_calls`): ejecuta con `handle_tool_call`, añade los resultados al historial con `role: "tool"` y devuelve `True` para que `main.py` repita la llamada.
	- Si no hubo `tool_calls`: añade la respuesta final como `role: "assistant"`, imprime con prefijo `🤖`, y devuelve `False`.

---

## 📌 Ejemplos de uso

**Ejecutar el agente en el REPL (línea de comandos):**

Ejecutar `main.py` iniciará un REPL interactivo donde puedes conversar directamente con el agente en la terminal:

```bash
python main.py
```

El prompt "Tú: " aparecerá en verde en terminales que soportan colores ANSI. Escribe "salir", "exit", "bye" o "sayonara" para terminar.

**Ejecutar el servidor Web (interfaz gráfica):**

Ejecutar `server.py` levantará un servidor FastAPI en `http://localhost:8000` con interfaz Web interactiva:

```bash
python server.py
```

Luego abre tu navegador en `http://localhost:8000` (se redirige automáticamente a `/static/index.html`). Podrás:
- Ver el historial de la conversación en tiempo real.
- Cambiar el modelo activo desde el selector en la barra superior.
- Escribir prompts en el textarea del footer y enviarlos.
- Ver salidas de herramientas con formato especial (parámetros colapsables, code blocks).

**Probar `get_system_os()` localmente:**

```python
from agent import Agent
agent = Agent()
info = agent.get_system_os()
print(info)
# Ejemplo de salida:
# {'platform': 'Windows', 'platform_release': '11', 'platform_version': '10.0.26200', 'architecture': 'AMD64', 'hostname': 'mi-maquina', 'python_version': '3.13.9'}
```

**Probar detección de comandos destructivos:**

```python
from agent import Agent
agent = Agent()
is_destructive, reason = agent._is_destructive_command("rm -rf /")
print(f"Destructivo: {is_destructive}, Razón: {reason}")
# Salida: Destructivo: True, Razón: uso de 'rm -rf'
```

---

## 🔌 Endpoints de la API Web (`server.py`)

- **`GET /`**
	- Redirige a `/static/index.html`.

- **`GET /api/models`**
	- Devuelve JSON: `{"models": ["model-1", "model-2", ...], "source": "..."}`
	- Intenta obtener los modelos de `client.models.list()` (SDK OpenAI); si falla, hace fallback a HTTP directo a `http://localhost:1234/v1/models`.

- **`POST /api/model`**
	- Payload: `{"model": "nombre-del-modelo"}`
	- Devuelve: `{"ok": true, "model": "...", "old_model": "...", "cleared_history": true}`
	- Cambia el modelo activo y limpia el historial de mensajes (mantiene solo el `system` prompt).

- **`POST /api/chat`**
	- Payload: `{"prompt": "tu-pregunta"}`
	- Devuelve: `{"ok": true, "model": "...", "response": "respuesta-texto", "messages": [...]}`
	- Envía el prompt al agente, ejecuta el loop de herramientas si es necesario, y devuelve la respuesta final con historial filtrado.
	- Maneja confirmaciones pendientes: si hay un comando destructivo en espera, la siguiente llamada con "sí"/"no" confirma o cancela.
	- El historial devuelto (`messages`) excluye el `system` prompt y agrupa múltiples `tool` messages en uno.

---

## 📌 Ejemplos de uso (antiguo, mantener por compatibilidad)

**Probar `get_system_os()` localmente:**

```python
from agent import Agent
agent = Agent()
info = agent.get_system_os()
print(info)
# Ejemplo de salida:
# {'platform': 'Windows', 'platform_release': '11', 'platform_version': '10.0.26200', 'architecture': 'AMD64', 'hostname': 'mi-maquina', 'python_version': '3.13.9'}
```

**Probar detección de comandos destructivos:**

```python
from agent import Agent
agent = Agent()
is_destructive, reason = agent._is_destructive_command("rm -rf /")
print(f"Destructivo: {is_destructive}, Razón: {reason}")
# Salida: Destructivo: True, Razón: uso de 'rm -rf'
```

**Ejecutar el agente en el REPL:**

Ejecutar `main.py` iniciará un REPL interactivo donde puedes conversar con el agente. Este último invocará herramientas automáticamente según sea necesario:

```bash
python main.py
```

Escribe "salir", "exit", "bye" o "sayonara" para terminar la sesión. El prompt "Tú: " aparecerá en verde en terminales que soportan colores ANSI.
