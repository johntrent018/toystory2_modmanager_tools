import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageEnhance
import customtkinter as ctk

# CustomTkinter setup
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TilesetEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Toy Story 2 - Tileset Editor")
        self.root.geometry("1020x820")
        self.root.resizable(True, True)

        # Apply game icon
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
        icon_path = os.path.join(base_path, "assets", "ts2.ico")

        if os.path.exists(icon_path):
            try:
                # Force Windows to reload the window style with the icon
                self.root.wm_iconbitmap(icon_path)
                # CustomTkinter workaround: reinforcement after window mapping
                self.root.after(200, lambda: self.root.wm_iconbitmap(icon_path))
            except Exception:
                pass

        # Fixed transparency bug by assigning explicit frame color
        self.tabview = ctk.CTkTabview(
            self.root, 
            corner_radius=8,
            segmented_button_fg_color="#2B2B2B",
            segmented_button_selected_color="#1F6AA5",
            segmented_button_selected_hover_color="#144870"
        )
        self.tabview.pack(expand=True, fill=tk.BOTH, padx=15, pady=10)

        # Tab naming update using fragment logic
        self.tab_extract = self.tabview.add("Extract from a tileset")
        self.tab_inject = self.tabview.add("Inject into a tileset")

        # Make the tabs look like classic large Tkinter buttons aligned left
        try:
            self.tabview._segmented_button.configure(
                font=("Helvetica", 12, "bold"),
                height=35,
                anchor="w"
            )
        except Exception:
            pass

        self.init_extract_tab()
        self.init_inject_tab()

    def init_extract_tab(self):
        self.ext_image_path = None
        self.ext_original_img = None    
        self.ext_display_img = None     
        self.ext_grid_size = 16         
        self.ext_zoom_factor = 2        
        self.ext_selected_fragments = set() 

        top_frame = ctk.CTkFrame(self.tab_extract, height=60, corner_radius=6)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        top_frame.pack_propagate(False)

        self.btn_ext_load = ctk.CTkButton(top_frame, text="Load Tileset", width=120, font=("Helvetica", 12, "bold"), command=self.ext_load_image)
        self.btn_ext_load.pack(side=tk.LEFT, padx=10, pady=15)

        ctk.CTkLabel(top_frame, text="Grid Snap :", font=("Helvetica", 12)).pack(side=tk.LEFT, padx=(10, 5))
        self.ext_grid_options = {"4x4 (64px)": 4, "8x8 (32px)": 8, "16x16 (16px)": 16, "32x32 (8px)": 32}
        self.ext_grid_menu = ctk.CTkOptionMenu(top_frame, values=list(self.ext_grid_options.keys()), width=130, command=self.ext_change_grid)
        self.ext_grid_menu.set("16x16 (16px)")
        self.ext_grid_menu.pack(side=tk.LEFT, padx=5)

        ctk.CTkLabel(top_frame, text="Zoom :", font=("Helvetica", 12)).pack(side=tk.LEFT, padx=(15, 2))
        ctk.CTkButton(top_frame, text="-", width=32, font=("Arial", 14, "bold"), command=self.ext_zoom_out).pack(side=tk.LEFT, padx=2)
        self.lbl_ext_zoom = ctk.CTkLabel(top_frame, text=f"{self.ext_zoom_factor}x", width=40, font=("Helvetica", 12, "bold"))
        self.lbl_ext_zoom.pack(side=tk.LEFT)
        ctk.CTkButton(top_frame, text="+", width=32, font=("Arial", 14, "bold"), command=self.ext_zoom_in).pack(side=tk.LEFT, padx=2)

        view_frame = ctk.CTkFrame(self.tab_extract, corner_radius=6)
        view_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        view_frame.grid_rowconfigure(0, weight=1)
        view_frame.grid_columnconfigure(0, weight=1)

        self.ext_v_scrollbar = tk.Scrollbar(view_frame, orient=tk.VERTICAL)
        self.ext_v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.ext_h_scrollbar = tk.Scrollbar(view_frame, orient=tk.HORIZONTAL)
        self.ext_h_scrollbar.grid(row=1, column=0, sticky="ew")

        self.ext_canvas_size = 256 * self.ext_zoom_factor
        self.ext_canvas = tk.Canvas(view_frame, bg="#1A1A1A", highlightthickness=0, xscrollcommand=self.ext_h_scrollbar.set, yscrollcommand=self.ext_v_scrollbar.set)
        self.ext_canvas.grid(row=0, column=0, sticky="nsew")
        self.ext_h_scrollbar.config(command=self.ext_canvas.xview)
        self.ext_v_scrollbar.config(command=self.ext_canvas.yview)

        self.ext_canvas.bind("<Button-1>", self.ext_on_canvas_click)
        self.ext_canvas.bind("<Control-MouseWheel>", self.ext_on_mousewheel_zoom)
        self.ext_canvas.bind("<MouseWheel>", lambda e: self.ext_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self.ext_canvas.bind("<Shift-MouseWheel>", lambda e: self.ext_canvas.xview_scroll(int(-1 * (e.delta / 120)), "units"))
        self.ext_canvas.bind("<Button-2>", lambda e: self.ext_canvas.scan_mark(e.x, e.y))
        self.ext_canvas.bind("<B2-Motion>", lambda e: self.ext_canvas.scan_dragto(e.x, e.y, gain=1))

        bottom_frame = ctk.CTkFrame(self.tab_extract, height=90, corner_radius=6)
        bottom_frame.pack(fill=tk.X, padx=5, pady=5)
        self.btn_ext_export = ctk.CTkButton(bottom_frame, text="Export selected fragment as BMP", font=("Helvetica", 13, "bold"), fg_color="#2E7D32", hover_color="#1B5E20", state="disabled", command=self.ext_export_selection)
        self.btn_ext_export.pack(side=tk.TOP, pady=(12, 4), ipadx=15, ipady=3)
        self.lbl_ext_status = ctk.CTkLabel(bottom_frame, text="Please load a Toy Story 2 tileset texture to start.", text_color="#AAAAAA", font=("Helvetica", 11, "italic"))
        self.lbl_ext_status.pack(side=tk.TOP, pady=2)

    def init_inject_tab(self):
        self.inj_base_image_path = None
        self.inj_original_base_img = None  
        self.inj_display_img = None        
        self.inj_grid_size = 16            
        self.inj_zoom_factor = 2           
        self.inj_fragments = []            
        self.inj_active_fragment_idx = None   

        self.inj_dragged_widget_idx = None
        self.inj_insertion_idx = None
        self.inj_fragment_widgets = []        

        top_frame = ctk.CTkFrame(self.tab_inject, height=60, corner_radius=6)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        top_frame.pack_propagate(False)

        self.btn_inj_load_base = ctk.CTkButton(top_frame, text="1. Load Canvas Tileset", font=("Helvetica", 12, "bold"), fg_color="#1E88E5", hover_color="#1565C0", command=self.inj_load_base_image)
        self.btn_inj_load_base.pack(side=tk.LEFT, padx=10, pady=15)

        ctk.CTkLabel(top_frame, text="Grid Snap :", font=("Helvetica", 12)).pack(side=tk.LEFT, padx=(10, 5))
        self.inj_grid_menu = ctk.CTkOptionMenu(top_frame, values=["4x4 (64px)", "8x8 (32px)", "16x16 (16px)", "32x32 (8px)"], width=150, command=self.inj_change_grid)
        self.inj_grid_menu.set("16x16 (16px)")
        self.inj_grid_menu.pack(side=tk.LEFT, padx=5)

        ctk.CTkLabel(top_frame, text="Zoom :", font=("Helvetica", 12)).pack(side=tk.LEFT, padx=(15, 2))
        ctk.CTkButton(top_frame, text="-", width=32, font=("Arial", 14, "bold"), command=self.inj_zoom_out).pack(side=tk.LEFT, padx=2)
        self.lbl_inj_zoom = ctk.CTkLabel(top_frame, text=f"{self.inj_zoom_factor}x", width=40, font=("Helvetica", 12, "bold"))
        self.lbl_inj_zoom.pack(side=tk.LEFT)
        ctk.CTkButton(top_frame, text="+", width=32, font=("Arial", 14, "bold"), command=self.inj_zoom_in).pack(side=tk.LEFT, padx=2)

        main_container = ctk.CTkFrame(self.tab_inject, fg_color="#2B2B2B")
        main_container.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

        view_frame = ctk.CTkFrame(main_container, corner_radius=6)
        view_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        view_frame.grid_rowconfigure(0, weight=1)
        view_frame.grid_columnconfigure(0, weight=1)

        self.inj_v_scrollbar = tk.Scrollbar(view_frame, orient=tk.VERTICAL)
        self.inj_v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.inj_h_scrollbar = tk.Scrollbar(view_frame, orient=tk.HORIZONTAL)
        self.inj_h_scrollbar.grid(row=1, column=0, sticky="ew")

        self.inj_canvas_size = 256 * self.inj_zoom_factor
        self.inj_canvas = tk.Canvas(view_frame, bg="#1A1A1A", highlightthickness=0, xscrollcommand=self.inj_h_scrollbar.set, yscrollcommand=self.inj_v_scrollbar.set)
        self.inj_canvas.grid(row=0, column=0, sticky="nsew")
        self.inj_h_scrollbar.config(command=self.inj_canvas.xview)
        self.inj_v_scrollbar.config(command=self.inj_canvas.yview)

        # Mouse & drag shortcuts binding
        self.inj_canvas.bind("<Button-1>", self.inj_on_canvas_click)      
        self.inj_canvas.bind("<B1-Motion>", self.inj_on_canvas_drag)      
        self.inj_canvas.bind("<Control-MouseWheel>", self.inj_on_mousewheel_zoom)
        self.inj_canvas.bind("<MouseWheel>", lambda e: self.inj_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self.inj_canvas.bind("<Shift-MouseWheel>", lambda e: self.inj_canvas.xview_scroll(int(-1 * (e.delta / 120)), "units"))
        self.inj_canvas.bind("<Button-2>", lambda e: self.inj_canvas.scan_mark(e.x, e.y))
        self.inj_canvas.bind("<B2-Motion>", lambda e: self.inj_canvas.scan_dragto(e.x, e.y, gain=1))

        self.right_frame = ctk.CTkFrame(main_container, width=300, corner_radius=6, fg_color="#2B2B2B")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        self.right_frame.pack_propagate(False)

        ctk.CTkLabel(self.right_frame, text="Fragments Stack (Layers)", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, padx=15, pady=(10, 5))
        self.btn_inj_load_fragment = ctk.CTkButton(self.right_frame, text="+ Inject a custom fragment", font=("Helvetica", 12, "bold"), fg_color="#8E24AA", hover_color="#6A1B9A", state="disabled", command=self.inj_load_fragment_image)
        self.btn_inj_load_fragment.pack(fill=tk.X, padx=15, pady=5)

        self.fragments_container = ctk.CTkScrollableFrame(self.right_frame, fg_color="#1E1E1E")
        self.fragments_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        self.btn_inj_delete_fragment = ctk.CTkButton(self.right_frame, text="Delete selected layer", font=("Helvetica", 12, "bold"), fg_color="#C62828", hover_color="#B71C1C", state="disabled", command=self.inj_delete_active_fragment)
        self.btn_inj_delete_fragment.pack(fill=tk.X, padx=15, pady=10)

        bottom_frame = ctk.CTkFrame(self.tab_inject, height=90, corner_radius=6)
        bottom_frame.pack(fill=tk.X, padx=5, pady=5)
        self.btn_inj_export = ctk.CTkButton(bottom_frame, text="Save injected tileset configuration", font=("Helvetica", 13, "bold"), fg_color="#2E7D32", hover_color="#1B5E20", state="disabled", command=self.inj_save_final_tileset)
        self.btn_inj_export.pack(side=tk.TOP, pady=(12, 4), ipadx=15, ipady=3)
        self.lbl_inj_status = ctk.CTkLabel(bottom_frame, text="Please load a base canvas texture first.", text_color="#AAAAAA", font=("Helvetica", 11, "italic"))
        self.lbl_inj_status.pack(side=tk.TOP, pady=2)

    def ext_load_image(self):
        fp = filedialog.askopenfilename(filetypes=[("BMP Images", "*.bmp")])
        if not fp: return
        try:
            img = Image.open(fp)
            if img.size != (256, 256):
                if not messagebox.askyesno("Dimension Warning", "Image isn't 256x256px. Load anyway?"): return
            self.ext_image_path, self.ext_original_img = fp, img.convert("RGB")
            self.ext_selected_fragments.clear()
            self.ext_update_canvas_dimensions()
            self.btn_ext_export.configure(state="normal")
            self.lbl_ext_status.configure(text=f"Loaded: {os.path.basename(fp)}", text_color="#64B5F6", font=("Helvetica", 11, "bold"))
        except Exception as e: messagebox.showerror("Error", str(e))

    def ext_change_grid(self, selection):
        self.ext_grid_size = self.ext_grid_options[selection]
        self.ext_selected_fragments.clear()
        self.ext_draw_canvas()

    def ext_zoom_in(self):
        if self.ext_zoom_factor < 16: self.ext_zoom_factor += 1; self.ext_update_canvas_dimensions()
    def ext_zoom_out(self):
        if self.ext_zoom_factor > 1: self.ext_zoom_factor -= 1; self.ext_update_canvas_dimensions()
    def ext_on_mousewheel_zoom(self, event):
        if event.delta > 0: self.ext_zoom_in()
        else: self.ext_zoom_out()

    def ext_update_canvas_dimensions(self):
        self.ext_canvas_size = 256 * self.ext_zoom_factor
        self.lbl_ext_zoom.configure(text=f"{self.ext_zoom_factor}x")
        self.ext_canvas.config(scrollregion=(0, 0, self.ext_canvas_size, self.ext_canvas_size))
        self.ext_draw_canvas()

    def ext_draw_canvas(self):
        if self.ext_original_img is None: return
        self.ext_canvas.delete("all")
        res = self.ext_original_img.resize((self.ext_canvas_size, self.ext_canvas_size), resample=Image.Resampling.NEAREST)
        self.ext_display_img = ImageTk.PhotoImage(res)
        self.ext_canvas.create_image(0, 0, anchor=tk.NW, image=self.ext_display_img)
        cs = self.ext_canvas_size / self.ext_grid_size
        for (c, r) in self.ext_selected_fragments:
            x0, y0, x1, y1 = c*cs, r*cs, c*cs+cs, r*cs+cs
            self.ext_canvas.create_rectangle(x0, y0, x1, y1, outline="#F44336", width=3)
            self.ext_canvas.create_line(x0, y0, x1, y1, fill="#F44336", width=2)
            self.ext_canvas.create_line(x1, y0, x0, y1, fill="#F44336", width=2)
        for i in range(1, self.ext_grid_size):
            p = i * cs
            dash = (2, 2) if self.ext_grid_size == 32 and self.ext_zoom_factor < 3 else None
            self.ext_canvas.create_line(p, 0, p, self.ext_canvas_size, fill="#00FF00", dash=dash)
            self.ext_canvas.create_line(0, p, self.ext_canvas_size, p, fill="#00FF00", dash=dash)

    def ext_on_canvas_click(self, event):
        if self.ext_original_img is None: return
        rx, ry = self.ext_canvas.canvasx(event.x), self.ext_canvas.canvasy(event.y)
        cs = self.ext_canvas_size / self.ext_grid_size
        c = min(max(0, int(rx // cs)), self.ext_grid_size - 1)
        r = min(max(0, int(ry // cs)), self.ext_grid_size - 1)
        coord = (c, r)
        if coord in self.ext_selected_fragments: self.ext_selected_fragments.remove(coord)
        else: self.ext_selected_fragments.add(coord)
        self.ext_draw_canvas()
        self.lbl_ext_status.configure(text=f"Selected zones: {len(self.ext_selected_fragments)}", text_color="#FFF176")

    def ext_export_selection(self):
        if not self.ext_selected_fragments: return
        cols, rows = [c for c, r in self.ext_selected_fragments], [r for c, r in self.ext_selected_fragments]
        csv = 256 // self.ext_grid_size
        x0, y0, x1, y1 = min(cols)*csv, min(rows)*csv, (max(cols)+1)*csv, (max(rows)+1)*csv
        sp = filedialog.asksaveasfilename(defaultextension=".bmp", filetypes=[("BMP Images", "*.bmp")], initialfile=f"fragment_{x1-x0}x{y1-y0}.bmp")
        if sp:
            try:
                self.ext_original_img.crop((x0, y0, x1, y1)).save(sp, "BMP")
                messagebox.showinfo("Success", "Fragment extracted successfully!")
            except Exception as e: messagebox.showerror("Error", str(e))

    def refresh_inj_layers_ui(self):
        for w in self.fragments_container.winfo_children(): w.destroy()
        self.inj_fragment_widgets = []
        for idx in range(len(self.inj_fragments) - 1, -1, -1):
            layer = self.inj_fragments[idx]
            act = (idx == self.inj_active_fragment_idx)
            bg, tx = ("#1976D2", "#FFFFFF") if act else ("#2D2D2D", "#DDDDDD")
            f = ctk.CTkFrame(self.fragments_container, fg_color=bg, corner_radius=6, height=38)
            f.pack(fill=tk.X, padx=5, pady=3)
            f.pack_propagate(False)
            lbl = ctk.CTkLabel(f, text=layer["name"], text_color=tx, anchor=tk.W, font=("Helvetica", 11, "bold" if act else "normal"), cursor="hand2")
            lbl.pack(fill=tk.BOTH, expand=True, padx=15)
            lbl.bind("<Button-1>", lambda e, i=idx: self.start_inj_drag(e, i))
            lbl.bind("<B1-Motion>", lambda e, i=idx: self.move_inj_drag(e, i))
            lbl.bind("<ButtonRelease-1>", lambda e: self.end_inj_drag(e))
            self.inj_fragment_widgets.append((idx, f))

    def start_inj_drag(self, event, idx):
        self.inj_active_fragment_idx = idx
        self.inj_dragged_widget_idx = idx
        self.refresh_inj_layers_ui()
        self.inj_draw_canvas()

    def move_inj_drag(self, event, idx):
        if self.inj_dragged_widget_idx is None: return
        my = event.y_root - self.fragments_container.winfo_rooty()
        t_idx = len(self.inj_fragments)
        min_d = 9999
        for _, frame in self.inj_fragment_widgets: frame.configure(border_width=0)
        for orig_idx, frame in self.inj_fragment_widgets:
            fy, fh = frame.winfo_y(), frame.winfo_height()
            d = abs(my - (fy + fh / 2))
            if d < min_d:
                min_d = d
                t_idx = orig_idx + 1 if my < (fy + fh / 2) else orig_idx
        self.inj_insertion_idx = t_idx
        for orig_idx, frame in self.inj_fragment_widgets:
            if self.inj_insertion_idx == orig_idx + 1 or (self.inj_insertion_idx == 0 and orig_idx == 0):
                frame.configure(border_color="#FF5252", border_width=2)
                break

    def end_inj_drag(self, event):
        if self.inj_dragged_widget_idx is not None and self.inj_insertion_idx is not None:
            layer = self.inj_fragments.pop(self.inj_dragged_widget_idx)
            dest = self.inj_insertion_idx
            if dest > self.inj_dragged_widget_idx: dest -= 1
            self.inj_fragments.insert(dest, layer)
            self.inj_active_fragment_idx = dest
        self.inj_dragged_widget_idx = self.inj_insertion_idx = None
        self.refresh_inj_layers_ui()
        self.inj_draw_canvas()

    def inj_load_base_image(self):
        fp = filedialog.askopenfilename(filetypes=[("BMP Images", "*.bmp")])
        if not fp: return
        try:
            img = Image.open(fp)
            if img.size != (256, 256):
                if not messagebox.askyesno("Dimension Warning", "Canvas is not 256x256px. Load anyway?"): return
            self.inj_base_image_path, self.inj_original_base_img = fp, img.convert("RGB")
            self.btn_inj_load_fragment.configure(state="normal")
            self.inj_update_canvas_dimensions()
            self.lbl_inj_status.configure(text="Canvas loaded. Ready to inject custom fragments.", text_color="#64B5F6", font=("Helvetica", 11, "bold"))
        except Exception as e: messagebox.showerror("Error", str(e))

    def inj_load_fragment_image(self):
        fp = filedialog.askopenfilename(filetypes=[("BMP Images", "*.bmp")])
        if not fp: return
        try:
            img = Image.open(fp)
            name = f"Fragment {len(self.inj_fragments) + 1} ({img.size}x{img.size})"
            self.inj_fragments.append({"name": name, "img": img.convert("RGB"), "x": 0, "y": 0})
            self.inj_active_fragment_idx = len(self.inj_fragments) - 1
            self.btn_inj_delete_fragment.configure(state="normal")
            self.btn_inj_export.configure(state="normal")
            self.refresh_inj_layers_ui()
            self.inj_draw_canvas()
            self.lbl_inj_status.configure(text=f"'{name}' added. Drag to place it.", text_color="#FFF176")
        except Exception as e: messagebox.showerror("Error", str(e))

    def inj_delete_active_fragment(self):
        if self.inj_active_fragment_idx is not None and 0 <= self.inj_active_fragment_idx < len(self.inj_fragments):
            self.inj_fragments.pop(self.inj_active_fragment_idx)
            self.inj_active_fragment_idx = len(self.inj_fragments) - 1 if self.inj_fragments else None
            if not self.inj_fragments: self.btn_inj_delete_fragment.configure(state="disabled")
            self.refresh_inj_layers_ui()
            self.inj_draw_canvas()

    def inj_change_grid(self, selection):
        try:
            # Extracts '16' from a string like '16x16 (Pas 16px)'
            self.inj_grid_size = int(selection.split("x")[0])
        except Exception:
            self.inj_grid_size = 16
        if self.inj_active_fragment_idx is not None:
            l = self.inj_fragments[self.inj_active_fragment_idx]
            self.inj_snap_and_update(l["x"], l["y"])
        else:
            self.inj_draw_canvas()

    def inj_zoom_in(self):
        if self.inj_zoom_factor < 16: self.inj_zoom_factor += 1; self.inj_update_canvas_dimensions()
    def inj_zoom_out(self):
        if self.inj_zoom_factor > 1: self.inj_zoom_factor -= 1; self.inj_update_canvas_dimensions()
    def inj_on_mousewheel_zoom(self, event):
        if event.delta > 0: self.inj_zoom_in()
        else: self.inj_zoom_out()

    def inj_update_canvas_dimensions(self):
        self.inj_canvas_size = 256 * self.inj_zoom_factor
        self.lbl_inj_zoom.configure(text=f"{self.inj_zoom_factor}x")
        self.inj_canvas.config(scrollregion=(0, 0, self.inj_canvas_size, self.inj_canvas_size))
        self.inj_draw_canvas()

    def inj_on_canvas_click(self, event):
        self.inj_process_mouse_position(event.x, event.y)

    def inj_on_canvas_drag(self, event):
        self.inj_process_mouse_position(event.x, event.y)

    def inj_process_mouse_position(self, ex, ey):
        if self.inj_original_base_img is None or self.inj_active_fragment_idx is None: return
        rx = self.inj_canvas.canvasx(ex) / self.inj_zoom_factor
        ry = self.inj_canvas.canvasy(ey) / self.inj_zoom_factor
        step = 256 // self.inj_grid_size
        l = self.inj_fragments[self.inj_active_fragment_idx]
        tw, th = l["img"].size
        self.inj_snap_and_update(round(rx - (tw / 2)), round(ry - (th / 2)))

    def inj_snap_and_update(self, sx, sy):
        if self.inj_active_fragment_idx is None: return
        l = self.inj_fragments[self.inj_active_fragment_idx]
        tw, th = l["img"].size
        sx, sy = min(max(0, sx), 256 - tw), min(max(0, sy), 256 - th)
        step = 256 // self.inj_grid_size
        l["x"], l["y"] = int(round(sx / step) * step), int(round(sy / step) * step)
        self.inj_draw_canvas()

    def inj_draw_canvas(self):
        if self.inj_original_base_img is None: return
        self.inj_canvas.delete("all")
        if self.inj_fragments:
            render_img = ImageEnhance.Brightness(self.inj_original_base_img).enhance(0.45)
        else: render_img = self.inj_original_base_img.copy()
        for layer in self.inj_fragments: render_img.paste(layer["img"], (layer["x"], layer["y"]))
        res = render_img.resize((self.inj_canvas_size, self.inj_canvas_size), resample=Image.Resampling.NEAREST)
        self.inj_display_img = ImageTk.PhotoImage(res)
        self.inj_canvas.create_image(0, 0, anchor=tk.NW, image=self.inj_display_img)
        cs = self.inj_canvas_size / self.inj_grid_size
        for i in range(1, self.inj_grid_size):
            p = i * cs
            dash = (2, 2) if self.inj_grid_size == 32 and self.inj_zoom_factor < 3 else None
            self.inj_canvas.create_line(p, 0, p, self.inj_canvas_size, fill="#00FF00", dash=dash)
            self.inj_canvas.create_line(0, p, self.inj_canvas_size, p, fill="#00FF00", dash=dash)
        if self.inj_active_fragment_idx is not None and 0 <= self.inj_active_fragment_idx < len(self.inj_fragments):
            al = self.inj_fragments[self.inj_active_fragment_idx]
            tw, th = al["img"].size
            tx0, ty0 = al["x"] * self.inj_zoom_factor, al["y"] * self.inj_zoom_factor
            self.inj_canvas.create_rectangle(tx0, ty0, tx0+(tw*self.inj_zoom_factor), ty0+(th*self.inj_zoom_factor), outline="#FFFF00", width=3)

    def inj_save_final_tileset(self):
        if self.inj_original_base_img is None: return
        fo = self.inj_original_base_img.copy()
        for l in self.inj_fragments: fo.paste(l["img"], (l["x"], l["y"]))
        sp = filedialog.asksaveasfilename(defaultextension=".bmp", filetypes=[("BMP Images", "*.bmp")], initialfile="tileset_modded.bmp")
        if sp:
            try: fo.save(sp, "BMP"); messagebox.showinfo("Success", "Modded tileset saved successfully!")
            except Exception as e: messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    app_root = ctk.CTk()
    app = TilesetEditorApp(app_root)
    app_root.mainloop()