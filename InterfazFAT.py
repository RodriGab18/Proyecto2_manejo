import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextEdit, QLabel, QListWidget, QStyleFactory,
    QMessageBox, QCheckBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt

from InterfacesFAT import (
    Usuario, ServicioAutenticacion, LectorArchivos, EditorArchivos, 
    GestorPapelera, GestorPermisos, PoliticaPermisos
)
from InfraestructuraFAT import (
    RepositorioFATJson, AlmacenamientoBloquesJson, PoliticaPermisosBasica, AutenticadorBasico
)
from FATSimulador import FATSimulador

BEIGE_CLARO = "#DBAFA0"
ROSA_MALVA = "#BB8493"
MORADO_OSCURO_FONDO = "#704264"
MORADO_MUY_OSCURO = "#49243E"
TEXTO_CLARO = "#FFFFFF"
TEXTO_OSCURO = "#000000"


class FormateadorDetalleFAT:
    @staticmethod
    def formatear(fat_entry, contenido, usuario_actual, politica: PoliticaPermisos) -> tuple[str, bool]:
        if not fat_entry:
            return "Error al cargar metadatos.", False

        puede_escribir = politica.puede_escribir(usuario_actual.nombre, fat_entry)
        puede_leer = politica.puede_leer(usuario_actual.nombre, fat_entry)
        es_admin = politica.es_admin(usuario_actual.nombre)

        detalle = f"--- METADATOS FAT ---\n"
        detalle += f"Archivo: {fat_entry['nombre']}\n"
        detalle += f"Owner: {fat_entry['owner']}\n"
        detalle += f"ESTADO: {'EN PAPELERA' if fat_entry.get('papelera') else 'ACTIVO'}\n"
        detalle += f"Tamaño: {fat_entry.get('caracteres_total', 0)} caracteres\n"
        fecha_mod = fat_entry.get('fecha_modificacion', '')
        detalle += f"Modificación: {fecha_mod[:19].replace('T', ' ')}\n"

        if es_admin:
            detalle += f"Tus Permisos: L=True, E=True (Admin Total)\n"
        else:
            detalle += f"Tus Permisos: L={puede_leer}, E={puede_escribir}\n"

        if contenido and not isinstance(contenido, str):
            detalle += "\n--- CONTENIDO ---\n"
            detalle += contenido
        elif isinstance(contenido, str) and "Acceso denegado" in contenido:
            detalle += f"\n--- Contenido (Acceso Denegado) ---\n"
            detalle += contenido
        else:
            if not puede_leer:
                detalle += "\n--- No se pudo cargar el contenido (Sin permisos de lectura) ---\n"

        return detalle, puede_escribir


class VentanaLogin(QMainWindow):
    def __init__(self, servicio_autenticacion: ServicioAutenticacion, on_login_success):
        super().__init__()
        self.servicio_autenticacion = servicio_autenticacion
        self.on_login_success = on_login_success
        
        self.setWindowTitle("Sistema FAT - Iniciar Sesión")
        self.setGeometry(500, 300, 400, 250)
        self.setStyleSheet(self._get_login_style())

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.txt_usuario = QLineEdit()
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.btn_login = QPushButton("INICIAR SESIÓN")
        self.btn_login.setObjectName("BotonLogin")

        form_layout = QFormLayout()
        form_layout.addRow(QLabel("Usuario:"), self.txt_usuario)
        form_layout.addRow(QLabel("Contraseña:"), self.txt_password)

        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.btn_login)

        self.btn_login.clicked.connect(self.autenticar)

    def _get_login_style(self):
        return f"""
            QMainWindow {{ background-color: {MORADO_OSCURO_FONDO}; }}
            QWidget {{ color: {TEXTO_CLARO}; font-size: 10pt; }}
            QLabel {{ color: {TEXTO_CLARO}; }}
            QLineEdit {{
                border: 1px solid {ROSA_MALVA}; 
                padding: 8px; 
                background-color: {MORADO_MUY_OSCURO}; 
                color: {TEXTO_CLARO};
            }}
            QPushButton#BotonLogin {{
                background-color: {ROSA_MALVA}; color: {TEXTO_OSCURO}; border: none;
                padding: 12px; font-weight: bold; border-radius: 6px; margin-top: 15px;
            }}
            QPushButton#BotonLogin:hover {{ background-color: {BEIGE_CLARO}; }}
            QMessageBox {{ 
                background-color: {MORADO_OSCURO_FONDO}; 
                color: {TEXTO_CLARO}; 
            }}
        """

    def autenticar(self):
        usuario_str = self.txt_usuario.text().strip()
        password_str = self.txt_password.text()

        usuario_logueado = self.servicio_autenticacion.autenticar(usuario_str, password_str)

        if usuario_logueado:
            self.hide()
            self.on_login_success(usuario_logueado)
        else:
            QMessageBox.critical(self, "Error de Login", "Credenciales incorrectas. Intente de nuevo.")


