import hashlib
import os
import sys
import re
import struct
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

# Configuration globale du thème CustomTkinter
ctk.set_appearance_mode("System")  # Aligné sur le thème de l'OS (Sombre/Clair)
ctk.set_default_color_theme("blue")

def detecter_groupes_modifs(img_ref, img_mod, distance_fusion=2):
    """Groups modified pixels close to each other into distinct clusters."""
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
    """Calculates the intersection of two flat rectangles (x1, y1, x2, y2)."""
    ax1, ay1, ax2, ay2 = r1
    bx1, by1, bx2, by2 = r2
    cx1, cy1 = max(ax1, bx1), max(ay1, by1)
    cx2, cy2 = min(ax2, bx2), min(ay2, by2)
    if cx1 <= cx2 and cy1 <= cy2:
        return (int(cx1), int(cy1), int(cx2), int(cy2))
    return None

class MultiBoundingBoxApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TS2 Mod Manager - Texture Conflict Resolver")
        self.geometry("900x720")

        self.var_ref = tk.StringVar()
        self.var_mod_a = tk.StringVar()
        self.var_mod_b = tk.StringVar()
        self.var_vue = tk.StringVar(value="mixte")

        self.creer_interface()

        # Target your assets directory at the same level as main_v2.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, "assets", "ts2.ico")
        
        # Apply window icon safely if the file exists on the disk
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

    def creer_interface(self):
        # Titre Principal
        titre = ctk.CTkLabel(
            self,
            text="TS2 Mod Manager: Texture Collision Analysis & Arbitration",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        titre.pack(anchor="w", padx=20, pady=(20, 15))

        # Cadre de sélection des fichiers
        cadre_fichiers = ctk.CTkFrame(self)
        cadre_fichiers.pack(fill="x", padx=20, pady=5)

        self.ajouter_ligne_fichier(cadre_fichiers, "1. Vanilla Texture (Base):", self.var_ref)
        self.ajouter_ligne_fichier(cadre_fichiers, "2. Mod A Texture (Active):", self.var_mod_a)
        self.ajouter_ligne_fichier(cadre_fichiers, "3. Mod B Texture (Incoming):", self.var_mod_b)

        # Bouton d'analyse principale
        btn_analyser = ctk.CTkButton(
            self,
            text="Analyze and Verify Mod B Compatibility",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=40,
            command=self.lancer_analyse
        )
        btn_analyser.pack(fill="x", padx=20, pady=15)

        # Label d'informations log
        self.lbl_info = ctk.CTkLabel(
            self,
            text="Please load textures to initiate detection.",
            font=ctk.CTkFont(family="Consolas", size=11),
            anchor="w",
            justify="left"
        )
        self.lbl_info.pack(anchor="w", padx=25, pady=(0, 10))

        # Zone d'aperçu principale
        cadre_apercu = ctk.CTkFrame(self, fg_color="transparent")
        cadre_apercu.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        cadre_apercu.grid_columnconfigure((0, 1), weight=1)
        cadre_apercu.grid_rowconfigure(0, weight=1)

        # Colonne Gauche : Map de Déboguage
        col_gauche = ctk.CTkFrame(cadre_apercu)
        col_gauche.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        ctk.CTkLabel(col_gauche, text="Global Conflict Map (Alerts)", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        self.lbl_img_debug = ctk.CTkLabel(col_gauche, text="", fg_color=("#D1D5DB", "#2A2B2B"))
        self.lbl_img_debug.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Colonne Droite : Aperçu Fusion
        col_droite = ctk.CTkFrame(cadre_apercu)
        col_droite.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        ctk.CTkLabel(col_droite, text="Final Merged Result", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        self.lbl_img_fusion = ctk.CTkLabel(col_droite, text="", fg_color=("#D1D5DB", "#2A2B2B"))
        self.lbl_img_fusion.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def ajouter_ligne_fichier(self, parent, texte_label, variable):
        cadre = ctk.CTkFrame(parent, fg_color="transparent")
        cadre.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(cadre, text=texte_label, width=200, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(cadre, textvariable=variable)
        entry.pack(side="left", fill="x", expand=True, padx=10)
        btn = ctk.CTkButton(cadre, text="Browse...", width=100, command=lambda: self.choisir_image(variable))
        btn.pack(side="right")

    def choisir_image(self, variable):
        chemin = filedialog.askopenfilename(filetypes=[("Images", "*.bmp")])
        if chemin:
            variable.set(chemin)

    def lancer_analyse(self):
        p_ref = self.var_ref.get().strip()
        p_a = self.var_mod_a.get().strip()
        p_b = self.var_mod_b.get().strip()

        if not (os.path.exists(p_ref) and 
                os.path.exists(p_a) and 
                os.path.exists(p_b)):
            messagebox.showerror("Missing Files", "Please select all three base images.")
            return

        self.img_ref = Image.open(p_ref).convert("RGB")
        self.img_a = Image.open(p_a).convert("RGB")
        self.img_b = Image.open(p_b).convert("RGB")

        if (self.img_ref.size != self.img_a.size or 
                self.img_ref.size != self.img_b.size):
            messagebox.showerror("Incompatible Dimensions", 
                                 "Images must share the same resolution.")
            return

        self.groupes_a = detecter_groupes_modifs(self.img_ref, self.img_a, distance_fusion=2)
        self.groupes_b = detecter_groupes_modifs(self.img_ref, self.img_b, distance_fusion=2)

        self.conflits = []
        for idx_b, gb in enumerate(self.groupes_b):
            for idx_a, ga in enumerate(self.groupes_a):
                inter = rectangles_se_chevauchent(ga["rect"], gb["rect"])
                if inter:
                    self.conflits.append({
                        "id_b": idx_b, "id_a": idx_a,
                        "rect_b": gb["rect"], "rect_a": ga["rect"], 
                        "rect_inter": inter, "pixels_b": gb["pixels"], 
                        "pixels_a": ga["pixels"], "decision": None
                    })

        if self.conflits:
            reponse = messagebox.askyesno(
                "⚠️ Conflicts Detected",
                f"Mod B collides with Mod A on {len(self.conflits)} zone(s).\n\n"
                "Open the Conflict Resolution Assistant?"
            )
            if reponse:
                self.ouvrir_assistant_conflits()
            else:
                self.lbl_info.configure(text="Mod B activation aborted.")
        else:
            self.appliquer_fusion_directe()

    def ouvrir_assistant_conflits(self):
        self.win_assistant = ctk.CTkToplevel(self)
        self.win_assistant.title("Conflict Resolution Assistant")
        self.win_assistant.geometry("1150x700")
        self.win_assistant.transient(self)
        self.win_assistant.grab_set()

        cadre_principal = ctk.CTkFrame(self.win_assistant, fg_color="transparent")
        cadre_principal.pack(fill="both", expand=True, padx=15, pady=15)

        col_actions_arbre = ctk.CTkFrame(cadre_principal, width=380)
        col_actions_arbre.pack(side="left", fill="both", padx=(0, 10))
        col_actions_arbre.pack_propagate(False)

        cadre_liste = ctk.CTkFrame(col_actions_arbre)
        cadre_liste.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(cadre_liste, text="1. Collision Registry", 
                     font=ctk.CTkFont(weight="bold")).pack(pady=5)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", 
                        fieldbackground="#2b2b2b", foreground="white", 
                        borderwidth=0)
        style.map("Treeview", background=[("selected", "#1f538d")])

        self.tree_conflits = ttk.Treeview(cadre_liste, columns=("status",), 
                                          show="tree headings")
        self.tree_conflits.heading("#0", text="Resource / Zone", anchor="w")
        self.tree_conflits.heading("status", text="Status", anchor="center")
        self.tree_conflits.column("#0", width=240, anchor="w")
        self.tree_conflits.column("status", width=110, anchor="center")
        self.tree_conflits.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree_conflits.bind("<<TreeviewSelect>>", 
                                self.sur_conflit_selectionne)

        id_parent = self.tree_conflits.insert("", "end", text="Level01 / Tex00", 
                                              open=True, values=("Pending",))
        for idx, conf in enumerate(self.conflits):
            self.tree_conflits.insert(id_parent, "end", iid=str(idx), 
                                      text=f"Collision #{idx + 1}", 
                                      values=("⚠️ Unresolved",))

        self.cadre_actions = ctk.CTkFrame(col_actions_arbre)
        self.cadre_actions.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(self.cadre_actions, text="2. Selected Zone Resolution", 
                     font=ctk.CTkFont(weight="bold")).pack(pady=5)

        self.lbl_statut_zone = ctk.CTkLabel(
            self.cadre_actions, 
            text="Select an item from the tree.", 
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_statut_zone.pack(pady=5, fill="x")

        self.btn_garder_a = ctk.CTkButton(
            self.cadre_actions, text="Keep Mod A (Active Asset)", 
            font=ctk.CTkFont(weight="bold"), fg_color="#c92a2a", 
            hover_color="#a61e1e", state="disabled", 
            command=lambda: self.enregistrer_decision("A")
        )
        self.btn_garder_a.pack(fill="x", padx=15, pady=5)

        self.btn_prendre_b = ctk.CTkButton(
            self.cadre_actions, text="Replace with Mod B (Incoming)", 
            font=ctk.CTkFont(weight="bold"), fg_color="#1c7ed6", 
            hover_color="#1864ab", state="disabled", 
            command=lambda: self.enregistrer_decision("B")
        )
        self.btn_prendre_b.pack(fill="x", padx=15, pady=5)

        btn_tout_b = ctk.CTkButton(
            self.cadre_actions, text="Overwrite All with Mod B", 
            fg_color="transparent", border_width=1, 
            command=self.tout_resoudre_b
        )
        btn_tout_b.pack(fill="x", padx=15, pady=(10, 5))

        self.btn_appliquer_mats = ctk.CTkButton(
            self.cadre_actions, text="Apply Arbitrations", 
            font=ctk.CTkFont(weight="bold"), fg_color="#495057", 
            state="disabled", command=self.finaliser_fusion_assistee
        )
        self.btn_appliquer_mats.pack(fill="x", padx=15, pady=(5, 15))

        self.cadre_visuel = ctk.CTkFrame(cadre_principal)
        self.cadre_visuel.pack(side="right", fill="both", expand=True, padx=(10, 0))
        ctk.CTkLabel(self.cadre_visuel, text="3. Geo-localized Interactive Viewport", 
                     font=ctk.CTkFont(weight="bold")).pack(pady=5)

        cadre_radios = ctk.CTkFrame(self.cadre_visuel, fg_color="transparent")
        cadre_radios.pack(fill="x", pady=2)
        
        ctk.CTkRadioButton(cadre_radios, text="Mod A View", variable=self.var_vue, 
                           value="A", command=self.rafrachir_apercu).pack(side="left", padx=15)
        ctk.CTkRadioButton(cadre_radios, text="Mod B View", variable=self.var_vue, 
                           value="B", command=self.rafrachir_apercu).pack(side="left", padx=15)
        ctk.CTkRadioButton(cadre_radios, text="Mixed Wireframe", variable=self.var_vue, 
                           value="mixte", command=self.rafrachir_apercu).pack(side="left", padx=15)

        self.var_afficher_modifs = tk.BooleanVar(value=True)
        self.chk_modifs = ctk.CTkCheckBox(
            self.cadre_visuel, text="Render highlighting overlay", 
            variable=self.var_afficher_modifs, command=self.rafrachir_apercu
        )
        self.chk_modifs.pack(anchor="w", padx=15, pady=5)

        self.canvas_local = tk.Canvas(self.cadre_visuel, bg="#1E1E1E", 
                                      bd=0, highlightthickness=0)
        self.canvas_local.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        self.zoom_facteur = 1.0
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
        if not selection: return
        id_selectionne = next(iter(selection))
        if not id_selectionne.isdigit(): return

        idx = int(id_selectionne)
        conflit_courant = self.conflits[idx]

        dec = conflit_courant["decision"]
        statut_txt = "Pending" if dec is None else f"Arbitrated ({dec})"
        self.lbl_statut_zone.configure(
            text=f"Collision #{idx + 1} | Status: {statut_txt}"
        )
        self.btn_garder_a.configure(state="normal")
        self.btn_prendre_b.configure(state="normal")

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

        vue = self.var_vue.get()
        if vue == "A":
            img_view = self.img_a.copy()
        elif vue == "B":
            img_view = self.img_b.copy()
        else:
            img_view = img_base

        draw = ImageDraw.Draw(img_view)
        cx1, cy1, cx2, cy2 = map(int, conflit_courant["rect_inter"])
        if vue == "mixte":
            draw.rectangle([cx1, cy1, cx2, cy2], outline=(255, 235, 59), width=1)

        self.win_assistant.update_idletasks()
        w_canvas = max(400, self.canvas_local.winfo_width())
        h_canvas = max(400, self.canvas_local.winfo_height())
        taille_canvas = min(w_canvas, h_canvas)

        centre_x, centre_y = (cx1 + cx2) // 2, (cy1 + cy2) // 2
        taille_crop = int((img_view.width / 2) / self.zoom_facteur)
        
        crop_box = (
            max(0, centre_x - taille_crop), 
            max(0, centre_y - taille_crop), 
            min(img_view.width, centre_x + taille_crop), 
            min(img_view.height, centre_y + taille_crop)
        )
        
        # Découpage chirurgical en plusieurs instructions courtes pour l'affichage
        img_cropped = img_view.crop(crop_box)
        img_cropped = img_cropped.resize(
            (taille_canvas, taille_canvas), 
            Image.Resampling.NEAREST
        )
        
        self.tk_img_local = ImageTk.PhotoImage(img_cropped)
        self.canvas_local.delete("all")
        self.canvas_local.create_image(
            w_canvas // 2, 
            h_canvas // 2, 
            image=self.tk_img_local, 
            anchor="center"
        )

    def verificar_tous_resolus(self):
        return all(conf["decision"] is not None for conf in self.conflits)

    def enregistrer_decision(self, choix):
        selection = self.tree_conflits.selection()
        if not selection: return
        idx = int(next(iter(selection)))
        self.conflits[idx]["decision"] = choix
        
        symbole = "🔴 Mod A" if choix == "A" else "🔵 Mod B"
        self.tree_conflits.item(str(idx), values=(symbole,))

        if self.verificar_tous_resolus():
            self.btn_appliquer_mats.configure(
                state="normal", 
                fg_color="#2b8a3e", 
                hover_color="#237032"
            )
            self.lbl_statut_zone.configure(
                text="All zones resolved!", 
                text_color="#2b8a3e"
            )
        else:
            if idx + 1 < len(self.conflits):
                self.tree_conflits.selection_clear()
                self.tree_conflits.selection_set(str(idx + 1))
                self.sur_conflit_selectionne(None)

    def tout_resoudre_b(self):
        for idx, conf in enumerate(self.conflits):
            conf["decision"] = "B"
            self.tree_conflits.item(str(idx), values=("🔵 Mod B",))
        self.btn_appliquer_mats.configure(
            state="normal", 
            fg_color="#2b8a3e", 
            hover_color="#237032"
        )
        self.finaliser_fusion_assistee()

    def finaliser_fusion_assistee(self):
        if not self.verificar_tous_resolus(): return
        img_fusion = self.img_ref.copy()
        pix_fusion = img_fusion.load()
        pix_a, pix_b = self.img_a.load(), self.img_b.load()

        for ga in self.groupes_a:
            for (x, y) in ga["pixels"]: pix_fusion[x, y] = pix_a[x, y]
        for gb in self.groupes_b:
            conflits_lies = [c for c in self.conflits if c["rect_b"] == gb["rect"]]
            if not conflits_lies:
                for (x, y) in gb["pixels"]: pix_fusion[x, y] = pix_b[x, y]
            else:
                decision = conflits_lies[0]["decision"]
                pixels_c = set().union(*(c["pixels_b"] for c in conflits_lies))
                for (x, y) in gb["pixels"]:
                    if (x, y) not in pixels_c or decision == "B": 
                        pix_fusion[x, y] = pix_b[x, y]

        self.sauvegarder_et_afficher_images(img_fusion)
        self.win_assistant.destroy()

    def appliquer_fusion_directe(self):
        img_fusion = self.img_ref.copy()
        pix_fusion = img_fusion.load()
        pix_a, pix_b = self.img_a.load(), self.img_b.load()
        for ga in self.groupes_a:
            for (x, y) in ga["pixels"]: pix_fusion[x, y] = pix_a[x, y]
        for gb in self.groupes_b:
            for (x, y) in gb["pixels"]: pix_fusion[x, y] = pix_b[x, y]
        self.sauvegarder_et_afficher_images(img_fusion)
        self.lbl_info.configure(text="[DIRECT MERGE] Successful generation.")

    def sauvegarder_et_afficher_images(self, img_fusion):
        img_debug = self.img_ref.copy()
        draw = ImageDraw.Draw(img_debug)
        
        for ga in self.groupes_a: 
            draw.rectangle(ga["rect"], outline=(255, 0, 0), width=1)
        for gb in self.groupes_b: 
            draw.rectangle(gb["rect"], outline=(0, 120, 255), width=1)

        dossier = os.path.dirname(self.var_ref.get().strip())
        img_debug.save(os.path.join(dossier, "debug_bounding_boxes.png"))
        img_fusion.save(os.path.join(dossier, "fusion_resultat.bmp"))

        self.lbl_info.configure(text=f"Compiled on drive: {dossier}")
        
        self.tk_img_debug = ImageTk.PhotoImage(
            img_debug.resize((320, 320), Image.Resampling.NEAREST)
        )
        self.tk_img_fusion = ImageTk.PhotoImage(
            img_fusion.resize((320, 320), Image.Resampling.NEAREST)
        )
        self.lbl_img_debug.configure(image=self.tk_img_debug)
        self.lbl_img_fusion.configure(image=self.tk_img_fusion)

if __name__ == "__main__":
    app = MultiBoundingBoxApp()
    app.mainloop()