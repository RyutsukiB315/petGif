import sys
import os
import shutil
from datetime import datetime
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QSystemTrayIcon, QMenu, QAction

# -----------------------------------------------------------------------------------
# FONCTION POUR LES RESSOURCES INCLUSES DANS L'EXE
# -----------------------------------------------------------------------------------
def resource_path(relative_path):
    """Chemin correct pour PyInstaller (lecture seule)."""
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

# -----------------------------------------------------------------------------------
# FONCTION POUR LES FICHIERS DE CONFIGURATION UTILISATEUR (MODIFIABLES)
# -----------------------------------------------------------------------------------
def user_config_path(filename):
    """Retourne le chemin du fichier de config modifiable, crée config_user/ si besoin."""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")
    folder = os.path.join(base_path, "config_user")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, filename)

# -----------------------------------------------------------------------------------
# Chemins
# -----------------------------------------------------------------------------------
GIF_FOLDER = resource_path("gif")  # GIF inclus
LAST_GIF_FILE = user_config_path("last_gif.txt")  # modifiable
CONFIG_FILE = user_config_path("last_gif_config.txt")  # modifiable
os.makedirs(GIF_FOLDER, exist_ok=True)

# -----------------------------------------------------------------------------------
# Classe principale
# -----------------------------------------------------------------------------------
class GifWindow(QtWidgets.QLabel):
    NORMAL_FPS = 25  # vitesse normale pour calcul speed_percent

    def __init__(self):
        # Widget parent invisible pour ne pas montrer d'icône
        self.fake_parent = QtWidgets.QWidget()
        self.fake_parent.setWindowFlags(QtCore.Qt.Tool)
        self.fake_parent.hide()

        super().__init__(self.fake_parent)
        self.setWindowFlags(
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.Tool
        )
        self.setAcceptDrops(True)

        self.gif = None
        self.fps = 25
        self.zoom_percent = 100
        self.base_size = None
        self.setText("Drag GIF here")
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showMenu)
        self.build_tray_menu()
        self.start_pos = None

        # Charger dernier GIF si possible
        self.load_last_gif()

    # -----------------------------------------------------------------------------------
    # Sauvegarde config
    # -----------------------------------------------------------------------------------
    def save_config(self, path):
        pos = self.pos()
        filename = os.path.basename(path)
        with open(CONFIG_FILE, "w") as f:
            f.write(f"{filename}\n")
            f.write(f"{self.fps}\n")
            f.write(f"{self.zoom_percent}\n")
            f.write(f"{pos.x()},{pos.y()}\n")

    # -----------------------------------------------------------------------------------
    # Charger dernier GIF
    # -----------------------------------------------------------------------------------
    def load_last_gif(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                lines = f.read().splitlines()
                if lines:
                    last_gif_name = lines[0]
                    fps_saved = int(lines[1])
                    zoom_saved = int(lines[2])
                    pos_saved = lines[3] if len(lines) > 3 else None

                    gif_path = os.path.join(GIF_FOLDER, last_gif_name)
                    if os.path.exists(gif_path):
                        self.fps = fps_saved
                        self.zoom_percent = zoom_saved
                        self.load_gif(gif_path)
                        if pos_saved:
                            x, y = map(int, pos_saved.split(","))
                            QtCore.QTimer.singleShot(100, lambda: self.move(x, y))
                        return

        # Sinon charger premier GIF du dossier
        gif_files = [f for f in sorted(os.listdir(GIF_FOLDER)) if f.lower().endswith(".gif")]
        if gif_files:
            self.load_gif(os.path.join(GIF_FOLDER, gif_files[0]))

    # -----------------------------------------------------------------------------------
    # Menu tray
    # -----------------------------------------------------------------------------------
    def build_tray_menu(self):
        self.tray_icon = QSystemTrayIcon(QtGui.QIcon())
        self.tray_icon.setToolTip("GIF en Avant-Plan")
        menu = QMenu()
        menu.addAction(QAction("Ouvrir un GIF", self, triggered=self.select_gif))
        menu.addAction(QAction("Régler FPS", self, triggered=self.set_fps))
        menu.addAction(QAction("Régler Zoom", self, triggered=self.set_zoom))
        menu.addAction(QAction("Ouvrir bibliothèque GIFs", self, triggered=self.open_gif_library))
        menu.addSeparator()
        menu.addAction(QAction("Quitter", self, triggered=QtWidgets.QApplication.quit))
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    # -----------------------------------------------------------------------------------
    # Sélection et chargement GIF
    # -----------------------------------------------------------------------------------
    def select_gif(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir un GIF", "", "GIF Files (*.gif)")
        if path:
            self.load_gif(path)

    def load_gif(self, path):
        self.gif = QtGui.QMovie(path)
        self.gif.setCacheMode(QtGui.QMovie.CacheAll)
        self.set_speed()
        self.setMovie(self.gif)
        self.gif.start()

        def adjust_size(frame):
            if frame == 0:
                self.base_size = self.gif.currentImage().size()
                self.apply_zoom()
                self.gif.frameChanged.disconnect(adjust_size)

        self.gif.frameChanged.connect(adjust_size)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: rgba(0,0,0,0);")

        # Mise à jour du dernier GIF
        with open(LAST_GIF_FILE, "w") as f:
            f.write(path)

    # -----------------------------------------------------------------------------------
    # Calcul speed_percent pour QMovie
    # -----------------------------------------------------------------------------------
    def set_speed(self):
        if self.gif:
            speed_percent = int((self.fps / self.NORMAL_FPS) * 100)
            self.gif.setSpeed(speed_percent)

    # -----------------------------------------------------------------------------------
    # Zoom
    # -----------------------------------------------------------------------------------
    def apply_zoom(self):
        if self.gif and self.base_size:
            new_size = self.base_size * (self.zoom_percent / 100)
            self.gif.setScaledSize(new_size)
            self.resize(new_size)
            if self.gif:
                self.save_config(self.gif.fileName())

    def set_zoom(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Régler le Zoom")
        layout = QtWidgets.QVBoxLayout(dialog)
        label = QtWidgets.QLabel(f"Zoom : {self.zoom_percent}%")
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setStyleSheet("color: red;")
        layout.addWidget(label)

        btn_minus = QtWidgets.QPushButton("x0.8")
        btn_plus = QtWidgets.QPushButton("x1.2")
        style = """
        QPushButton {
            color: white;
            background-color: black;
            border: 2px solid white;
            border-radius: 5px;
            font-size: 18pt;
            min-width: 50px;
            min-height: 40px;
        }
        QPushButton:hover {
            background-color: #333333;
        }
        QPushButton:pressed {
            background-color: #555555;
        }
        """

        btn_minus.setStyleSheet(style)
        btn_plus.setStyleSheet(style)
        btn_minus.clicked.connect(lambda: self.update_zoom(label, 0.8))
        btn_plus.clicked.connect(lambda: self.update_zoom(label, 1.2))

        h = QtWidgets.QHBoxLayout()
        h.addWidget(btn_minus)
        h.addWidget(btn_plus)
        layout.addLayout(h)

        dialog.exec_()

    def update_zoom(self, label, mult):
        self.zoom_percent = max(10, min(300, int(self.zoom_percent * mult)))
        label.setText(f"Zoom : {self.zoom_percent}%")
        label.setStyleSheet("color: red;")
        self.apply_zoom()

    # -----------------------------------------------------------------------------------
    # FPS
    # -----------------------------------------------------------------------------------
    def set_fps(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Régler FPS")
        layout = QtWidgets.QVBoxLayout(dialog)

        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setMinimum(1)
        slider.setMaximum(60)
        slider.setValue(self.fps)
        layout.addWidget(slider)

        label = QtWidgets.QLabel(f"FPS : {self.fps}")
        label.setStyleSheet("color: red;")
        layout.addWidget(label)

        def change(v):
            self.fps = v
            label.setText(f"FPS : {v}")
            label.setStyleSheet("color: red;")
            self.set_speed()
            if self.gif:
                self.save_config(self.gif.fileName())

        slider.valueChanged.connect(change)
        dialog.exec_()

    # -----------------------------------------------------------------------------------
    # Drag & Drop
    # -----------------------------------------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".gif"):
                    event.accept()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.toLocalFile().lower().endswith(".gif"):
                src = url.toLocalFile()
                os.makedirs(GIF_FOLDER, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dst = os.path.join(GIF_FOLDER, f"gif_{timestamp}.gif")
                shutil.copy2(src, dst)
                self.load_gif(dst)
                return

    # -----------------------------------------------------------------------------------
    # Bibliothèque GIFs
    # -----------------------------------------------------------------------------------
    def open_gif_library(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Bibliothèque GIFs")
        dialog.resize(400, 300)
        layout = QtWidgets.QVBoxLayout(dialog)

        self.gif_list_widget = QtWidgets.QListWidget()
        self.gif_list_widget.setViewMode(QtWidgets.QListView.IconMode)
        self.gif_list_widget.setIconSize(QtCore.QSize(100, 100))
        layout.addWidget(self.gif_list_widget)

        btn_delete = QtWidgets.QPushButton("Supprimer GIF")
        layout.addWidget(btn_delete)

        self.refresh_gif_list()
        btn_delete.clicked.connect(self.delete_selected_gif)
        self.gif_list_widget.itemDoubleClicked.connect(self.load_selected_gif)

        dialog.setLayout(layout)
        dialog.exec_()

    def refresh_gif_list(self):
        self.gif_list_widget.clear()
        files = [f for f in sorted(os.listdir(GIF_FOLDER)) if f.lower().endswith(".gif")]
        for filename in files:
            movie = QtGui.QMovie(os.path.join(GIF_FOLDER, filename))
            movie.jumpToFrame(0)
            pixmap = movie.currentPixmap()
            item = QtWidgets.QListWidgetItem(QtGui.QIcon(pixmap), filename)
            self.gif_list_widget.addItem(item)

    def load_selected_gif(self, item):
        path = os.path.join(GIF_FOLDER, item.text())
        if os.path.exists(path):
            self.load_gif(path)
            self.gif_list_widget.parentWidget().accept()

    def delete_selected_gif(self):
        selected_items = self.gif_list_widget.selectedItems()
        for item in selected_items:
            path = os.path.join(GIF_FOLDER, item.text())
            if os.path.exists(path):
                os.remove(path)
        self.refresh_gif_list()

    # -----------------------------------------------------------------------------------
    # Déplacement fenêtre
    # -----------------------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.start_pos = event.globalPos()
            self.init_pos = self.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton and self.start_pos:
            diff = event.globalPos() - self.start_pos
            self.move(self.init_pos + diff)
            if self.gif:
                self.save_config(self.gif.fileName())

    # -----------------------------------------------------------------------------------
    # Zoom molette
    # -----------------------------------------------------------------------------------
    def wheelEvent(self, event):
        if self.gif:
            if event.angleDelta().y() > 0:
                self.zoom_percent = min(300, int(self.zoom_percent * 1.2))
            else:
                self.zoom_percent = max(10, int(self.zoom_percent * 0.8))
            self.apply_zoom()

    # -----------------------------------------------------------------------------------
    # Menu contextuel
    # -----------------------------------------------------------------------------------
    def showMenu(self, pos):
        menu = QMenu()
        menu.addAction(QAction("Ouvrir un GIF", self, triggered=self.select_gif))
        menu.addAction(QAction("Régler FPS", self, triggered=self.set_fps))
        menu.addAction(QAction("Régler Zoom", self, triggered=self.set_zoom))
        menu.addAction(QAction("Ouvrir bibliothèque GIFs", self, triggered=self.open_gif_library))
        menu.addSeparator()
        menu.addAction(QAction("Fermer", self, triggered=QtWidgets.QApplication.quit))
        menu.exec_(self.mapToGlobal(pos))

# -----------------------------------------------------------------------------------
# Lancement de l'application
# -----------------------------------------------------------------------------------
app = QtWidgets.QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
window = GifWindow()
window.show()
sys.exit(app.exec_())
