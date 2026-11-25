import hashlib
import os
import re
import struct
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageDraw, ImageTk

def detecter_groupes_modifs(img_ref, img_mod, distance_fusion=2):
    """Regroupe les pixels modifiés proches en îlots distincts (gribouillis/zones)."""
    largeur, hauteur = img_ref.size
    pix_ref = img_ref.load()
    pix_mod = img_mod.load()

    pixels_modifies = set()
    for y in range(hauteur):
        for x in range(largeur):
            if pix_mod[x, y] != pix_ref[x, y]:
                pixels_modifies.add((x, y))

    visites = set()
    groupes = []

    for px in pixels_modifies:
        if px in visites:
            continue

        file_attente = [px]
        visites.add(px)
        pixels_du_groupe = set()

        while file_attente:
            cx, cy = file_attente.pop()
            pixels_du_groupe.add((cx, cy))

            for dy in range(-distance_fusion, distance_fusion + 1):
                for dx in range(-distance_fusion, distance_fusion + 1):
                    voisin = (cx + dx, cy + dy)
                    if voisin in pixels_modifies and voisin not in visites:
                        visites.add(voisin)
                        file_attente.append(voisin)

        xs, ys = zip(*pixels_du_groupe)
        rect = (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))
        groupes.append({"rect": rect, "pixels": pixels_du_groupe})

    groupes.sort(key=lambda g: (g["rect"], g["rect"]))
    return groupes

def rectangles_se_chevauchent(r1, r2):
    """Calcule l'intersection de deux rectangles plats (x1, y1, x2, y2)."""
    ax1, ay1, ax2, ay2 = r1
    bx1, by1, bx2, by2 = r2
    cx1, cy1 = max(ax1, bx1), max(ay1, by1)
    cx2, cy2 = min(ax2, bx2), min(ay2, by2)
    if cx1 <= cx2 and cy1 <= cy2:
        return (int(cx1), int(cy1), int(cx2), int(cy2))
    return None

class MultiBoundingBoxApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TS2 Mod Manager - Conflict Manager (Future feature simulated)")
        self.root.geometry("860x660")
        self.root.configure(padx=15, pady=15)

        self.var_ref = tk.StringVar()
        self.var_mod_a = tk.StringVar()
        self.var_mod_b = tk.StringVar()
        self.var_vue = tk.StringVar(value="mixte")

        self.creer_interface()

    def creer_interface(self):
        titre = tk.Label(
            self.root,
            text="TS2 Mod Manager : Analyse et arbitrage des collisions de textures",
            font=("Segoe UI", 12, "bold")
        )
        titre.pack(anchor="w", pady=(0, 10))

        self.ajouter_ligne_fichier("1. Texture Vanilla (Base) :", self.var_ref)
        self.ajouter_ligne_fichier("2. Texture Mod A (Actif) :", self.var_mod_a)
        self.ajouter_ligne_fichier("3. Texture Mod B (Entrant) :", self.var_mod_b)

        btn_analyser = tk.Button(
            self.root,
            text="Analyser et vérifier la compatibilité du Mod B",
            font=("Segoe UI", 10, "bold"),
            bg="#1565C0",
            fg="white",
            pady=8,
            command=self.lancer_analyse
        )
        btn_analyser.pack(fill="x", pady=12)

        self.lbl_info = tk.Label(
            self.root,
            text="Veuillez charger vos textures pour lancer la détection.",
            font=("Consolas", 9),
            justify="left",
            fg="#222222"
        )
        self.lbl_info.pack(anchor="w", pady=(0, 10))

        cadre_apercu = tk.Frame(self.root)
        cadre_apercu.pack(fill="both", expand=True)

        col_gauche = tk.Frame(cadre_apercu)
        col_gauche.pack(side="left", fill="both", expand=True, padx=(0, 5))
        tk.Label(col_gauche, text="Carte globale des zones (Alerte)", font=("Segoe UI", 9, "bold")).pack()
        self.lbl_img_debug = tk.Label(col_gauche, bg="#E0E0E0", relief="sunken")
        self.lbl_img_debug.pack(fill="both", expand=True, pady=4)

        col_droite = tk.Frame(cadre_apercu)
        col_droite.pack(side="right", fill="both", expand=True, padx=(5, 0))
        tk.Label(col_droite, text="Résultat final de la fusion", font=("Segoe UI", 9, "bold")).pack()
        self.lbl_img_fusion = tk.Label(col_droite, bg="#E0E0E0", relief="sunken")
        self.lbl_img_fusion.pack(fill="both", expand=True, pady=4)

    def ajouter_ligne_fichier(self, texte_label, variable):
        cadre = tk.Frame(self.root)
        cadre.pack(fill="x", pady=3)
        tk.Label(cadre, text=texte_label, width=28, anchor="w").pack(side="left")
        tk.Entry(cadre, textvariable=variable).pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(cadre, text="Parcourir...", command=lambda: self.choisir_image(variable)).pack(side="right")

    def choisir_image(self, variable):
        chemin = filedialog.askopenfilename(
            filetypes=[("Images", "*.bmp")]
        )
        if chemin:
            variable.set(chemin)

    def lancer_analyse(self):
        p_ref = self.var_ref.get().strip()
        p_a = self.var_mod_a.get().strip()
        p_b = self.var_mod_b.get().strip()

        if not (os.path.exists(p_ref) and os.path.exists(p_a) and os.path.exists(p_b)):
            messagebox.showerror("Fichiers manquants", "Veuillez sélectionner les trois images.")
            return

        self.img_ref = Image.open(p_ref).convert("RGB")
        self.img_a = Image.open(p_a).convert("RGB")
        self.img_b = Image.open(p_b).convert("RGB")

        if self.img_ref.size != self.img_a.size or self.img_ref.size != self.img_b.size:
            messagebox.showerror("Tailles incompatibles", "Toutes les images doivent avoir la même résolution.")
            return

        # 1. Détection des groupes de modifications
        self.groupes_a = detecter_groupes_modifs(self.img_ref, self.img_a, distance_fusion=2)
        self.groupes_b = detecter_groupes_modifs(self.img_ref, self.img_b, distance_fusion=2)

        # 2. Identification des conflits
        self.conflits = []
        for idx_b, gb in enumerate(self.groupes_b):
            for idx_a, ga in enumerate(self.groupes_a):
                inter = rectangles_se_chevauchent(ga["rect"], gb["rect"])
                if inter:
                    self.conflits.append({
                        "id_b": idx_b, "id_a": idx_a,
                        "rect_b": gb["rect"], "rect_a": ga["rect"], "rect_inter": inter,
                        "pixels_b": gb["pixels"], "pixels_a": ga["pixels"], "decision": None
                    })

        if self.conflits:
            reponse = messagebox.askyesno(
                "⚠️ Conflits détectés",
                f"Le Mod B entre en collision avec le Mod A (déjà actif) sur {len(self.conflits)} zone(s).\n\n"
                "Voulez-vous ouvrir l'assistant de résolution des conflits ?"
            )
            if reponse:
                self.ouvrir_assistant_conflits()
            else:
                self.lbl_info.configure(text="Activation du Mod B annulée par l'utilisateur.")
        else:
            self.appliquer_fusion_directe()

    def ouvrir_assistant_conflits(self):
        self.win_assistant = tk.Toplevel(self.root)
        self.win_assistant.title("Assistant de Résolution Professionnel - TS2 Mod Manager")
        self.win_assistant.geometry("1100x680")
        self.win_assistant.transient(self.root)
        self.win_assistant.grab_set()

        cadre_principal = tk.Frame(self.win_assistant, padx=10, pady=10)
        cadre_principal.pack(fill="both", expand=True)

        # Colonne gauche unifiée (Liste + Arbitrage) de 360px de large
        col_actions_arbre = tk.Frame(cadre_principal, width=360)
        col_actions_arbre.pack(side="left", fill="both", padx=5)
        col_actions_arbre.pack_propagate(False)

        # Section 1 : Arbre Treeview hiérarchique par fichier élargi
        cadre_liste = tk.LabelFrame(col_actions_arbre, text=" 1. Liste des collisions ", padx=5, pady=5)
        cadre_liste.pack(fill="both", expand=True, pady=(0, 5))

        self.tree_conflits = ttk.Treeview(cadre_liste, columns=("status",), show="tree headings")
        self.tree_conflits.heading("#0", text="Ressource / Zone", anchor="w")
        self.tree_conflits.heading("status", text="Statut", anchor="center")
        self.tree_conflits.column("#0", width=220, anchor="w")
        self.tree_conflits.column("status", width=100, anchor="center")
        self.tree_conflits.pack(fill="both", expand=True)
        self.tree_conflits.bind("<<TreeviewSelect>>", self.sur_conflit_selectionne)

        nom_fichier_demo = "Level01 / Tex00"
        id_parent = self.tree_conflits.insert("", "end", text=nom_fichier_demo, open=True, values=("En attente",))

        for idx, conf in enumerate(self.conflits):
            self.tree_conflits.insert(id_parent, "end", iid=str(idx), text=f"Collision #{idx + 1}", values=("⚠️ Non réglé",))

        # Section 2 : Panneau d'arbitrage situé directement sous l'arbre
        self.cadre_actions = tk.LabelFrame(col_actions_arbre, text=" 2. Arbitrage de la zone sélectionnée ", padx=10, pady=10)
        self.cadre_actions.pack(fill="x", pady=(5, 0))

        self.lbl_statut_zone = tk.Label(self.cadre_actions, text="Sélectionnez une collision dans l'arbre.", font=("Segoe UI", 9, "bold"), justify="center")
        self.lbl_statut_zone.pack(pady=(0, 10), fill="x")

        self.btn_garder_a = tk.Button(
            self.cadre_actions, text="🔴 Garder le Mod A (Actif)", font=("Segoe UI", 9, "bold"),
            bg="#FFCDD2", fg="#B71C1C", height=2, state="disabled", command=lambda: self.enregistrer_decision("A")
        )
        self.btn_garder_a.pack(fill="x", pady=4)

        self.btn_prendre_b = tk.Button(
            self.cadre_actions, text="🔵 Remplacer par le Mod B (Entrant)", font=("Segoe UI", 9, "bold"),
            bg="#BBDEFB", fg="#0D47A1", height=2, state="disabled", command=lambda: self.enregistrer_decision("B")
        )
        self.btn_prendre_b.pack(fill="x", pady=4)

        btn_tout_b = tk.Button(self.cadre_actions, text="Tout écraser par le Mod B", font=("Segoe UI", 9), command=self.tout_resoudre_b)
        btn_tout_b.pack(fill="x", pady=(15, 4))

        # Bouton d'application finale lisible (fond gris clair standard)
        self.btn_appliquer_mats = tk.Button(
            self.cadre_actions, text="Appliquer les décisions", font=("Segoe UI", 10, "bold"),
            bg="#E0E0E0", fg="#757575", state="disabled", command=self.finaliser_fusion_assistee
        )
        self.btn_appliquer_mats.pack(fill="x", pady=(4, 0))

        # 3. Colonne Droite - Élargie au maximum pour l'aperçu géolocalisé interactif
        self.cadre_visuel = tk.LabelFrame(cadre_principal, text=" 3. Aperçu géolocalisé interactif ", padx=10, pady=10)
        self.cadre_visuel.pack(side="right", fill="both", expand=True, padx=5)

        cadre_radios = tk.Frame(self.cadre_visuel)
        cadre_radios.pack(fill="x", pady=(0, 5))
        
        tk.Radiobutton(cadre_radios, text="Vue Mod A (Actif)", variable=self.var_vue, value="A", command=self.rafrachir_apercu).pack(side="left", padx=5)
        tk.Radiobutton(cadre_radios, text="Vue Mod B (Entrant)", variable=self.var_vue, value="B", command=self.rafrachir_apercu).pack(side="left", padx=5)
        tk.Radiobutton(cadre_radios, text="Vue Mixte (Cadres)", variable=self.var_vue, value="mixte", command=self.rafrachir_apercu).pack(side="left", padx=5)

        self.var_afficher_modifs = tk.BooleanVar(value=True)
        self.chk_modifs = tk.Checkbutton(
            self.cadre_visuel, text="Afficher les modifications dessinées", 
            variable=self.var_afficher_modifs, command=self.rafrachir_apercu
        )
        self.chk_modifs.pack(anchor="w", pady=(0, 5))

        # Grand Canvas carré sur fond gris foncé
        self.canvas_local = tk.Canvas(self.cadre_visuel, bg="#1E1E1E", bd=1, relief="sunken", highlightthickness=0)
        self.canvas_local.pack(fill="both", expand=True, pady=5)

                # Initialisation du moteur de zoom et déplacement de la caméra (Canvas Scan/Drag)
        self.zoom_facteur = 1.0  # Démarre à 1.0 pour occuper 100% de la zone par défaut
        self.canvas_local.bind("<ButtonPress-1>", self.commencer_pan)
        self.canvas_local.bind("<B1-Motion>", self.executer_pan)
        self.canvas_local.bind("<MouseWheel>", self.executer_zoom)

        self.tree_conflits.selection_set("0")
        self.sur_conflit_selectionne(None)

    def rafrachir_apercu(self):
        self.sur_conflit_selectionne(None)

    def commencer_pan(self, event):
        self.canvas_local.scan_mark(event.x, event.y)

    def executer_pan(self, event):
        self.canvas_local.scan_dragto(event.x, event.y, gain=1)

    def executer_zoom(self, event):
        if event.delta > 0:
            self.zoom_facteur = min(16.0, self.zoom_facteur + 0.5)
        else:
            self.zoom_facteur = max(1.0, self.zoom_facteur - 0.5)
        self.sur_conflit_selectionne(None)

    def sur_conflit_selectionne(self, event):
        selection = self.tree_conflits.selection()
        if not selection:
            return
            
        # Sécurité anti-crash : Si on clique sur la ligne parente, on ignore proprement l'événement
        id_selectionne = next(iter(selection))
        if not id_selectionne.isdigit():
            return

        idx = int(id_selectionne)
        conflit_courant = next(iter(self.conflits[idx : idx + 1]))

        # Mettre à jour l'affichage central
        dec = conflit_courant["decision"]
        statut_txt = "En attente" if dec is None else f"Tranché ({dec})"
        self.lbl_statut_zone.configure(text=f"Collision #{idx + 1}\nStatut : {statut_txt}")
        self.btn_garder_a.configure(state="normal")
        self.btn_prendre_b.configure(state="normal")

        # 1. Sélection de la texture de fond (Modifications ou fond Vanilla pur)
        if self.var_afficher_modifs.get():
            img_base = self.img_ref.copy()
            pix_b = img_base.load()
            pix_mod_a = self.img_a.load()
            pix_mod_b = self.img_b.load()
            for ga in self.groupes_a:
                for (x, y) in ga["pixels"]: pix_b[x, y] = pix_mod_a[x, y]
            for gb in self.groupes_b:
                for (x, y) in gb["pixels"]: pix_b[x, y] = pix_mod_b[x, y]
        else:
            img_base = self.img_ref.copy()

        # 2. Application du filtre de vue ("A" va bien chercher self.img_a)
        vue = self.var_vue.get()
        if vue == "A":
            img_view = self.img_a.copy()
        elif vue == "B":
            img_view = self.img_b.copy()
        else:
            img_view = img_base

        draw = ImageDraw.Draw(img_view)

        # 3. Extraction et calcul des rectangles (Correction chirurgicale avec index du tuple [0] et)
        px_a = list(conflit_courant["pixels_a"])
        px_b = list(conflit_courant["pixels_b"])
        
        ax1 = int(min(pt[0] for pt in px_a))
        ay1 = int(min(pt[1] for pt in px_a))
        ax2 = int(max(pt[0] for pt in px_a))
        ay2 = int(max(pt[1] for pt in px_a))
        
        bx1 = int(min(pt[0] for pt in px_b))
        by1 = int(min(pt[1] for pt in px_b))
        bx2 = int(max(pt[0] for pt in px_b))
        by2 = int(max(pt[1] for pt in px_b))
        
        cx1, cy1, cx2, cy2 = map(int, conflit_courant["rect_inter"])

        # Tracé des lignes 1px discrètes sur la vue Mixte
        if vue == "mixte":
            draw.line([ax1, ay1, ax2, ay1, ax2, ay2, ax1, ay2, ax1, ay1], fill=(255, 0, 0), width=1)
            draw.line([bx1, by1, bx2, by1, bx2, by2, bx1, by2, bx1, by1], fill=(0, 120, 255), width=1)
            draw.line([cx1, cy1, cx2, cy1, cx2, cy2, cx1, cy2, cx1, cy1], fill=(255, 235, 59), width=1)

        # 4. Comportement Caméra (Pas de marges, occupe 100% de l'espace au dézoom minimum)
        self.win_assistant.update_idletasks()
        w_canvas = max(400, self.canvas_local.winfo_width())
        h_canvas = max(400, self.canvas_local.winfo_height())
        taille_canvas = min(w_canvas, h_canvas)

        centre_x, centre_y = (cx1 + cx2) // 2, (cy1 + cy2) // 2
        
        # Le crop s'ajuste dynamiquement selon le facteur de zoom
        taille_crop = int((img_view.width / 2) / self.zoom_facteur)
        
        crop_box = (
            max(0, centre_x - taille_crop), max(0, centre_y - taille_crop),
            min(img_view.width, centre_x + taille_crop), min(img_view.height, centre_y + taille_crop)
        )
        
        # Redimensionnement net (Nearest) à la taille exacte du viewport carré
        img_cropped = img_view.crop(crop_box).resize((taille_canvas, taille_canvas), Image.Resampling.NEAREST)
        self.tk_img_local = ImageTk.PhotoImage(img_cropped)
        
        self.canvas_local.delete("all")
        self.canvas_local.create_image(w_canvas // 2, h_canvas // 2, image=self.tk_img_local, anchor="center")

    def verificar_tous_resolus(self):
        """Vérifie si TOUTES les collisions de la liste ont reçu un arbitrage."""
        for conf in self.conflits:
            if conf["decision"] is None:
                return False
        return True

    def enregistrer_decision(self, choix):
        selection = self.tree_conflits.selection()
        if not selection:
            return
        idx = int(next(iter(selection)))
        self.conflits[idx]["decision"] = choix

        symbole = "🔴 Mod A" if choix == "A" else "🔵 Mod B"
        self.tree_conflits.item(str(idx), values=(symbole,))

        # Sécurité : On vérifie l'intégralité du tableau avant d'activer le bouton vert
        if self.verificar_tous_resolus():
            self.btn_appliquer_mats.configure(state="normal", bg="#2E7D32", fg="white")
            self.lbl_statut_zone.configure(text="Toutes les zones ont été arbitrées !\nVous pouvez appliquer.", fg="#2E7D32")
        else:
            if idx + 1 < len(self.conflits):
                self.tree_conflits.selection_clear()
                self.tree_conflits.selection_set(str(idx + 1))
                self.sur_conflit_selectionne(None)

    def tout_resoudre_b(self):
        for idx, conf in enumerate(self.conflits):
            conf["decision"] = "B"
            self.tree_conflits.item(str(idx), values=("🔵 Mod B",))
        self.btn_appliquer_mats.configure(state="normal", bg="#2E7D32", fg="white")
        self.finaliser_fusion_assistee()

    def finaliser_fusion_assistee(self):
        if not self.verificar_tous_resolus():
            messagebox.showwarning("Incomplet", "Veuillez résoudre tous les conflits avant d'appliquer.")
            return

        img_fusion = self.img_ref.copy()
        pix_fusion = img_fusion.load()
        pix_a = self.img_a.load()
        pix_b = self.img_b.load()

        for ga in self.groupes_a:
            for (x, y) in ga["pixels"]: pix_fusion[x, y] = pix_a[x, y]

        for gb in self.groupes_b:
            pixels_conflit_locaux = set()
            conflits_lies = []

            for conf in self.conflits:
                if conf["rect_b"] == gb["rect"]:
                    conflits_lies.append(conf)
                    pixels_conflit_locaux.update(conf["pixels_b"])

            if not conflits_lies:
                for (x, y) in gb["pixels"]: pix_fusion[x, y] = pix_b[x, y]
            else:
                decision_prise = next(iter(conflits_lies))["decision"]
                for (x, y) in gb["pixels"]:
                    if (x, y) in pixels_conflit_locaux:
                        if decision_prise == "B": pix_fusion[x, y] = pix_b[x, y]
                    else:
                        pix_fusion[x, y] = pix_b[x, y]

        self.sauvegarder_et_afficher_images(img_fusion)
        self.win_assistant.destroy()

    def appliquer_fusion_directe(self):
        img_fusion = self.img_ref.copy()
        pix_fusion = img_fusion.load()
        pix_a = self.img_a.load()
        pix_b = self.img_b.load()

        for ga in self.groupes_a:
            for (x, y) in ga["pixels"]: pix_fusion[x, y] = pix_a[x, y]
        for gb in self.groupes_b:
            for (x, y) in gb["pixels"]: pix_fusion[x, y] = pix_b[x, y]

        self.sauvegarder_et_afficher_images(img_fusion)
        self.lbl_info.configure(text="[FUSION DIRECTE] Aucun conflit détecté. Fusion réalisée à 100% en arrière-plan.")

    def sauvegarder_et_afficher_images(self, img_fusion):
        img_debug = self.img_ref.copy()
        draw = ImageDraw.Draw(img_debug)
        for ga in self.groupes_a:
            x1, y1, x2, y2 = map(int, ga["rect"])
            draw.line([x1, y1, x2, y1, x2, y2, x1, y2, x1, y1], fill=(255, 0, 0), width=1)
        for gb in self.groupes_b:
            x1, y1, x2, y2 = map(int, gb["rect"])
            draw.line([x1, y1, x2, y1, x2, y2, x1, y2, x1, y1], fill=(0, 120, 255), width=1)
        for conf in self.conflits:
            cx1, cy1, cx2, cy2 = map(int, conf["rect_inter"])
            draw.line([cx1, cy1, cx2, cy1, cx2, cy2, cx1, cy2, cx1, cy1], fill=(255, 220, 0), width=1)

        dossier = os.path.dirname(self.var_ref.get().strip())
        img_debug.save(os.path.join(dossier, "debug_bounding_boxes.png"))
        img_fusion.save(os.path.join(dossier, "fusion_resultat.bmp"))

        self.lbl_info.configure(
            text=f"• Zones Mod A (Rouge) : {len(self.groupes_a)} | Zones Mod B (Bleu) : {len(self.groupes_b)}\n"
                 f"• Fichiers mis à jour avec succès sur le disque dans : {dossier}"
        )

        ap_debug = img_debug.resize((320, 320), Image.Resampling.NEAREST)
        ap_fusion = img_fusion.resize((320, 320), Image.Resampling.NEAREST)
        self.tk_img_debug = ImageTk.PhotoImage(ap_debug)
        self.tk_img_fusion = ImageTk.PhotoImage(ap_fusion)

        self.lbl_img_debug.configure(image=self.tk_img_debug)
        self.lbl_img_fusion.configure(image=self.tk_img_fusion)

if __name__ == "__main__":
    fenetre = tk.Tk()
    app = MultiBoundingBoxApp(fenetre)
    fenetre.mainloop()
