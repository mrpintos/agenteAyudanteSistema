import os
import json

class Agent:
    def __init__(self):
        self.setup_tools()
        self.messages = [
            {"role": "system", "content": 
             """Eres un asistente útil que habla en el idioma que te preguntan y eres conciso con tus respuestas.
                Puedes usar las siguientes herramientas para ayudar al usuario con tareas relacionadas con el sistema de archivos y la ejecución de comandos bash.
                Cuando uses los las herramientas, si hay alguna operativa que pueda causar daño al sistema (como borrados o modificar archivos), 
                primero pregunta al usuario para confirmarlo. No hace falta perdir permiso para operativas de búsquda o que muestren información.
                Intenta siempre usar las herramientas cuando sea posible y necesario.
                Si la respuesta que das es una lista intenta formatearla como una lista con viñetas.
                Cuando el usuario quiera salir, despídete cortésmente y díle que para salir puede escribir "salir", "exit", "bye" o "sayonara".
           
             """
             
            }
        ]
    
    def setup_tools(self):
        self.tools = [
         #   
         #   {
         #       "type": "function",
         #       "name": "list_files_in_dir",
         #       "description": "Lista los archivos que existen en un directorio dado (por defecto es el directorio actual)",
         #       "parameters": {
         #           "type": "object",
         #           "properties": {
         #               "directory": {
         #                   "type": "string",
         #                   "description": "Directorio para listar (opcional). Por defecto es el directorio actual"
         #               }
         #           },
         #           "required": []
         #       }
         #   },
            {
                "type": "function",
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
            },
            {
                "type": "function",
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
            },
            {
                "type": "function",
                "name": "execute_bash_command",
                "description": """Ejecuta un comando bash en el sistema operativo y devuelve el resultado, 
                con ello puedes inspeccionar el sistema, listar directorios, copiar archivos, mover archivos, etc. 
                También puedes crear y ejecutar scripts. Todo lo relacionado con el Sistema Operativo y la terminal.""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "El comando bash a ejecutar con sus argumentos si lo requiere"
                        }
                    },
                    "required": ["command"]
                }
            }
        ]
        
    #Definición de herramientas
    def list_files_in_dir(self, directory="."):
        print(" ⚙️  Herramienta llamada: list_files_in_dir")
        try:
            files = os.listdir(directory)
            
            #Asi lo deje en el video. En realidad allá se agrega a un
            #diccionario entonces no es necesario hacerlo aquí
            return {"files": files}
        except Exception as e:
            return {"error": str(e)}
        
    #Herramienta: Leer archivos
    def read_file(self, path):
        print(" ⚙️  Herramienta llamada: read_file")
        try:
            with open(path, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            err = f"Error al leer el archivo {path}"
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
    
    def execute_bash_command(self, command):
        print(" ⚙️  Herramienta llamada: execute_bash_command")
        try:
            result = os.popen(command).read()
            return result
        except Exception as e:
            err = f"Error al ejecutar el comando: {command}"
            print(err)
            return err

    def process_response(self, response):
        #True = si llama a una funcion. False = No hubo llamado.
        
        #Almacenar para historial
        self.messages += response.output
        
        for output in response.output:
            if output.type == "function_call":
                fn_name = output.name
                args = json.loads(output.arguments)
                
                print(f"    - El modelo considera llamar a la herramienta {fn_name}")
                print(f"    - Argumentos: {args}")
                
                if fn_name == "list_files_in_dir":
                    result = self.list_files_in_dir(**args)
                elif fn_name == "read_file":
                    result = self.read_file(**args)
                elif fn_name == "edit_file":
                    result = self.edit_file(**args)
                elif fn_name == "execute_bash_command":
                    result = self.execute_bash_command(**args)
                    
                #Agregar a la memoria la respuesta del llamado
                self.messages.append({
                    "type": "function_call_output",
                    "call_id": output.call_id,
                    "output": json.dumps({
                        #Así lo dejé en el video. Creo que queda mejor
                        #dejarlo como 'result', al aplicar ahora a las
                        #3 herramientas
                        "result": result
                    })
                })
                    
                return True
                
            elif output.type == "message":
                #print(f"Asistente: {output.content}")
                reply = "\n".join(part.text for part in output.content)
                print(f"Asistente: {reply}")
                
        return False