class VentanaFAT(QMainWindow):
    def __init__(self, 
                 lector: LectorArchivos, 
                 editor: EditorArchivos, 
                 papelera: GestorPapelera, 
                 permisos: GestorPermisos, 
                 politica: PoliticaPermisos,
                 usuario_logueado: Usuario):
        super().__init__()
        self.lector = lector
        self.editor = editor
        self.papelera = papelera
        self.permisos = permisos
        self.politica = politica
        self.usuario_actual = usuario_logueado

        self.setWindowTitle(f"Simulador de Archivos FAT - Logueado como: {self.usuario_actual.nombre}")
        self.setGeometry(100, 100, 1100, 800)
        self.setStyleSheet(self.get_qss_style())

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        self.acciones_panel = self.crear_panel_acciones()
        main_layout.addWidget(self.acciones_panel, 1)

        self.vistas_panel = self.crear_panel_vistas()
        main_layout.addWidget(self.vistas_panel, 2)

        self.aplicar_restricciones_rol()
        self.cargar_lista_activa()

        self.btn_crear.clicked.connect(self.crear_archivo)
        self.list_activa.itemClicked.connect(lambda item: self.mostrar_detalle(item, es_papelera=False))
        self.list_papelera.itemClicked.connect(lambda item: self.mostrar_detalle(item, es_papelera=True))

        self.btn_abrir.clicked.connect(self.abrir_archivo)
        self.btn_modificar.clicked.connect(self.modificar_archivo_ui)
        self.btn_eliminar.clicked.connect(self.eliminar_archivo)
        self.btn_listar_papelera.clicked.connect(lambda: self.cargar_lista_papelera(True))
        self.btn_recuperar.clicked.connect(self.recuperar_archivo)
        self.btn_asignar_permisos.clicked.connect(self.asignar_permisos_ui)

    def aplicar_restricciones_rol(self):
        # Utilizamos la política para decidir qué mostrar
        es_admin = self.politica.es_admin(self.usuario_actual.nombre)
        if not es_admin:
            self.grp_control.hide()
            self.grp_permisos.hide()
            self.btn_crear.setDisabled(True)
            self.txt_nombre.setReadOnly(True)
            self.grp_crear.setTitle("1. Crear Archivo (Solo Admin)")
        else:
            self.txt_contenido.setReadOnly(False)
            self.txt_contenido.setPlaceholderText("Ingrese el contenido inicial aquí si crea un archivo.")

    def get_qss_style(self):
        return f"""
            QMainWindow {{ background-color: {MORADO_OSCURO_FONDO}; }} 
            QWidget {{ color: {TEXTO_CLARO}; font-size: 10pt; }}
            QLabel {{ font-weight: bold; margin-bottom: 5px; color: {TEXTO_CLARO}; }}
            QGroupBox {{ 
                border: 2px solid {ROSA_MALVA}; 
                margin-top: 15px; 
                padding: 10px;
                background-color: {MORADO_MUY_OSCURO}; 
                color: {TEXTO_CLARO};
            }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; color: {BEIGE_CLARO}; }}
            QListWidget, QTextEdit, QLineEdit {{
                border: 1px solid {ROSA_MALVA}; 
                padding: 8px; 
                background-color: {MORADO_MUY_OSCURO}; 
                color: {TEXTO_CLARO};
                selection-background-color: {ROSA_MALVA};
                selection-color: {TEXTO_OSCURO};
            }}
            QListWidget {{ padding: 0px; }} 
            QPushButton {{
                background-color: {ROSA_MALVA}; color: {TEXTO_OSCURO}; border: none;
                padding: 12px; font-weight: bold; border-radius: 6px; margin-bottom: 5px;
            }}
            QPushButton:hover {{ background-color: {BEIGE_CLARO}; color: {TEXTO_OSCURO}; }}
            #BotonCrear {{ background-color: {ROSA_MALVA}; color: {TEXTO_OSCURO}; }}
            #BotonCrear:hover {{ background-color: {BEIGE_CLARO}; }}
            #BotonEliminar {{ background-color: {MORADO_OSCURO_FONDO}; color: {TEXTO_CLARO}; border: 1px solid {BEIGE_CLARO}; }}
            #BotonEliminar:hover {{ background-color: {ROSA_MALVA}; }}
            #BotonListarPapelera {{ background-color: {MORADO_MUY_OSCURO}; color: {TEXTO_CLARO}; border: 1px solid {ROSA_MALVA};}} 
            #BotonListarPapelera:hover {{ background-color: {ROSA_MALVA}; }}
            #BotonRecuperar {{ background-color: {BEIGE_CLARO}; color: {TEXTO_OSCURO}; }} 
            #BotonRecuperar:hover {{ background-color: {ROSA_MALVA}; }}
            QCheckBox {{ color: {TEXTO_CLARO}; }}
            QMessageBox {{ background-color: {MORADO_MUY_OSCURO}; color: {TEXTO_CLARO}; }}
            QMessageBox QPushButton {{ background-color: {ROSA_MALVA}; color: {TEXTO_OSCURO}; }}
        """

    def crear_panel_acciones(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        self.grp_control = QGroupBox("Control de Sesión (ADMIN ONLY)")
        lay_control = QHBoxLayout(self.grp_control)
        self.lbl_usuario = QLabel(f"Usuario Logueado: {self.usuario_actual.nombre}")
        lay_control.addWidget(self.lbl_usuario)
        layout.addWidget(self.grp_control)

        self.grp_crear = QGroupBox("1. Crear Archivo")
        lay_crear = QVBoxLayout(self.grp_crear)
        lay_crear.addWidget(QLabel("Nombre del Archivo:"))
        self.txt_nombre = QLineEdit()
        lay_crear.addWidget(self.txt_nombre)
        lay_crear.addWidget(QLabel("Contenido:"))
        self.txt_contenido = QTextEdit()
        self.txt_contenido.setMinimumHeight(150)
        lay_crear.addWidget(self.txt_contenido)
        self.btn_crear = QPushButton("CREAR ARCHIVO")
        self.btn_crear.setObjectName("BotonCrear")
        lay_crear.addWidget(self.btn_crear)
        layout.addWidget(self.grp_crear)

        self.grp_permisos = QGroupBox("2. Gestión de Permisos (ADMIN ONLY)")
        lay_permisos = QVBoxLayout(self.grp_permisos)
        lay_permisos.addWidget(QLabel("Seleccionar Archivo:"))
        self.list_permisos_archivo = QListWidget()
        self.list_permisos_archivo.setMinimumHeight(100)
        self.list_permisos_archivo.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        lay_permisos.addWidget(self.list_permisos_archivo)

        lay_permisos.addWidget(QLabel("Seleccionar Usuario Objetivo:"))
        self.list_usuario_permisos = QListWidget()
        self.list_usuario_permisos.setMinimumHeight(50)
        self.list_usuario_permisos.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.list_usuario_permisos.addItem("usuario_prueba")
        lay_permisos.addWidget(self.list_usuario_permisos)

        self.chk_lectura = QCheckBox("Permiso de Lectura (Abrir)")
        self.chk_escritura = QCheckBox("Permiso de Escritura (Modificar)")
        lay_permisos.addWidget(self.chk_lectura)
        lay_permisos.addWidget(self.chk_escritura)
        self.btn_asignar_permisos = QPushButton("ASIGNAR / REVOCAR PERMISOS")
        lay_permisos.addWidget(self.btn_asignar_permisos)
        layout.addWidget(self.grp_permisos)

        layout.addStretch(1)
        return panel

    def crear_panel_vistas(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        layout.addWidget(QLabel("3. Archivos Activos del Sistema FAT:"))
        self.list_activa = QListWidget()
        self.list_activa.setMinimumHeight(120)
        layout.addWidget(self.list_activa)

        btn_layout_activa = QHBoxLayout()
        self.btn_abrir = QPushButton("ABRIR")
        self.btn_modificar = QPushButton("MODIFICAR")
        self.btn_eliminar = QPushButton("ELIMINAR")
        self.btn_eliminar.setObjectName("BotonEliminar")
        btn_layout_activa.addWidget(self.btn_abrir)
        btn_layout_activa.addWidget(self.btn_modificar)
        btn_layout_activa.addWidget(self.btn_eliminar)
        layout.addLayout(btn_layout_activa)

        self.btn_listar_papelera = QPushButton("MOSTRAR PAPELERA")
        self.btn_listar_papelera.setObjectName("BotonListarPapelera")
        layout.addWidget(self.btn_listar_papelera)
        self.list_papelera = QListWidget()
        self.list_papelera.setMinimumHeight(80)
        self.list_papelera.hide()
        layout.addWidget(self.list_papelera)

        self.btn_recuperar = QPushButton("RECUPERAR ARCHIVO SELECCIONADO")
        self.btn_recuperar.setObjectName("BotonRecuperar")
        self.btn_recuperar.hide()
        layout.addWidget(self.btn_recuperar)

        layout.addWidget(QLabel("4. Detalle y Contenido del Archivo Seleccionado:"))
        self.txt_detalle = QTextEdit()
        self.txt_detalle.setReadOnly(True)
        self.txt_detalle.setMinimumHeight(200)
        layout.addWidget(self.txt_detalle)

        return panel

    def cargar_lista_activa(self):
        self.list_activa.clear()
        self.list_permisos_archivo.clear()
        self.list_papelera.clearSelection()
        self.list_papelera.clear()
        self.cargar_lista_papelera(False)

        archivos = self.lector.listar_archivos(mostrar_papelera=False)
        for fat_entry in archivos:
            nombre = fat_entry['nombre']
            self.list_activa.addItem(nombre)
            self.list_permisos_archivo.addItem(nombre)

    def cargar_lista_papelera(self, mostrar=False):
        if mostrar:
            self.list_papelera.show()
            self.btn_recuperar.show()
            self.list_papelera.clear()
            self.list_activa.clearSelection()
            self.list_permisos_archivo.clearSelection()
            self.txt_detalle.clear()

            archivos = self.lector.listar_archivos(mostrar_papelera=True)
            for fat_entry in archivos:
                self.list_papelera.addItem(fat_entry['nombre'])

            self.btn_listar_papelera.setText("Ocultar Papelera")
            try:
                self.btn_listar_papelera.clicked.disconnect()
            except:
                pass
            self.btn_listar_papelera.clicked.connect(lambda: self.cargar_lista_papelera(False))
        else:
            self.list_papelera.hide()
            self.btn_recuperar.hide()
            self.btn_listar_papelera.setText("MOSTRAR PAPELERA")
            try:
                self.btn_listar_papelera.clicked.disconnect()
            except:
                pass
            self.btn_listar_papelera.clicked.connect(lambda: self.cargar_lista_papelera(True))

    def crear_archivo(self):
        nombre = self.txt_nombre.text().strip()
        contenido = self.txt_contenido.toPlainText()

        owner_creacion = self.usuario_actual.nombre

        mensaje, exito = self.editor.crear_archivo(nombre, contenido, owner_creacion)
        QMessageBox.information(self, "Creación de Archivo", mensaje)

        if exito:
            self.txt_nombre.clear()
            self.txt_contenido.clear()
            self.cargar_lista_activa()

    def mostrar_detalle(self, item, es_papelera):
        nombre_archivo = item.text()
        contenido, fat_entry = self.lector.abrir_archivo(nombre_archivo, self.usuario_actual.nombre)

        detalle, puede_escribir = FormateadorDetalleFAT.formatear(
            fat_entry, contenido, self.usuario_actual, self.politica
        )

        self.txt_detalle.setText(detalle)

        if puede_escribir:
            self.txt_contenido.setReadOnly(False)
            self.txt_contenido.clear()
            self.txt_contenido.setPlaceholderText(f"Ingrese el NUEVO contenido para modificar '{nombre_archivo}' aquí.")
        else:
            self.txt_contenido.setReadOnly(True)
            self.txt_contenido.setPlaceholderText("No tiene permiso de escritura para modificar este archivo.")

    def abrir_archivo(self):
        try:
            nombre_archivo = self.list_activa.currentItem().text()
        except:
            QMessageBox.warning(self, "Error", "Seleccione un archivo activo para abrir.")
            return

        contenido, fat_entry = self.lector.abrir_archivo(nombre_archivo, self.usuario_actual.nombre)

        if isinstance(contenido, str) and ("Acceso denegado" in contenido or "Error: Archivo no encontrado" in contenido):
            QMessageBox.critical(self, "Error de Apertura", contenido)
        elif isinstance(contenido, str):
            QMessageBox.information(self, f"Contenido de '{nombre_archivo}'", contenido, QMessageBox.StandardButton.Ok)
        else:
            QMessageBox.critical(self, "Error de Apertura", "Fallo desconocido al abrir el archivo.")

    def modificar_archivo_ui(self):
        try:
            nombre_archivo = self.list_activa.currentItem().text()
        except:
            QMessageBox.warning(self, "Error", "Seleccione un archivo activo para modificar.")
            return

        nuevo_contenido = self.txt_contenido.toPlainText()
        if not nuevo_contenido:
            QMessageBox.warning(self, "Advertencia", "Ingrese el nuevo contenido en el área de 'Contenido' a la izquierda.")
            return

        mensaje = self.editor.modificar_archivo(nombre_archivo, nuevo_contenido, self.usuario_actual.nombre)

        if "Acceso denegado" in mensaje:
            QMessageBox.critical(self, "Modificación Denegada", mensaje)
        else:
            QMessageBox.information(self, "Modificación Exitosa", mensaje)

        self.cargar_lista_activa()
        self.txt_contenido.clear()

    def eliminar_archivo(self):
        try:
            nombre_archivo = self.list_activa.currentItem().text()
        except:
            QMessageBox.warning(self, "Error", "Seleccione un archivo activo para mover a la papelera.")
            return

        mensaje = self.papelera.eliminar_archivo(nombre_archivo)
        QMessageBox.information(self, "Eliminación", mensaje)
        self.cargar_lista_activa()

    def recuperar_archivo(self):
        try:
            nombre_archivo = self.list_papelera.currentItem().text()
        except:
            QMessageBox.warning(self, "Error", "Seleccione un archivo de la papelera para recuperar.")
            return

        mensaje = self.papelera.recuperar_archivo(nombre_archivo)
        QMessageBox.information(self, "Recuperación", mensaje)
        self.cargar_lista_activa()
        self.cargar_lista_papelera(True)

    def asignar_permisos_ui(self):
        try:
            nombre_archivo = self.list_permisos_archivo.currentItem().text()
        except:
            QMessageBox.warning(self, "Error", "Seleccione un archivo de la lista de gestión de permisos.")
            return

        try:
            usuario_a_modificar = self.list_usuario_permisos.currentItem().text()
        except:
            QMessageBox.warning(self, "Error", "Seleccione un usuario objetivo de la lista.")
            return

        lectura = self.chk_lectura.isChecked()
        escritura = self.chk_escritura.isChecked()

        if not self.politica.es_admin(self.usuario_actual.nombre):
            QMessageBox.critical(self, "Error de Permisos",
                                 "Acceso Denegado: Solo el usuario 'admin' puede asignar o revocar permisos.")
            return

        mensaje = self.permisos.asignar_permisos(
            nombre_archivo,
            usuario_a_modificar,
            lectura,
            escritura,
            owner=self.usuario_actual.nombre
        )

        QMessageBox.information(self, "Gestión de Permisos", mensaje)
        self.cargar_lista_activa()


def main():
    try:
        QApplication.setStyle(QStyleFactory.create("Fusion"))
    except:
        pass

    app = QApplication(sys.argv)

    # Inyección de dependencias (Composición / Assembler)
    repositorio = RepositorioFATJson()
    almacenamiento = AlmacenamientoBloquesJson()
    politica = PoliticaPermisosBasica()
    autenticador = AutenticadorBasico()

    servicio_fat = FATSimulador(repositorio, almacenamiento, politica)

    ventana_principal = None

    def on_login(usuario_logueado):
        nonlocal ventana_principal
        ventana_principal = VentanaFAT(
            lector=servicio_fat,
            editor=servicio_fat,
            papelera=servicio_fat,
            permisos=servicio_fat,
            politica=politica,
            usuario_logueado=usuario_logueado
        )
        ventana_principal.show()

    login_window = VentanaLogin(autenticador, on_login)
    login_window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()