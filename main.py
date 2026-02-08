import sys
import os
import json
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout,
                               QWidget, QFileDialog, QTreeWidget, QTreeWidgetItem, QLabel,
                               QProgressBar, QCheckBox, QComboBox, QSpinBox, QGroupBox, QLineEdit)
from PySide6.QtCore import Qt
from checker_logic import UniversalFBXAnaliser

CONFIG_FILE = "config_qa_tool.json"


class CheckerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GameArt QA Pipeline - Scan & Patch")
        self.resize(1150, 800)
        self.setStyleSheet("background-color: #2b2b2b; color: #ffffff;")

        self.config = self.load_config()
        main_layout = QHBoxLayout()

        # --- PANEL GAUCHE ---
        settings_panel = QVBoxLayout()

        # Configuration Blender
        path_group = QGroupBox("Configuration")
        path_layout = QVBoxLayout()

        self.blender_path_input = QLineEdit(self.config.get("blender_path", ""))
        btn_browse = QPushButton("Chercher blender.exe")
        btn_browse.clicked.connect(self.browse_blender)

        path_layout.addWidget(self.blender_path_input)
        path_layout.addWidget(btn_browse)
        path_group.setLayout(path_layout)
        settings_panel.addWidget(path_group)

        # 1. VALIDATION (SCAN)
        val_group = QGroupBox("Validation (SCAN)")
        val_layout = QVBoxLayout()

        self.check_pivot = QCheckBox("Check Pivot Position")
        self.check_pivot.setChecked(True)

        self.scan_pivot_mode = QComboBox()
        self.scan_pivot_mode.addItems(["Bottom Center", "Center", "Top Center"])

        self.check_ngon = QCheckBox("Check NGons")
        self.check_ngon.setChecked(True)

        self.check_ucx = QCheckBox("Check UCX Collision")
        self.check_ucx.setChecked(True)

        self.check_poly = QCheckBox("Check Poly Limit")
        self.poly_limit = QSpinBox()

        self.poly_limit.setRange(1, 1000000)
        self.poly_limit.setValue(10000)

        val_layout.addWidget(self.check_pivot)
        val_layout.addWidget(self.scan_pivot_mode)
        val_layout.addWidget(self.check_ngon)
        val_layout.addWidget(self.check_ucx)
        val_layout.addWidget(self.check_poly)
        val_layout.addWidget(self.poly_limit)
        val_group.setLayout(val_layout)
        settings_panel.addWidget(val_group)

        # 2. PATCH (FIX)
        patch_group = QGroupBox("Patch (FIX)")
        patch_layout = QVBoxLayout()
        self.fix_pivot = QCheckBox("Fix Pivot & Center World")
        self.fix_pivot.setChecked(True)
        self.fix_pivot_mode = QComboBox()
        self.fix_pivot_mode.addItems(["Bottom Center", "Center", "Top Center"])

        self.fix_ngon = QCheckBox("Fix NGons (Triangulate)")
        self.fix_ngon.setChecked(True)
        self.fix_double = QCheckBox("Merge Double Vertices")
        self.fix_double.setChecked(True)

        patch_layout.addWidget(self.fix_pivot)
        patch_layout.addWidget(self.fix_pivot_mode)
        patch_layout.addWidget(self.fix_ngon)
        patch_layout.addWidget(self.fix_double)
        patch_group.setLayout(patch_layout)
        settings_panel.addWidget(patch_group)

        settings_panel.addStretch()

        # --- PANEL DROITE ---
        results_panel = QVBoxLayout()
        btn_layout = QHBoxLayout()
        self.btn_scan = QPushButton("🔍 SCANNER DOSSIER")
        self.btn_scan.setStyleSheet("background-color: #4CAF50; height: 50px; font-weight: bold;")
        self.btn_scan.clicked.connect(lambda: self.start_process(fix_mode=False))

        self.btn_patch = QPushButton("🔧 APPLIQUER PATCH (FIX)")
        self.btn_patch.setStyleSheet("background-color: #e67e22; height: 50px; font-weight: bold; color: black;")
        self.btn_patch.clicked.connect(lambda: self.start_process(fix_mode=True))

        btn_layout.addWidget(self.btn_scan)
        btn_layout.addWidget(self.btn_patch)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Fichier / Objet", "Status", "Détails"])
        self.tree.setColumnWidth(0, 350)

        results_panel.addLayout(btn_layout)
        results_panel.addWidget(self.progress)
        results_panel.addWidget(self.tree)

        # Final Layout
        left_container = QWidget()
        left_container.setLayout(settings_panel)
        left_container.setFixedWidth(320)
        main_layout.addWidget(left_container)
        main_layout.addLayout(results_panel)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def browse_blender(self):
        file, _ = QFileDialog.getOpenFileName(self, "Trouver blender.exe", "", "Executable (blender.exe)")
        if file: self.blender_path_input.setText(file); self.save_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f: return json.load(f)
        return {}

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump({"blender_path": self.blender_path_input.text()}, f)

    def start_process(self, fix_mode=False):
        self.save_config()
        blender_path = self.blender_path_input.text()
        if not os.path.exists(blender_path): return

        folder = QFileDialog.getExistingDirectory(self, "Dossier FBX")
        if not folder: return

        settings = {
            "check_pivot": self.check_pivot.isChecked(),
            "scan_pivot_mode": self.scan_pivot_mode.currentText(),
            "check_ngon": self.check_ngon.isChecked(),
            "check_ucx": self.check_ucx.isChecked(),
            "check_poly": self.check_poly.isChecked(),
            "poly_limit": self.poly_limit.value(),
            "fix_pivot": self.fix_pivot.isChecked(),
            "fix_pivot_mode": self.fix_pivot_mode.currentText(),
            "fix_ngon": self.fix_ngon.isChecked(),
            "fix_double": self.fix_double.isChecked()
        }

        self.tree.clear()
        files = [f for f in os.listdir(folder) if f.lower().endswith(".fbx")]
        self.progress.setVisible(True)
        self.progress.setMaximum(len(files))

        for i, fbx in enumerate(files):
            path = os.path.join(folder, fbx)
            file_item = QTreeWidgetItem(self.tree, [fbx, "Traitement..."])
            results = UniversalFBXAnaliser.check_file(path, settings, fix_mode=fix_mode, blender_path=blender_path)

            has_fail = False
            for res in results:
                icon = "✅" if res["status"] == "Pass" else "❌"
                child = QTreeWidgetItem(file_item, [res["name"], icon, ", ".join(res["errors"])])
                if res["status"] == "Fail": child.setForeground(1, Qt.red); has_fail = True

            file_item.setText(1, "🟢 PASS" if not has_fail else "🔴 FAIL")
            file_item.setExpanded(True)
            self.progress.setValue(i + 1)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CheckerWindow()
    window.show()
    sys.exit(app.exec())