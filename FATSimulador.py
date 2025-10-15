import os
import json
from datetime import datetime
import uuid

BLOCK_SIZE = 20
FAT_DIR = 'data/fat_table'
BLOCKS_DIR = 'data/blocks'
ADMIN_USER = 'admin'


class Usuario:
    def __init__(self, nombre, es_owner=False):
        self.nombre = nombre
        self.es_owner = es_owner


class FATSimulador:
    def __init__(self):
        os.makedirs(FAT_DIR, exist_ok=True)
        os.makedirs(BLOCKS_DIR, exist_ok=True)

    def _guardar_json(self, ruta_completa, data):
        with open(ruta_completa, 'w') as f:
            json.dump(data, f, indent=4)

    def _cargar_json(self, ruta_completa):
        if not os.path.exists(ruta_completa):
            return None
        with open(ruta_completa, 'r') as f:
            return json.load(f)

    def _eliminar_archivo_fisico(self, ruta_completa):
        if os.path.exists(ruta_completa):
            os.remove(ruta_completa)
            return True
        return False

    def _generar_bloques(self, contenido, archivo_nombre):
        bloques = [contenido[i:i + BLOCK_SIZE]
                   for i in range(0, len(contenido), BLOCK_SIZE)]

        primer_bloque_path = None
        bloque_paths = []

        for i, datos in enumerate(bloques):
            bloque_id = str(uuid.uuid4())
            ruta_bloque = os.path.join(BLOCKS_DIR, f"{bloque_id}.json")
            bloque_paths.append(ruta_bloque)

            data_bloque = {
                "datos": datos,
                "siguiente_archivo": None,
                "eof": (i == len(bloques) - 1)
            }
            self._guardar_json(ruta_bloque, data_bloque)
            if i == 0:
                primer_bloque_path = ruta_bloque

        for i in range(len(bloque_paths) - 1):
            ruta_actual = bloque_paths[i]
            ruta_siguiente = bloque_paths[i + 1]
            bloque = self._cargar_json(ruta_actual)
            if bloque:
                bloque['siguiente_archivo'] = ruta_siguiente
                self._guardar_json(ruta_actual, bloque)

        return primer_bloque_path

    def _obtener_contenido_completo(self, ruta_inicial_bloque):
        contenido_completo = ""
        ruta_actual = ruta_inicial_bloque
        max_bloques = 1000
        bloques_leidos = 0

        while ruta_actual and bloques_leidos < max_bloques:
            bloque = self._cargar_json(ruta_actual)
            if not bloque:
                break

            contenido_completo += bloque.get("datos", "")
            bloques_leidos += 1

            if bloque.get("eof"):
                break

            ruta_actual = bloque.get("siguiente_archivo")

        return contenido_completo

    def crear_archivo(self, nombre, contenido, owner=ADMIN_USER):
        ruta_fat_check = os.path.join(FAT_DIR, f"{nombre}.json")
        if os.path.exists(ruta_fat_check):
            return f"Error: Ya existe un archivo llamado '{nombre}'.", False

        ruta_inicial_bloque = self._generar_bloques(contenido, nombre)

        if not ruta_inicial_bloque:
            return "Error al generar bloques de datos.", False

        fecha_actual = datetime.now().isoformat()

        fat_entry = {
            "nombre": nombre,
            "ruta_o_nombre_inicial": ruta_inicial_bloque,
            "papelera": False,
            "caracteres_total": len(contenido),
            "fecha_creacion": fecha_actual,
            "fecha_modificacion": fecha_actual,
            "fecha_eliminacion": None,
            "owner": owner,
            "permisos_usuarios": {
                owner: {"lectura": True, "escritura": True},
            }
        }

        ruta_fat = os.path.join(FAT_DIR, f"{nombre}.json")
        self._guardar_json(ruta_fat, fat_entry)

        return f"Archivo '{nombre}' creado y FAT actualizado con {len(contenido)} caracteres.", True

    def listar_archivos(self, mostrar_papelera=False):
        archivos_listos = []
        for filename in os.listdir(FAT_DIR):
            if filename.endswith(".json"):
                fat_entry = self._cargar_json(os.path.join(FAT_DIR, filename))
                if fat_entry and fat_entry.get('papelera') == mostrar_papelera:
                    archivos_listos.append(fat_entry)
        return archivos_listos

    def abrir_archivo(self, nombre_archivo, usuario):
        ruta_fat = os.path.join(FAT_DIR, f"{nombre_archivo}.json")
        fat_entry = self._cargar_json(ruta_fat)

        if not fat_entry:
            return "Error: Archivo no encontrado.", None

        if usuario == ADMIN_USER:
            contenido = self._obtener_contenido_completo(fat_entry['ruta_o_nombre_inicial'])
            return contenido, fat_entry

        permisos_usuarios = fat_entry.get('permisos_usuarios', {})
        usuario_permisos = permisos_usuarios.get(usuario, {"lectura": False, "escritura": False})

        if not usuario_permisos.get('lectura', False):
            return "Acceso denegado: No tiene permiso de lectura.", fat_entry

        contenido = self._obtener_contenido_completo(fat_entry['ruta_o_nombre_inicial'])

        return contenido, fat_entry

    def modificar_archivo(self, nombre_archivo, nuevo_contenido, usuario):
        ruta_fat = os.path.join(FAT_DIR, f"{nombre_archivo}.json")
        fat_entry = self._cargar_json(ruta_fat)

        if not fat_entry:
            return "Error: Archivo no encontrado."

        if usuario != ADMIN_USER:
            permisos_usuarios = fat_entry.get('permisos_usuarios', {})
            usuario_permisos = permisos_usuarios.get(usuario, {"lectura": False, "escritura": False})

            if not usuario_permisos.get('escritura', False):
                return "Acceso denegado: No tiene permiso de escritura."

        ruta_vieja_inicial = fat_entry['ruta_o_nombre_inicial']

        nueva_ruta_inicial = self._generar_bloques(nuevo_contenido, nombre_archivo)

        ruta_a_eliminar = ruta_vieja_inicial
        while ruta_a_eliminar:
            bloque = self._cargar_json(ruta_a_eliminar)
            if bloque:
                siguiente = bloque.get("siguiente_archivo")
                self._eliminar_archivo_fisico(ruta_a_eliminar)
                if bloque.get("eof"):
                    break
                ruta_a_eliminar = siguiente
            else:
                break

        fat_entry['ruta_o_nombre_inicial'] = nueva_ruta_inicial
        fat_entry['caracteres_total'] = len(nuevo_contenido)
        fat_entry['fecha_modificacion'] = datetime.now().isoformat()
        self._guardar_json(ruta_fat, fat_entry)

        return f"Archivo '{nombre_archivo}' modificado exitosamente. Bloques antiguos eliminados."

    def eliminar_archivo(self, nombre_archivo):
        ruta_fat = os.path.join(FAT_DIR, f"{nombre_archivo}.json")
        fat_entry = self._cargar_json(ruta_fat)
        if not fat_entry:
            return "Error: Archivo no encontrado."
        if fat_entry['papelera']:
            return "Advertencia: El archivo ya está en la papelera."

        fat_entry['papelera'] = True
        fat_entry['fecha_eliminacion'] = datetime.now().isoformat()
        self._guardar_json(ruta_fat, fat_entry)

        return f"Archivo '{nombre_archivo}' movido a la papelera."

    def recuperar_archivo(self, nombre_archivo):
        ruta_fat = os.path.join(FAT_DIR, f"{nombre_archivo}.json")
        fat_entry = self._cargar_json(ruta_fat)
        if not fat_entry:
            return "Error: Archivo no encontrado."
        if not fat_entry['papelera']:
            return "Advertencia: El archivo no está en la papelera."

        fat_entry['papelera'] = False
        fat_entry['fecha_eliminacion'] = None
        self._guardar_json(ruta_fat, fat_entry)

        return f"Archivo '{nombre_archivo}' recuperado de la papelera."

    def asignar_permisos(self, nombre_archivo, usuario_objetivo, lectura, escritura, owner=ADMIN_USER):
        ruta_fat = os.path.join(FAT_DIR, f"{nombre_archivo}.json")
        fat_entry = self._cargar_json(ruta_fat)

        if not fat_entry:
            return "Error: Archivo no encontrado."

        if owner != fat_entry.get('owner') and owner != ADMIN_USER:
            return "Acceso denegado: Solo el owner o el admin pueden modificar los permisos."

        permisos_usuarios = fat_entry.get('permisos_usuarios', {})
        permisos_usuarios[usuario_objetivo] = {"lectura": lectura, "escritura": escritura}

        fat_entry['permisos_usuarios'] = permisos_usuarios
        self._guardar_json(ruta_fat, fat_entry)

        return f"Permisos de '{nombre_archivo}' actualizados para '{usuario_objetivo}' exitosamente."