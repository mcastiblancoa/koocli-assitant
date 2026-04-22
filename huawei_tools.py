import os
import subprocess
import json
from langchain_core.tools import tool

@tool
def run_koocli_command(service: str, operation: str, params: dict = None) -> str:
    """
    Ejecuta un comando de KooCLI (hcloud) de Huawei Cloud.
    Usa esto para interactuar con Huawei Cloud en lugar de llamadas REST manuales.
    
    Args:
        service (str): El componente o servicio de Huawei Cloud, ej. 'ecs', 'vpc', 'ces'.
        operation (str): La operación de KooCLI a realizar, ej. 'ListCloudServers', 'CreateVpc'.
        params (dict, opcional): Diccionario con los parámetros específicos del comando.
                                 Ejemplo: {"limit": 1, "name": "mi-server"}.
                                 Nota: el project_id y credenciales se inyectan automáticamente.
        
    Returns:
        str: La salida (stdout o stderr) de la ejecución de KooCLI.
    """
    ak = os.getenv("HUAWEI_AK")
    sk = os.getenv("HUAWEI_SK")
    project_id = os.getenv("HUAWEI_PROJECT_ID")
    region = os.getenv("HUAWEI_REGION")
    
    if not ak or not sk or not region:
        return "Error: Faltan credenciales de Huawei Cloud (HUAWEI_AK, HUAWEI_SK, HUAWEI_REGION) en el .env"

    # Localizar hcloud de forma absoluta porque la variable PATH en VSCode a menudo 
    # no está actualizada tras una instalación reciente.
    import shutil
    hcloud_path = shutil.which("hcloud")
    if not hcloud_path:
        # Fallback a la ruta actual detectada en tu máquina
        hcloud_path = r"C:\users\nicol\Downloads\huaweicloud-cli-windows-amd64\hcloud.exe"

    cmd = [f'"{hcloud_path}"', service, operation]
    
    if params:
        for key, value in params.items():
            # Support for checking if the region was locally overridden in the prompt
            if key == "cli-region" or key == "region":
                region = value
                continue  # KooCLI ya usa el extend de región global, no necesitamos añadirlo aquí para evitar redundancias
            
            # En KooCLI, las operaciones de creación (POST) suelen recibir el body en formato JSON string escapado
            # Sin embargo, si al modelo se le pide enviar diccionarios, subprocess.run en Windows puede fallar al escapar comillas en parámetros con espacios o llaves
            # Usaremos una forma segura de enviar parámetros JSON en la línea de comando.
            if isinstance(value, (dict, list)):
                # Convertimos a string sin espacios extra y escapamos comillas en windows
                json_str = json.dumps(value, separators=(',', ':'))
                # Windows cmd requiere " " para strings con llaves/comillas y escapar " internos como \"
                escaped_json = json_str.replace('"', '\\"')
                cmd.append(f'--{key}="{escaped_json}"')
            else:
                cmd.append(f'--{key}="{str(value)}"')
                
    # Inyectar autenticación mediante variables de CLI de KooCLI
    cmd.extend([
        f"--cli-access-key={ak}",
        f"--cli-secret-key={sk}",
        f"--cli-region={region}"
    ])
    
    # Mapeo de Project IDs por región para evitar errores IAM APIGW.0301
    PROJECT_IDS = {
        "af-north-1": "ffd9e2abbbac4f888abd9f08b18dbc3d",
        "ap-southeast-1": "1724bd3fa7f745f79110f3ce49128ecb",
        "ap-southeast-3": "c03f2d01969044fc85baef46ba86a6ec",
        "cn-north-4": "a24fcb85b2204db7b2a90e48ebda08f5",
        "cn-south-1": "8358450edaa3433294d4f21fb22e5d3f",
        "la-north-2": "5785afdda6384c71ba92e8dd741b6ff8",
        "la-south-2": "ddee7698ac56487a9b6248f3567af49a",
        "me-east-1": "019dacb4116c733bbc10896f621443fe",
        "na-mexico-1": "4fde7221d82b4f7ca6b02ed0ca52d8b9",
        "sa-brazil-1": "b2ff269b26854f6ab80be16b4a206993"
    }
    
    # Determina el project_id real evaluando primero el diccionario local, o en su defecto el .env
    actual_project_id = PROJECT_IDS.get(region, project_id)

    # Inyectar project_id automáticamente si está disponible, es un parám común
    if actual_project_id and params and "project_id" not in params:
        cmd.append(f"--project_id={actual_project_id}")

    try:
        # Ejecutar el comando localmente. En Windows a menudo los comandos globales 
        # instalados por usuario (como hcloud.exe o .cmd) requieren shell=True para ser encontrados.
        cmd_str = " ".join(cmd)
        result = subprocess.run(cmd_str, capture_output=True, text=True, check=False, shell=True)
        
        output = result.stdout if result.returncode == 0 else result.stderr
        
        # Limitar la salida para no exceder el tamaño máximo de contexto del LLM
        max_length = 20000 
        if len(output) > max_length:
            output = output[:max_length] + f"\n\n...[ADVERTENCIA: La salida era muy larga y fue truncada a {max_length} caracteres. Sugiere al usuario usar filtros o parámetros de busqueda]..."

        if result.returncode == 0:
            return f"Éxito:\n{output}"
        else:
            return f"Error (Code {result.returncode}):\n{output}"
    except FileNotFoundError:
        return "Error crítico: El ejecutable de KooCLI ('hcloud') no está instalado o no se encuentra en el PATH del sistema operativo. Instala KooCLI primero."
    except Exception as e:
        return f"Error inesperado ejecutando hcloud: {str(e)}"
