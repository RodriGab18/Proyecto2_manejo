import os
import json
import uuid
from typing import Optional, Dict, Any, List
from InterfacesFAT import (
    RepositorioArchivos, AlmacenamientoBloques, 
    PoliticaPermisos, ServicioAutenticacion, Usuario
)

class RepositorioFATJson:
    def __init__(self, directorio: str = 'data/fat_table'):
        self.directorio = directorio
        os.makedirs(self.directorio, exist_ok=True)

    def _ruta(self, nombre: str) -> str:
        return os.path.join(self.directorio, f"{nombre}.json")

    def guardar(self, nombre: str, fat_entry: Dict[str, Any]) -> None:
        with open(self._ruta(nombre), 'w') as f:
            json.dump(fat_entry, f, indent=4)

    def buscar(self, nombre: str) -> Optional[Dict[str, Any]]:
        ruta = self._ruta(nombre)
        if not os.path.exists(ruta):
            return None
        with open(ruta, 'r') as f:
            return json.load(f)

    def listar(self, mostrar_papelera: bool = False) -> List[Dict[str, Any]]:
        archivos_listos = []
        for filename in os.listdir(self.directorio):
            if filename.endswith(".json"):
                ruta = os.path.join(self.directorio, filename)
                with open(ruta, 'r') as f:
                    fat_entry = json.load(f)
                    if fat_entry and fat_entry.get('papelera') == mostrar_papelera:
                        archivos_listos.append(fat_entry)
        return archivos_listos

    def borrar(self, nombre: str) -> bool:
        ruta = self._ruta(nombre)
        if os.path.exists(ruta):
            os.remove(ruta)
            return True
        return False


class AlmacenamientoBloquesJson:
    def __init__(self, directorio: str = 'data/blocks', block_size: int = 20):
        self.directorio = directorio
        self.block_size = block_size
        os.makedirs(self.directorio, exist_ok=True)

    def guardar_bloques(self, contenido: str, archivo_nombre: str) -> Optional[str]:
        if not contenido:
            # Manejo de archivo vacío
            bloques = [""]
        else:
            bloques = [contenido[i:i + self.block_size] for i in range(0, len(contenido), self.block_size)]

        primer_bloque_path = None
        bloque_paths = []

        for i, datos in enumerate(bloques):
            bloque_id = str(uuid.uuid4())
            ruta_bloque = os.path.join(self.directorio, f"{bloque_id}.json")
            bloque_paths.append(ruta_bloque)

            data_bloque = {
                "datos": datos,
                "siguiente_archivo": None,
                "eof": (i == len(bloques) - 1)
            }
            with open(ruta_bloque, 'w') as f:
                json.dump(data_bloque, f, indent=4)
            
            if i == 0:
                primer_bloque_path = ruta_bloque

        for i in range(len(bloque_paths) - 1):
            ruta_actual = bloque_paths[i]
            ruta_siguiente = bloque_paths[i + 1]
            with open(ruta_actual, 'r') as f:
                bloque = json.load(f)
            if bloque:
                bloque['siguiente_archivo'] = ruta_siguiente
                with open(ruta_actual, 'w') as f:
                    json.dump(bloque, f, indent=4)

        return primer_bloque_path

    def leer_bloques(self, referencia: str) -> str:
        contenido_completo = ""
        ruta_actual = referencia
        max_bloques = 1000
        bloques_leidos = 0

        while ruta_actual and bloques_leidos < max_bloques:
            if not os.path.exists(ruta_actual):
                break
            with open(ruta_actual, 'r') as f:
                bloque = json.load(f)
            
            if not bloque:
                break

            contenido_completo += bloque.get("datos", "")
            bloques_leidos += 1

            if bloque.get("eof"):
                break

            ruta_actual = bloque.get("siguiente_archivo")

        return contenido_completo

    def eliminar_bloques(self, referencia: str) -> None:
        ruta_a_eliminar = referencia
        while ruta_a_eliminar:
            if not os.path.exists(ruta_a_eliminar):
                break
            with open(ruta_a_eliminar, 'r') as f:
                bloque = json.load(f)
            if bloque:
                siguiente = bloque.get("siguiente_archivo")
                os.remove(ruta_a_eliminar)
                if bloque.get("eof"):
                    break
                ruta_a_eliminar = siguiente
            else:
                break


class PoliticaPermisosBasica:
    def __init__(self, admin_user: str = 'admin'):
        self.admin_user = admin_user

    def es_admin(self, usuario: str) -> bool:
        return usuario == self.admin_user

    def puede_leer(self, usuario: str, fat_entry: Dict[str, Any]) -> bool:
        if self.es_admin(usuario):
            return True
        permisos = fat_entry.get('permisos_usuarios', {}).get(usuario, {})
        return permisos.get('lectura', False)

    def puede_escribir(self, usuario: str, fat_entry: Dict[str, Any]) -> bool:
        if self.es_admin(usuario):
            return True
        permisos = fat_entry.get('permisos_usuarios', {}).get(usuario, {})
        return permisos.get('escritura', False)

    def puede_administrar(self, usuario: str, fat_entry: Dict[str, Any]) -> bool:
        if self.es_admin(usuario):
            return True
        return fat_entry.get('owner') == usuario


class AutenticadorBasico:
    def __init__(self):
        self.credenciales = {
            "usuario_prueba": ("1234", False),
            "admin": ("123", True)
        }

    def autenticar(self, nombre: str, password: str) -> Optional[Usuario]:
        if nombre in self.credenciales:
            password_correcta, es_owner = self.credenciales[nombre]
            if password == password_correcta:
                return Usuario(nombre, es_owner=es_owner)
        return None
