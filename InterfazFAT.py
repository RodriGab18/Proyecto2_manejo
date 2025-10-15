import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextEdit, QLabel, QListWidget, QStyleFactory,
    QMessageBox, QCheckBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt
from FATSimulador import FATSimulador, Usuario

BEIGE_CLARO = "#DBAFA0"
ROSA_MALVA = "#BB8493"
MORADO_OSCURO_FONDO = "#704264"
MORADO_MUY_OSCURO = "#49243E"
TEXTO_CLARO = "#FFFFFF"
TEXTO_OSCURO = "#000000"


class VentanaLogin(QMainWindow):
    CREDENCIALES = {
        "usuario_prueba": ("1234", False),
        "admin": ("123", True)
    }

    def __init__(self):
        super().__init__()
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

        if usuario_str in self.CREDENCIALES:
            password_correcta, es_owner = self.CREDENCIALES[usuario_str]

            if password_str == password_correcta:
                usuario_logueado = Usuario(usuario_str, es_owner=es_owner)

                self.hide()
                self.ventana_principal = VentanaFAT(usuario_logueado)
                self.ventana_principal.show()
                return

        QMessageBox.critical(self, "Error de Login", "Credenciales incorrectas. Intente de nuevo.")


class VentanaFAT(QMainWindow):
    def __init__(self, usuario_logueado):
        super().__init__()
        self.simulador_fat = FATSimulador()
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
        if not self.usuario_actual.es_owner:
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

        archivos = self.simulador_fat.listar_archivos(mostrar_papelera=False)
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

            archivos = self.simulador_fat.listar_archivos(mostrar_papelera=True)
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

        mensaje, exito = self.simulador_fat.crear_archivo(nombre, contenido, owner_creacion)

        QMessageBox.information(self, "Creación de Archivo", mensaje)

        if exito:
            self.txt_nombre.clear()
            self.txt_contenido.clear()
            self.cargar_lista_activa()

    def mostrar_detalle(self, item, es_papelera):
        nombre_archivo = item.text()

        contenido, fat_entry = self.simulador_fat.abrir_archivo(nombre_archivo, self.usuario_actual.nombre)

        self.txt_contenido.setReadOnly(True)

        if fat_entry:
            permisos_usuarios = fat_entry.get('permisos_usuarios', {})
            permisos_usuario_actual = permisos_usuarios.get(self.usuario_actual.nombre,
                                                            {"lectura": False, "escritura": False})

            detalle = f"--- METADATOS FAT ---\n"
            detalle += f"Archivo: {fat_entry['nombre']}\n"
            detalle += f"Owner: {fat_entry['owner']}\n"
            detalle += f"ESTADO: {'EN PAPELERA' if fat_entry['papelera'] else 'ACTIVO'}\n"
            detalle += f"Tamaño: {fat_entry['caracteres_total']} caracteres\n"
            detalle += f"Modificación: {fat_entry['fecha_modificacion'][:19].replace('T', ' ')}\n"

            puede_escribir = False
            if self.usuario_actual.nombre == "admin":
                detalle += f"Tus Permisos: L=True, E=True (Admin Total)\n"
                puede_escribir = True
            else:
                detalle += f"Tus Permisos: L={permisos_usuario_actual['lectura']}, E={permisos_usuario_actual['escritura']}\n"
                if permisos_usuario_actual['escritura']:
                    puede_escribir = True

            if puede_escribir:
                self.txt_contenido.setReadOnly(False)
                self.txt_contenido.clear()
                self.txt_contenido.setPlaceholderText(
                    f"Ingrese el NUEVO contenido para modificar '{nombre_archivo}' aquí.")
            else:
                self.txt_contenido.setReadOnly(True)
                self.txt_contenido.setPlaceholderText("No tiene permiso de escritura para modificar este archivo.")

            if contenido and not isinstance(contenido, str):
                detalle += "\n--- CONTENIDO ---\n"
                detalle += contenido
            elif isinstance(contenido, str) and "Acceso denegado" in contenido:
                detalle += f"\n--- Contenido (Acceso Denegado) ---\n"
                detalle += contenido
            else:
                detalle += "\n--- No se pudo cargar el contenido ---\n"

            self.txt_detalle.setText(detalle)
        else:
            self.txt_detalle.setText("Error al cargar metadatos.")
            self.txt_contenido.setReadOnly(True)
            self.txt_contenido.setPlaceholderText("No hay archivo seleccionado.")

    def abrir_archivo(self):
        try:
            nombre_archivo = self.list_activa.currentItem().text()
        except:
            QMessageBox.warning(self, "Error", "Seleccione un archivo activo para abrir.")
            return

        contenido, fat_entry = self.simulador_fat.abrir_archivo(nombre_archivo, self.usuario_actual.nombre)

        if isinstance(contenido, str) and (
                "Acceso denegado" in contenido or "Error: Archivo no encontrado" in contenido):
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
            QMessageBox.warning(self, "Advertencia",
                                "Ingrese el nuevo contenido en el área de 'Contenido' a la izquierda.")
            return

        mensaje = self.simulador_fat.modificar_archivo(nombre_archivo, nuevo_contenido, self.usuario_actual.nombre)

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

        mensaje = self.simulador_fat.eliminar_archivo(nombre_archivo)

        QMessageBox.information(self, "Eliminación", mensaje)
        self.cargar_lista_activa()

    def recuperar_archivo(self):
        try:
            nombre_archivo = self.list_papelera.currentItem().text()
        except:
            QMessageBox.warning(self, "Error", "Seleccione un archivo de la papelera para recuperar.")
            return

        mensaje = self.simulador_fat.recuperar_archivo(nombre_archivo)

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

        if self.usuario_actual.nombre != "admin":
            QMessageBox.critical(self, "Error de Permisos",
                                 "Acceso Denegado: Solo el usuario 'admin' puede asignar o revocar permisos.")
            return

        mensaje = self.simulador_fat.asignar_permisos(
            nombre_archivo,
            usuario_a_modificar,
            lectura,
            escritura,
            owner=self.usuario_actual.nombre
        )

        QMessageBox.information(self, "Gestión de Permisos", mensaje)
        self.cargar_lista_activa()


if __name__ == "__main__":
    try:
        QApplication.setStyle(QStyleFactory.create("Fusion"))
    except:
        pass

    app = QApplication(sys.argv)

    login_window = VentanaLogin()
    login_window.show()

    sys.exit(app.exec())