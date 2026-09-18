from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List
from InterfacesFAT import (
    LectorArchivos, EditorArchivos, GestorPapelera, GestorPermisos,
    RepositorioArchivos, AlmacenamientoBloques, PoliticaPermisos
)

class FATSimulador(LectorArchivos, EditorArchivos, GestorPapelera, GestorPermisos):
    def __init__(self, 
                 repositorio: RepositorioArchivos, 
                 almacenamiento: AlmacenamientoBloques, 
                 politica: PoliticaPermisos):
        self.repositorio = repositorio
        self.almacenamiento = almacenamiento
        self.politica = politica

    def crear_archivo(self, nombre: str, contenido: str, owner: str) -> Tuple[str, bool]:
        if self.repositorio.buscar(nombre):
            return f"Error: Ya existe un archivo llamado '{nombre}'.", False

        ruta_inicial_bloque = self.almacenamiento.guardar_bloques(contenido, nombre)

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

        self.repositorio.guardar(nombre, fat_entry)
        return f"Archivo '{nombre}' creado y FAT actualizado con {len(contenido)} caracteres.", True

    def listar_archivos(self, mostrar_papelera: bool = False) -> List[Dict[str, Any]]:
        return self.repositorio.listar(mostrar_papelera)

    def abrir_archivo(self, nombre_archivo: str, usuario: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        fat_entry = self.repositorio.buscar(nombre_archivo)

        if not fat_entry:
            return "Error: Archivo no encontrado.", None

        if not self.politica.puede_leer(usuario, fat_entry):
            return "Acceso denegado: No tiene permiso de lectura.", fat_entry

        contenido = self.almacenamiento.leer_bloques(fat_entry['ruta_o_nombre_inicial'])
        return contenido, fat_entry

    def modificar_archivo(self, nombre_archivo: str, nuevo_contenido: str, usuario: str) -> str:
        fat_entry = self.repositorio.buscar(nombre_archivo)

        if not fat_entry:
            return "Error: Archivo no encontrado."

        if not self.politica.puede_escribir(usuario, fat_entry):
            return "Acceso denegado: No tiene permiso de escritura."

        ruta_vieja_inicial = fat_entry['ruta_o_nombre_inicial']
        nueva_ruta_inicial = self.almacenamiento.guardar_bloques(nuevo_contenido, nombre_archivo)
        
        self.almacenamiento.eliminar_bloques(ruta_vieja_inicial)

        fat_entry['ruta_o_nombre_inicial'] = nueva_ruta_inicial
        fat_entry['caracteres_total'] = len(nuevo_contenido)
        fat_entry['fecha_modificacion'] = datetime.now().isoformat()
        
        self.repositorio.guardar(nombre_archivo, fat_entry)
        return f"Archivo '{nombre_archivo}' modificado exitosamente. Bloques antiguos eliminados."

    def eliminar_archivo(self, nombre_archivo: str) -> str:
        fat_entry = self.repositorio.buscar(nombre_archivo)
        if not fat_entry:
            return "Error: Archivo no encontrado."
        if fat_entry.get('papelera'):
            return "Advertencia: El archivo ya está en la papelera."

        fat_entry['papelera'] = True
        fat_entry['fecha_eliminacion'] = datetime.now().isoformat()
        self.repositorio.guardar(nombre_archivo, fat_entry)

        return f"Archivo '{nombre_archivo}' movido a la papelera."

    def recuperar_archivo(self, nombre_archivo: str) -> str:
        fat_entry = self.repositorio.buscar(nombre_archivo)
        if not fat_entry:
            return "Error: Archivo no encontrado."
        if not fat_entry.get('papelera'):
            return "Advertencia: El archivo no está en la papelera."

        fat_entry['papelera'] = False
        fat_entry['fecha_eliminacion'] = None
        self.repositorio.guardar(nombre_archivo, fat_entry)

        return f"Archivo '{nombre_archivo}' recuperado de la papelera."

    def asignar_permisos(self, nombre_archivo: str, usuario_objetivo: str, lectura: bool, escritura: bool, owner: str) -> str:
        fat_entry = self.repositorio.buscar(nombre_archivo)

        if not fat_entry:
            return "Error: Archivo no encontrado."

        if not self.politica.puede_administrar(owner, fat_entry):
            return "Acceso denegado: Solo el owner o el admin pueden modificar los permisos."

        permisos_usuarios = fat_entry.get('permisos_usuarios', {})
        permisos_usuarios[usuario_objetivo] = {"lectura": lectura, "escritura": escritura}

        fat_entry['permisos_usuarios'] = permisos_usuarios
        self.repositorio.guardar(nombre_archivo, fat_entry)

        return f"Permisos de '{nombre_archivo}' actualizados para '{usuario_objetivo}' exitosamente."