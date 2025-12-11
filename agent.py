import os
import json
import platform

class Agent:
    def __init__(self):
        # Configuración de límites para gestión de memoria
        self.MAX_MESSAGES = 50  # Máximo de mensajes antes de limpiar
        
        self.setup_tools()
        self.messages = [
            {"role": "system", "content": 
             """Eres un asistente útil que habla en el idioma que te preguntan y eres conciso con tus respuestas. Eres experto en ayudar con tareas relacionadas con el sistema de archivos y la ejecución de comandos en el terminal.
                Importante antes de usar herramianta para ejecutar comandos en el terminal o manipular archivos, asegúrate de conocer el sistema operativo del usuario con la herramienta get_system_os, para así adaptar los comandos y rutas de archivos.
                Puedes usar las siguientes herramientas para ayudar al usuario con tareas relacionadas con el sistema de archivos y la ejecución de comandos en el terminal, 
                para ello tienes que saber qué sistema operativo tiene el usuario y puedes saberlo utilizando la herramienta de ejecución de comandos para verificar el sistema operativo previamente.
                Cuando ejecutes un comando en el terminal, revisa la salida y si da error intenta corregir el comando y vuelve a intentarlo.
                Cuando uses los las herramientas, si hay alguna operativa que pueda causar daño al sistema (como borrados o modificar archivos), 
                primero pregunta al usuario para confirmarlo. No hace falta perdir permiso para operativas de búsquda o que muestren información.
                Intenta siempre usar las herramientas cuando sea posible y necesario.
                Si la respuesta que das es una lista intenta formatearla como una lista con viñetas, cuando tenga sentido. Si es una lista de un comando terminal intenta dejarla como salida de terminal.
                Cuando el usuario quiera salir, despídete cortésmente y díle que para salir puede escribir "salir", "exit", "bye" o "sayonara".
                Si el usuario quiere cambiar el modelo, puede escribir "/models" y se le mostrará la lista de modelos disponibles.
           
             """
             
            }
        ]
        self.TOOLS_FUNCTIONS = {
            "read_file": self.read_file,
            "edit_file": self.edit_file,
            "execute_terminal_command": self.execute_terminal_command,
            "get_system_os": self.get_system_os
        }
    
    def setup_tools(self):
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Lee el contenido de un archivo en una ruta especificada",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "La ruta del archivo a leer"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "Edita el contenido de un archivo reemplazando prev_text por new_text. Crea el archivo si no existe.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "La ruta del archivo a editar"
                            },
                            "prev_text": {
                                "type": "string",
                                "description": "El texto que se va a buscar para reemplazar (puede ser vacío para archivos nuevos)"
                            },
                            "new_text": {
                                "type": "string",
                                "description": "El texto que reemplazará a prev_text (o el texto para un archivo nuevo)"
                            }
                        },
                        "required": ["path", "new_text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_terminal_command",
                    "description": "Ejecuta un comando en el terminal del sistema operativo y devuelve el resultado, con ello puedes inspeccionar el sistema, listar directorios, copiar archivos, mover archivos, etc. También puedes crear y ejecutar scripts.",
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
                    "description": "Devuelve información sobre el sistema operativo donde corre el programa (plataforma, versión, arquitectura, hostname, python).",
                    "parameters": {
                        "type": "object",
                        "properties": {

                        },
                        "required": []
                    }
                }
            }
        ]
        
    #Herramienta: Leer archivos
    def read_file(self, path):
        print(" ⚙️  Herramienta llamada: read_file")
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
                # Limitar contenido si es muy grande
                if len(content) > 10000:
                    return content[:10000] + "\n... (contenido truncado, archivo muy grande)"
                return content
        except Exception as e:
            err = f"Error al leer el archivo {path}: {str(e)}"
            print(err)
            return err
        
    #Herramienta: Editar archivos
    def edit_file(self, path, prev_text, new_text):
        print(" ⚙️  Herramienta llamada: edit_file")
        try:
            existed = os.path.exists(path)
            if existed and prev_text:
                content = self.read_file(path)
                
                if prev_text not in content:
                    return f"Texto {prev_text} no encontrado en el archivo"
                
                content = content.replace(prev_text, new_text)
                
            else:
                #Crear o sobreescribir con el nuevo texto directamente
                dir_name = os.path.dirname(path)
                if dir_name:
                    os.makedirs(dir_name, exist_ok=True)
                
                content = new_text
                
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
                
            action = "editado" if existed and prev_text else "creado"
            return f"Archivo {path} {action} exitosamente"
        except Exception as e:
            err = f"Error al crear o editar el archivo {path}"
            print(err)
            return err
    
    def execute_terminal_command(self, command):
        print(" ⚙️  Herramienta llamada: execute_terminal_command")
        try:
            result = os.popen(command).read()
            # Limitar salida si es muy grande
            if len(result) > 5000:
                return result[:5000] + "\n... (salida truncada, resultado muy grande)"
            return result
        except Exception as e:
            err = f"Error al ejecutar el comando: {command}"
            print(err)
            return err

    def get_system_os(self):
        """Devuelve información básica del sistema operativo y entorno Python."""
        print("Herramienta llamada: get_system_os")
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
        """Ejecuta una herramienta y maneja errores."""
        if tool_name not in self.TOOLS_FUNCTIONS:
            return f"Error: Herramienta '{tool_name}' no encontrada"
        
        try:
            func = self.TOOLS_FUNCTIONS[tool_name]
            result = func(**tool_input)
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
                combined_outputs = []
                assistant_record = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": []
                }

                for tool_call in response.choices[0].message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_input = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        print(f"❌ Error al parsear argumentos JSON: {e}")
                        tool_input = {}

                    print(f"    - El modelo considera llamar a la herramienta {tool_name}")
                    print(f"    - Argumentos: {tool_input}")

                    # Ejecutar herramienta con manejo de errores
                    result = self.handle_tool_call(tool_name, tool_input)

                    # Registrar la intención de llamar herramientas en el mensaje assistant (metadatos)
                    assistant_record["tool_calls"].append({
                        "id": getattr(tool_call, 'id', None),
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": tool_call.function.arguments
                        }
                    })

                    # Formatear resultado y anexarlo al combinado
                    out_text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
                    header = f"== {tool_name} ==\n"
                    combined_outputs.append(header + out_text)

                # Añadir UNA sola entrada role:tool con todo el output combinado
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
                    print(f"Asistente: {output_text}")
                
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