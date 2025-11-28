import sys
from datetime import datetime
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QSystemTrayIcon, QMenu, QAction
import os
import shutil

LAST_GIF_FILE = "config/last_gif.txt"
CONFIG_FILE = "config/last_gif_config.txt"

class GifWindow(QtWidgets.QLabel):
    def __init__(self):
        # Création d'un widget parent invisible pour supprimer l'icône dans la barre des tâches
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
        self.setText("drag gif here")

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showMenu)
        self.build_tray_menu()
        self.start_pos = None

        os.makedirs("gif", exist_ok=True)
        pos_loaded = None
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                lines = f.read().splitlines()
                last_gif_path = lines[0] if lines else None
                if last_gif_path and os.path.exists(last_gif_path):
                    if len(lines) > 3:
                        x, y = map(int, lines[3].split(","))
                        self.load_gif(last_gif_path)
                        QtCore.QTimer.singleShot(100, lambda: self.move(x, y))
                    else:
                        self.load_gif(last_gif_path)
        else:
            gif_files = [f for f in sorted(os.listdir("gif")) if f.endswith(".gif")]
            if gif_files:
                self.load_gif(os.path.join("gif", gif_files[0]))

    def closeEvent(self, event):
        if self.gif:
            path = self.gif.fileName()
            self.save_config(path)
        event.accept()

    # --- Menu Tray ---
    def build_tray_menu(self):
        self.tray_icon = QSystemTrayIcon(QtGui.QIcon())
        self.tray_icon.setToolTip("GIF en Avant-Plan")
        menu = QMenu()

        open_action = QAction("Ouvrir un GIF", self)
        open_action.triggered.connect(self.select_gif)
        menu.addAction(open_action)

        fps_action = QAction("Régler FPS", self)
        fps_action.triggered.connect(self.set_fps)
        menu.addAction(fps_action)

        zoom_action = QAction("Régler Zoom", self)
        zoom_action.triggered.connect(self.set_zoom)
        menu.addAction(zoom_action)

        library_action = QAction("Ouvrir bibliothèque GIFs", self)
        library_action.triggered.connect(self.open_gif_library)
        menu.addAction(library_action)

        quit_action = QAction("Quitter", self)
        quit_action.triggered.connect(QtWidgets.QApplication.quit)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    # --- Sauvegarder configuration ---
    def save_config(self, path):
        pos = self.pos()
        with open(CONFIG_FILE, "w") as f:
            f.write(f"{path}\n")
            f.write(f"{self.fps}\n")
            f.write(f"{self.zoom_percent}\n")
            f.write(f"{pos.x()},{pos.y()}\n")

    # --- Charger un GIF ---
    def select_gif(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir un GIF", "", "GIF Files (*.gif)")
        if path:
            self.load_gif(path)

    def load_gif(self, path):
        self.gif = QtGui.QMovie(path)
        self.gif.setCacheMode(QtGui.QMovie.CacheAll)
        self.gif.setSpeed(self.fps * 10)
        self.setMovie(self.gif)
        self.gif.start()
        self.has_gif = True

        def adjust_size_on_first_frame(frame_number):
            if frame_number == 0:
                self.base_size = self.gif.currentImage().size()

                # Charger config si disponible et correspond au gif chargé
                if os.path.exists(CONFIG_FILE):
                    with open(CONFIG_FILE, "r") as f:
                        lines = f.read().splitlines()
                        if lines[0] == path:
                            self.fps = int(lines[1])
                            self.zoom_percent = int(lines[2])
                            x, y = map(int, lines[3].split(","))
                            self.move(x, y)
                            self.gif.setSpeed(self.fps * 10)

                self.apply_zoom()
                self.gif.frameChanged.disconnect(adjust_size_on_first_frame)

        self.gif.frameChanged.connect(adjust_size_on_first_frame)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: rgba(0,0,0,0);")

        # Sauvegarde du dernier GIF
        os.makedirs("gif", exist_ok=True)
        with open(LAST_GIF_FILE, "w") as f:
            f.write(path)

        # Ne pas sauvegarder immédiatement ici pour éviter écraser la position restaurée
        # self.save_config(path)

    # --- Zoom ---
    def apply_zoom(self):
        if self.gif and self.base_size:
            new_size = self.base_size * (self.zoom_percent / 100)
            self.gif.setScaledSize(new_size)
            self.resize(new_size)
            if self.gif:
                path = self.gif.fileName()
                self.save_config(path)

    def set_zoom(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Régler le Zoom")
        layout = QtWidgets.QVBoxLayout(dialog)

        label = QtWidgets.QLabel(f"Zoom : {self.zoom_percent}%")
        label.setAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setPointSize(20)
        label.setFont(font)
        label.setStyleSheet("color: white;")
        layout.addWidget(label)

        button_layout = QtWidgets.QHBoxLayout()
        minus_btn = QtWidgets.QPushButton("x0.8")
        plus_btn = QtWidgets.QPushButton("x1.2")
        for btn in [minus_btn, plus_btn]:
            btn.setFont(font)
            btn.setStyleSheet("color: white; background-color: black;")
        button_layout.addWidget(minus_btn)
        button_layout.addWidget(plus_btn)
        layout.addLayout(button_layout)

        def update_zoom(multiplier):
            self.zoom_percent = max(10, min(300, int(self.zoom_percent * multiplier)))
            label.setText(f"Zoom : {self.zoom_percent}%")
            self.apply_zoom()

        plus_btn.clicked.connect(lambda: update_zoom(1.2))
        minus_btn.clicked.connect(lambda: update_zoom(0.8))

        dialog.exec_()

    # --- FPS ---
    def set_fps(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Régler FPS")
        layout = QtWidgets.QVBoxLayout(dialog)

        slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        slider.setMinimum(1)
        slider.setMaximum(60)
        slider.setValue(self.fps)
        slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        slider.setTickInterval(5)

        label = QtWidgets.QLabel(f"FPS : {self.fps}")
        layout.addWidget(label)
        layout.addWidget(slider)

        def on_slider_change(value):
            self.fps = value
            label.setText(f"FPS : {value}")
            if self.gif:
                self.gif.setSpeed(self.fps * 10)
            if self.gif:
                path = self.gif.fileName()
                self.save_config(path)

        slider.valueChanged.connect(on_slider_change)
        dialog.exec_()

    # --- Drag & Drop ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().endswith('.gif'):
                    event.accept()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.toLocalFile().endswith('.gif'):
                src = url.toLocalFile()
                os.makedirs("gif", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dst = os.path.join("gif", f"gif_{timestamp}.gif")
                shutil.copy2(src, dst)
                self.load_gif(dst)
                return

    # --- Bibliothèque GIFs ---
    def open_gif_library(self):
        os.makedirs("gif", exist_ok=True)
        self.library_dialog = QtWidgets.QDialog(self)
        self.library_dialog.setWindowTitle("Bibliothèque GIFs")
        self.library_dialog.resize(400, 300)
        layout = QtWidgets.QVBoxLayout(self.library_dialog)

        self.gif_list_widget = QtWidgets.QListWidget()
        self.gif_list_widget.setViewMode(QtWidgets.QListView.IconMode)
        self.gif_list_widget.setIconSize(QtCore.QSize(100, 100))
        self.gif_list_widget.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.gif_list_widget.setSpacing(10)
        self.gif_list_widget.setStyleSheet("background-color: white;")
        layout.addWidget(self.gif_list_widget)

        self.delete_btn = QtWidgets.QPushButton("Supprimer le GIF sélectionné")
        self.delete_btn.setStyleSheet("background-color: red; color: white; font-weight: bold;")
        layout.addWidget(self.delete_btn)

        self.refresh_gif_list()
        self.delete_btn.clicked.connect(self.delete_selected_gif)
        self.gif_list_widget.itemDoubleClicked.connect(self.load_selected_gif)

        self.library_dialog.exec_()

    def refresh_gif_list(self):
        self.gif_list_widget.clear()
        gif_folder = "gif"
        os.makedirs(gif_folder, exist_ok=True)
        files = [f for f in sorted(os.listdir(gif_folder)) if f.endswith(".gif")]

        self.delete_btn.setEnabled(len(files) > 1)

        for filename in files:
            file_path = os.path.join(gif_folder, filename)
            movie = QtGui.QMovie(file_path)
            movie.jumpToFrame(0)
            pixmap = movie.currentPixmap()
            item = QtWidgets.QListWidgetItem()
            item.setIcon(QtGui.QIcon(pixmap))
            item.setText(filename)
            self.gif_list_widget.addItem(item)

    def load_selected_gif(self, item):
        file_path = os.path.join("gif", item.text())
        if os.path.exists(file_path):
            self.load_gif(file_path)
            if hasattr(self, "library_dialog") and self.library_dialog:
                self.library_dialog.accept()
                self.library_dialog = None

    def delete_selected_gif(self):
        selected_items = self.gif_list_widget.selectedItems()
        if not selected_items:
            return

        gif_folder = "gif"
        if len([f for f in os.listdir(gif_folder) if f.endswith(".gif")]) <= 1:
            return

        for item in selected_items:
            file_path = os.path.join(gif_folder, item.text())
            if os.path.exists(file_path):
                os.remove(file_path)

        self.refresh_gif_list()

    # --- Déplacement de la fenêtre ---
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.start_pos = event.globalPos()
            self.init_pos = self.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton and self.start_pos:
            diff = event.globalPos() - self.start_pos
            self.move(self.init_pos + diff)
            if self.gif:
                path = self.gif.fileName()
                self.save_config(path)

    # --- Zoom molette ---
    def wheelEvent(self, event):
        if self.gif:
            if event.angleDelta().y() > 0:
                self.zoom_percent = min(300, int(self.zoom_percent * 1.2))
            else:
                self.zoom_percent = max(10, int(self.zoom_percent * 0.8))
            self.apply_zoom()

    # --- Menu contextuel ---
    def showMenu(self, pos):
        menu = QMenu()
        menu.addAction(QAction("Ouvrir un GIF", self, triggered=self.select_gif))
        menu.addAction(QAction("Régler FPS", self, triggered=self.set_fps))
        menu.addAction(QAction("Régler Zoom", self, triggered=self.set_zoom))
        menu.addAction(QAction("Ouvrir bibliothèque GIFs", self, triggered=self.open_gif_library))
        menu.addSeparator()
        menu.addAction(QAction("Fermer", self, triggered=QtWidgets.QApplication.quit))
        menu.exec_(self.mapToGlobal(pos))


# --- Exécution ---
app = QtWidgets.QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
window = GifWindow()
window.show()
sys.exit(app.exec_())
