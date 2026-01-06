import os
import json
import platform
import re
import subprocess

class Agent:
    def __init__(self):
        # Configuración de límites para gestión de memoria
        self.MAX_MESSAGES = 150  # Máximo de mensajes antes de limpiar
        
        self.setup_tools()
        # Estado para gestionar confirmaciones de comandos destructivos
        self.pending_confirmation = None

        self.messages = [
            {"role": "system", "content": 
             """Eres un asistente experto en administración de sistemas y ejecución de comandos de terminal.
                Responde en el mismo idioma que el usuario y sé conciso pero completo.
                Cuando el usuario quiera salir, despídete cortésmente y díle que para salir puede escribir "salir", "exit", "bye" o "sayonara".
                Si el usuario quiere cambiar el modelo, puede escribir "/models" y se le mostrará la lista de modelos disponibles.
           
                HERRAMIENTAS DISPONIBLES:
                1. get_system_os: Obtiene información del sistema operativo (plataforma, versión, arquitectura, hostname, Python).
                2. execute_terminal_command: Ejecuta comandos en el terminal del sistema operativo (ver descripción detallada abajo).

                IMPORTANTE — COMPORTAMIENTO Y FORMATO DE SALIDA DE `execute_terminal_command`:
                Cuando llames a `execute_terminal_command`, la herramienta ejecutará el comando y devolverá UNA CADENA con uno de los siguientes formatos — el agente debe interpretarlos exactamente así:

                - Comando exitoso con salida en stdout:
                    - Devuelve exactamente el texto del stdout (sin prefijos). Ejemplo: "file1.txt\nfile2.txt\n".

                - Comando exitoso sin salida:
                    - Devuelve: "✓ Comando ejecutado exitosamente (sin salida)".
                        Significado: el comando se ejecutó correctamente (returncode == 0) pero no generó salida. No vuelvas a ejecutar el mismo comando.

                - Comando exitoso con salida solo en stderr (raro):
                    - Devuelve: "✓ Comando ejecutado exitosamente\n<stderr>". Trata stderr como información adicional.

                - Comando con error (returncode != 0):
                    - Devuelve: "Error (código N): <mensaje>" donde <mensaje> es stderr si está presente, o stdout en su defecto.
                        Significado: el comando falló. NO asumas éxito. Analiza el mensaje de error, propón una corrección del comando o solicita aclaración al usuario antes de volver a ejecutarlo.

                - Timeout:
                    - Devuelve: "Error: El comando excedió el tiempo límite (60 o 600 segundos, depende del sistema)".

                - Excepción de ejecución:
                    - Devuelve: "Error al ejecutar el comando '<comando>': <detalle>".

                REGLAS OPERACIONALES PARA EL MODELO CUANDO USES `execute_terminal_command`:
                1) Antes de ejecutar comandos que dependan de rutas, sintaxis o comportamiento del OS, llama siempre a `get_system_os` y adapta los comandos (rutas, separadores, opciones) al SO detectado.
                2) Si la herramienta devuelve un texto que empieza por "Error (código" o "Error:", NO asumas éxito. Analiza el contenido del error y propón una acción concreta:
                    - Si es un error de permiso, sugiere usar `sudo` o pedir al usuario permisos explícitos.
                    - Si es un error de sintaxis o ruta, propone el comando corregido y explica brevemente el cambio.
                    - No vuelvas a ejecutar exactamente el mismo comando fallido sin cambios.
                3) Si la herramienta devuelve "✓ Comando ejecutado exitosamente (sin salida)", trata como éxito sin salida: continúa con la siguiente acción lógica, no repitas el comando.
                4) Si la herramienta devuelve stdout, úsalo como fuente de verdad para tus decisiones (parsea listas, tablas, rutas, tamaños, etc.).
                5) Para operaciones potencialmente destructivas (borrar, mover, sobrescribir), siempre pide confirmación explícita al usuario antes de ejecutar el comando.
                6) Cuando propongas un comando corregido, devuélvelo en forma de llamada a la herramienta (es decir, genera la herramienta `execute_terminal_command` con su `command` argument) en lugar de solo copiar el texto en tu mensaje; así el sistema podrá ejecutarlo.

                FORMATO DE MENSAJES Y SALIDAS:
                - Cuando la herramienta se invoque, el agente agregará un mensaje `tool` cuyo `content` contiene una concatenación legible de:
                    - "== <tool_name> ==\n"
                    - opcionalmente una línea: "Parámetros: <JSON pretty>\n" si la llamada tenía argumentos
                    - la salida o mensaje devuelto por la herramienta (según los formatos descritos arriba)

                RECUERDA: Prioriza la seguridad y la confirmación del usuario antes de acciones destructivas. Usa las salidas de las herramientas como hechos (no especules) y transforma los errores en acciones concretas: analizar, corregir o pedir confirmación al usuario."""
             }
        ]
        self.TOOLS_FUNCTIONS = {
            "execute_terminal_command": self.execute_terminal_command,
            "get_system_os": self.get_system_os
        }
    
    def setup_tools(self):
        self.tools = [
  
            {
                "type": "function",
                "function": {
                    "name": "execute_terminal_command",
                    "description": "Ejecuta un comando en el terminal del sistema operativo y devuelve el resultado. En sistemas Unix se ejecuta dentro de un shell Bash usando `bash -lc '<command>'`, lo que permite encadenar varios pasos (por ejemplo: descarga && instalación && source) en una única llamada y así mantener el estado dentro de esa invocación. Devuelve stdout si el comando es exitoso; en caso de error devuelve 'Error (código N): <mensaje>'. Si la operación requiere múltiples pasos dependientes, agrupa los pasos en una sola llamada usando operadores como `&&` o `;`.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "El comando a ejecutar en el terminal con sus argumentos si lo requiere"
                            }
                        },
                        "required": ["command"]
                    }
                }
            }
            ,
            {
                "type": "function",
                "function": {
                    "name": "get_system_os",
                    "description": "Devuelve información sobre el sistema operativo donde corre el programa (plataforma, versión, arquitectura, hostname, python). No se le pasan parámetros a esta función.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]
        
    def execute_terminal_command(self, command):
      
        try:
            # Ejecutar en un shell adecuado según el SO
            if platform.system().lower().startswith('win'):
                # En Windows usar shell por compatibilidad (cmd/powershell según disponibilidad)
                process = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            else:
                # En Unix, ejecutar mediante bash -lc para permitir encadenar y usar 'source' en la misma invocación
                process = subprocess.run(
                    ["bash", "-lc", command],
                    capture_output=True,
                    text=True,
                    timeout=600
                )

            # print(process)
            stdout = process.stdout.strip()
            stderr = process.stderr.strip()
            return_code = process.returncode
            
            # Si el comando fue exitoso (código 0) pero no hay salida, indicar éxito
            if return_code == 0:
                if not stdout and not stderr:
                    return f"✓ Comando ejecutado exitosamente (sin salida)"
                elif stdout:
                    return stdout
                else:
                    return f"✓ Comando ejecutado exitosamente\n{stderr}"
            else:
                # Comando falló
                error_msg = f"Error (código {return_code})"
                if stderr:
                    error_msg += f": {stderr}"
                elif stdout:
                    error_msg += f": {stdout}"
                return error_msg
                
        except subprocess.TimeoutExpired:
            return f"Error: El comando excedió el tiempo límite (30 segundos)"
        except Exception as e:
            err = f"Error al ejecutar el comando '{command}': {str(e)}"
            print(err)
            return err

    def _is_destructive_command(self, command: str):
        """Heurística simple para detectar comandos potencialmente destructivos.
        Devuelve (True, motivo) si coincide alguna de las reglas.
        """
        if not command or not isinstance(command, str):
            return (False, None)

        c = command.lower()
        # reglas simples / patrones
        patterns = [
            (r"\brm\b", "uso de 'rm'"),
            (r"rm\s+-rf", "uso de 'rm -rf'"),
            (r"\bsudo\b", "uso de 'sudo'"),
            (r"\bdd\b", "uso de 'dd'"),
            (r"\bmkfs\b", "creación de sistemas de ficheros (mkfs)"),
            (r"\breboot\b|\bshutdown\b", "reinicio/apagado del sistema"),
            (r"curl\s+.*\|\s*bash", "descarga e ejecución remota (curl | bash)"),
            (r"wget\s+.*\|\s*bash", "descarga e instalación remota (wget | bash)"),
            (r"\bapt\b|\bapt-get\b|\byum\b|\bdnf\b", "gestor de paquetes del sistema"),
            (r"\bpip\s+install\b", "instalación de paquetes con pip"),
            (r"\bchmod\s+777\b", "permisos abiertos (chmod 777)"),
            (r"\bshutdown\b", "apagado o shutdown"),
        ]

        for pat, reason in patterns:
            if re.search(pat, c):
                return (True, reason)
        return (False, None)

    def get_system_os(self):
        """Devuelve información básica del sistema operativo y entorno Python."""
        try:
            info = {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "hostname": platform.node(),
                "python_version": platform.python_version()
            }
            return info
        except Exception as e:
            err = f"Error obteniendo info del sistema operativo: {str(e)}"
            print(err)
            return err
    
    def _cleanup_messages(self):
        """Limpia el historial de mensajes si excede límites.
        Mantiene el mensaje de sistema y las últimas N interacciones."""
        if len(self.messages) > self.MAX_MESSAGES:
            # Mantener: sistema + últimas N-1 mensajes
            system_msg = self.messages[0]
            self.messages = [system_msg] + self.messages[-(self.MAX_MESSAGES - 1):]
            print(f"⚠️  Historial de mensajes limpiado (mantenidas últimas {self.MAX_MESSAGES - 1} interacciones)")
    
    def handle_tool_call(self, tool_name, tool_input):
        """Ejecuta una herramienta y maneja errores.
        Soporta un flag interno `_confirmed` en `tool_input` para indicar que el usuario ya confirmó
        una operación potencialmente destructiva y que no debe volver a pedirse confirmación.
        """
        if tool_name not in self.TOOLS_FUNCTIONS:
            return f"Error: Herramienta '{tool_name}' no encontrada"

        try:
            # Hacer una copia local de los argumentos (para no mutar estructuras externas)
            input_args = dict(tool_input) if isinstance(tool_input, dict) else {}
            # Extraer y eliminar el flag interno de confirmación si existe
            confirmed = bool(input_args.pop("_confirmed", False))

            # Intercepción para execute_terminal_command: detectar comandos destructivos
            if tool_name == "execute_terminal_command":
                cmd = input_args.get("command") if isinstance(input_args, dict) else None
                is_destructive, reason = self._is_destructive_command(cmd)
                if is_destructive and not confirmed:
                    # Guardar estado pendiente y pedir confirmación al usuario
                    self.pending_confirmation = {"command": cmd, "reason": reason}
                    print (f"\n\n⚠️ Se detectó un comando potencialmente destructivo: {reason}\nComando: {cmd}\nPor favor confirma escribiendo 'sí' para ejecutar o 'no' para cancelar.")
                    return (f"⚠️ Se detectó un comando potencialmente destructivo: {reason}\nComando: {cmd}\nPor favor confirma escribiendo 'sí' para ejecutar o 'no' para cancelar.")

            func = self.TOOLS_FUNCTIONS[tool_name]
            # Ejecutar la función con los argumentos (si los hay)
            result = func(**input_args) if isinstance(input_args, dict) else func()
            return result
        except TypeError as e:
            return f"Error en argumentos de {tool_name}: {str(e)}"
        except Exception as e:
            return f"Error ejecutando {tool_name}: {str(e)}"

    def process_response(self, response):
        """Procesa respuesta de OpenAI API.
        Retorna True si se ejecutó una herramienta, False si es respuesta final."""
        try:
            # Manejar respuestas con tool calls
            if response.choices[0].message.tool_calls:
                # Primero, compactar llamadas consecutivas a execute_terminal_command en una sola llamada
                raw_calls = response.choices[0].message.tool_calls
                merged_calls = []

                # --- NUEVA LÓGICA: parseo más robusto y deduplicado de llamadas ---
                for tc in raw_calls:
                    name = tc.function.name
                    args_raw = tc.function.arguments
                    # Try to parse JSON; tolerate some bad quoting
                    args = {}
                    try:
                        args = json.loads(args_raw) if args_raw else {}
                    except Exception:
                        try:
                            args = json.loads(args_raw.replace("'", '"'))
                        except Exception:
                            args = {}

                    # Sanitizar: si el dict tiene claves vacías ("" o espacios), tratarlas como {} 
                    if isinstance(args, dict):
                        if any((not str(k).strip()) for k in args.keys()):
                            args = {}

                    # Deduplicar llamadas consecutivas idénticas (mismo name + mismos args)
                    if merged_calls and name == merged_calls[-1]["name"] and merged_calls[-1]["args"] == args:
                        # Omitir duplicado
                        continue

                    # Mantener la lógica original de fusionar comandos `execute_terminal_command` consecutivos
                    if merged_calls and name == "execute_terminal_command" and merged_calls[-1]["name"] == "execute_terminal_command":
                        prev_cmd = merged_calls[-1]["args"].get("command", "")
                        new_cmd = args.get("command", "")
                        if prev_cmd and new_cmd:
                            merged = prev_cmd + " && " + new_cmd
                        else:
                            merged = prev_cmd or new_cmd
                        merged_calls[-1]["args"]["command"] = merged
                        # Nota: no duplicamos el 'raw' aquí
                    else:
                        merged_calls.append({"name": name, "args": args, "raw": args_raw})

                combined_outputs = []
                assistant_record = {"role": "assistant", "content": None, "tool_calls": []}

                # Ahora ejecutar cada llamada (ya fusionadas y deduplicadas)
                for mc in merged_calls:
                    tool_name = mc["name"]
                    tool_input = mc["args"] if isinstance(mc.get("args"), dict) else {}

                    print(f"\n 🛠️ Herramienta llamada: {tool_name}")
                    print(f" ⚙️ Argumento: {tool_input}")
                    result = self.handle_tool_call(tool_name, tool_input)

                    assistant_record["tool_calls"].append({
                        "type": "function",
                        "function": {"name": tool_name, "arguments": mc.get("raw")}
                    })

                    out_text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)

                    try:
                        params_json = json.dumps(tool_input, ensure_ascii=False, indent=2) if tool_input else ""
                    except Exception:
                        params_json = str(tool_input) if tool_input else ""

                    header = f"== {tool_name} ==\n"
                    param_line = f"Parámetros: {params_json}\n" if params_json else ""

                    combined_outputs.append(header + param_line + out_text)

                    # Si se generó una confirmación pendiente, detener la ejecución de llamadas subsecuentes
                    if self.pending_confirmation is not None:
                        print("⏳ Esperando confirmación del usuario para comando destructivo")
                        break

                combined_text = "\n\n".join(combined_outputs)
                self.messages.append({
                    "role": "tool",
                    "content": combined_text,
                    "display_as": "code",
                    "tool_calls": assistant_record["tool_calls"]
                })

                # Limpiar memoria si es necesario
                self._cleanup_messages()
                return True
                
            else:
                # Respuesta de texto normal
                output_text = response.choices[0].message.content
                if output_text:
                    self.messages.append({"role": "assistant", "content": output_text})
                    print(f"\n🤖 Asistente: {output_text}")
                
                # Limpiar memoria si es necesario
                self._cleanup_messages()
                return False
                
        except Exception as e:
            print(f"❌ Error procesando respuesta: {e}")
            self.messages.append({
                "role": "system",
                "content": f"Error interno: {str(e)}"
            })
            return False

