import os
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Global UI configuration
ctk.set_appearance_mode("System")  # Adapts to Windows theme (Dark/Light)
ctk.set_default_color_theme("blue")

# Executable patching targets
PATCH_OFFSET = 0x000B071E
BYTES_RESTRICTED = b'\x8B\xC1'
BYTES_UNRESTRICTED = b'\x90\x90'


class ToyStory2Patcher(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Toy Story 2 - Texture Size Unlocker")
        self.geometry("550x320")
        self.resizable(False, False)
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, "ts2.ico")
        
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        # ------------------------

        self.exe_path = ""
        self.lock_switch = (
            True  # Prevents triggering the patch during switch initialization
        )

        self.create_interface()

    def create_interface(self):
        # Main Title Label
        self.lbl_title = ctk.CTkLabel(
            self,
            text="Check if your Toy Story 2 game supports high resolution textures",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.lbl_title.pack(pady=(20, 15))

        # File Selection Frame
        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.pack(fill="x", padx=25, pady=5)

        self.entry_path = ctk.CTkEntry(
            self.file_frame,
            placeholder_text="Select your toy2.exe file...",
            width=360,
        )
        self.entry_path.pack(side="left", padx=(10, 5), pady=10)

        self.btn_browse = ctk.CTkButton(
            self.file_frame,
            text="Browse",
            width=100,
            command=self.browse_file,
        )
        self.btn_browse.pack(side="right", padx=(5, 10), pady=10)

        # Visual Status Label
        self.lbl_status = ctk.CTkLabel(
            self,
            text="Please load a toy2.exe file to analyze its state.",
            font=ctk.CTkFont(size=13, slant="italic"),
            text_color="white",
        )
        self.lbl_status.pack(pady=(25, 10))

        # Toggle Switch (Disabled until a file is loaded)
        self.switch_patch = ctk.CTkSwitch(
            self,
            text="Enable the support of HD textures (over 256x256 pixels)",
            font=ctk.CTkFont(size=13, weight="normal"),
            command=self.toggle_patch,
            state="disabled",
        )
        self.switch_patch.pack(pady=15)

    def browse_file(self):
        path = filedialog.askopenfilename(
            title="Select toy2.exe", filetypes=[("Executable", "*.exe")]
        )
        if path:
            self.exe_path = path
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, path)
            self.analyze_initial_status()

    def analyze_initial_status(self):
        if not os.path.exists(self.exe_path):
            return

        try:
            with open(self.exe_path, "rb") as f:
                f.seek(PATCH_OFFSET)
                current_bytes = f.read(2)

            self.lock_switch = True  # Locks the switch UI events
            self.switch_patch.configure(state="normal")

            if current_bytes == BYTES_RESTRICTED:
                self.lbl_status.configure(
                    text="Actual state : RESTRICTED (Textures limited to 256x256 pixels)",
                    text_color="#D32F2F",
                )
                self.switch_patch.deselect()  # Unchecked state
            elif current_bytes == BYTES_UNRESTRICTED:
                self.lbl_status.configure(
                    text="Actual state : UNRESTRICTED (HD Textures allowed !)",
                    text_color="#388E3C",
                )
                self.switch_patch.select()  # Checked state
            else:
                self.lbl_status.configure(
                    text="Actual state : UNKNOWN (abnormal state or wrong executable uploaded)",
                    text_color="#F57C00",
                )
                self.switch_patch.configure(state="disabled")

            self.lock_switch = False  # Unlocks the switch UI events

        except Exception as e:
            messagebox.showerror("Analysis Error", f"Unable to analyze the file :\n{str(e)}")

    def toggle_patch(self):
        # Ignore event if the switch is updated programmatically or if no file is selected
        if self.lock_switch or not self.exe_path:
            return

        # Determine target bytes based on switch position
        hd_mode_active = self.switch_patch.get()
        bytes_to_write = BYTES_UNRESTRICTED if hd_mode_active else BYTES_RESTRICTED

        try:
            # Inline binary write operation at the specific file offset
            with open(self.exe_path, "r+b") as f:
                f.seek(PATCH_OFFSET)
                f.write(bytes_to_write)

            # Update UI labels upon successful write
            if hd_mode_active:
                self.lbl_status.configure(
                    text="Actual state : UNRESTRICTED (HD Textures allowed !)",
                    text_color="#388E3C",
                )
            else:
                self.lbl_status.configure(
                    text="Actual state : RESTRICTED (Textures limited to 256x256 pixels)",
                    text_color="#D32F2F",
                )

        except PermissionError:
            messagebox.showerror(
                "Permission Error",
                "Unable to patch the file. Please check if this executable isn't already launched or run this app as Administrator.",
            )
            # Revert switch to previous configuration on failure
            self.analyze_initial_status()
        except Exception as e:
            messagebox.showerror("Patching Error", f"An error occurred during the application of the patch :\n{str(e)}")
            self.analyze_initial_status()


if __name__ == "__main__":
    app = ToyStory2Patcher()
    app.mainloop()
