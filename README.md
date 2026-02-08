# GameArt QA Pipeline (FBX Validator)
Outil standalone de validation et de correction automatique d'assets 3D pour les moteurs de jeu (Unreal Engine / Unity). Ce projet assure que les fichiers .fbx respectent les contraintes techniques avant leur intégration.

## 📋 Vue d'ensemble
Ce pipeline permet aux artistes 3D et aux Tech Artists de scanner un dossier entier d'assets pour détecter les erreurs fréquentes (mauvais pivot, n-gons, nomenclature) et d'appliquer des correctifs automatiques sans ouvrir manuellement chaque fichier.

### Stack Technique
Frontend : Python 3.10+ & PySide6 (Qt).

Backend : Blender API (bpy) en mode headless (arrière-plan).

Format supporté : FBX.

## ⚙️ Fonctionnement
L'architecture repose sur l'injection de scripts :

GUI (Main Thread) : L'utilisateur configure les règles de validation via l'interface.

Processus : L'outil génère un script Python temporaire contenant les paramètres.

Exécution : Une instance de Blender est lancée en ligne de commande (subprocess) pour exécuter ce script sur le fichier cible.

Reporting : Les résultats sont sérialisés en JSON via stdout et affichés en temps réel dans l'interface.

## ✅ Features Actuelles
### 1. Validation (Mode Scan)
Pivot Point : Vérification de l'alignement (ex: Bottom Center pour les props au sol).

Topologie : Détection des N-Gons (faces > 4 sommets).

Polycount : Alerte si le budget de polygones est dépassé.

Nomenclature : Vérification de la correspondance des noms de collision (UCX_Asset vs Asset).

### 2. Correction Automatique (Mode Patch)
Auto-Triangulation : Conversion des N-Gons en triangles.

Reset Pivot : Recalcul du point de pivot (Bounding Box Center/Bottom) et déplacement à l'origine (0,0,0).

Cleanup : Fusion des sommets doublés (Remove Doubles) et application des transformations (Freeze Transforms).

## 🚀 Roadmap & Futures Features
L'outil est conçu pour être modulaire. Les prochaines itérations incluront des vérifications plus poussées sur les UVs et les matériaux.

### UV Validation :

Détection des UVs qui se chevauchent (Overlapping UVs).

Vérification des UVs hors de l'espace 0-1 (UDIM check).

### Texel Density :
 Analyse de la densité de pixels pour garantir une cohérence visuelle.

### Smoothing Groups :
 Vérification des Hard Edges et des normales brisées.

### Material Check :
 Détection des matériaux suffixes (ex: .001) ou des slots vides.

### LOD Generator :
 Génération automatique de niveaux de détails basiques.

## 🛠 Installation & Usage
1. Cloner le repo.

2. Installer les dépendances :
```Bash
pip install PySide6
```

Lancer l'application :
```Bash
python main_gui.py
```
Au premier lancement, indiquer le chemin de l'exécutable blender.exe dans l'onglet Configuration.