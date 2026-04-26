import customtkinter as ctk
from tkinter import filedialog, messagebox
from src.core.memory import MemoryManager
from src.core.injector import ManualMapInjector
import threading
import os

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class MemDumpApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MemDump - Stealth Memory Tool")
        self.geometry("800x600")

        self.memory_manager = MemoryManager()
        self.selected_process = None

        self._build_ui()
        self.refresh_processes()

    def _build_ui(self):
        # Grid configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Top Frame: Process Selection ---
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        self.top_frame.grid_columnconfigure(1, weight=1)

        self.proc_label = ctk.CTkLabel(self.top_frame, text="Process:")
        self.proc_label.grid(row=0, column=0, padx=10, pady=10)

        self.proc_combo = ctk.CTkComboBox(self.top_frame, values=[], command=self.on_process_select)
        self.proc_combo.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.proc_combo.bind("<KeyRelease>", self.filter_process_list)

        self.filter_system_var = ctk.BooleanVar(value=True)
        self.filter_cb = ctk.CTkCheckBox(self.top_frame, text="Hide System", variable=self.filter_system_var, command=self.refresh_processes, width=100)
        self.filter_cb.grid(row=0, column=2, padx=10, pady=10)

        self.refresh_btn = ctk.CTkButton(self.top_frame, text="Refresh", command=self.refresh_processes, width=100)
        self.refresh_btn.grid(row=0, column=3, padx=10, pady=10)

        # Cache for all loaded processes
        self.all_processes = []

        # --- Middle: TabView ---
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        self.tab_dumper = self.tabview.add("Dumper")
        self.tab_injector = self.tabview.add("Injector")

        self._setup_dumper_tab()
        self._setup_injector_tab()

        # --- Bottom: Log Console ---
        self.log_text = ctk.CTkTextbox(self, height=150)
        self.log_text.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.log_text.configure(state="disabled")

    def _setup_dumper_tab(self):
        self.tab_dumper.grid_columnconfigure(0, weight=1)

        self.mod_frame = ctk.CTkFrame(self.tab_dumper)
        self.mod_frame.pack(pady=20, padx=50, fill="x")
        self.mod_frame.grid_columnconfigure(1, weight=1)

        self.dump_mod_label = ctk.CTkLabel(self.mod_frame, text="Select Module:")
        self.dump_mod_label.grid(row=0, column=0, padx=10, pady=10)

        self.mod_combo = ctk.CTkComboBox(self.mod_frame, values=[], command=self.on_module_select)
        self.mod_combo.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.mod_combo.bind("<KeyRelease>", self.filter_module_list)

        self.refresh_mod_btn = ctk.CTkButton(self.mod_frame, text="↻", width=30, command=self.refresh_modules)
        self.refresh_mod_btn.grid(row=0, column=2, padx=10, pady=10)

        self.info_box = ctk.CTkTextbox(self.tab_dumper, height=100)
        self.info_box.pack(pady=10, padx=50, fill="x")
        self.info_box.insert("0.0", "Module Info:\nBase Address: -\nImage Size: -")
        self.info_box.configure(state="disabled")

        self.dump_btn = ctk.CTkButton(self.tab_dumper, text="Dump Selected Module", command=self.dump_module, fg_color="blue", hover_color="darkblue")
        self.dump_btn.pack(pady=20)

        self.all_modules = []

    def _setup_injector_tab(self):
        self.tab_injector.grid_columnconfigure(0, weight=1)

        self.dll_path_label = ctk.CTkLabel(self.tab_injector, text="No DLL Selected")
        self.dll_path_label.pack(pady=(20, 0))

        self.select_dll_btn = ctk.CTkButton(self.tab_injector, text="Select DLL", command=self.select_dll)
        self.select_dll_btn.pack(pady=10)

        self.method_label = ctk.CTkLabel(self.tab_injector, text="Injection Method:")
        self.method_label.pack(pady=(10, 0))
        
        self.method_var = ctk.StringVar(value="Manual Map")
        self.method_combo = ctk.CTkComboBox(self.tab_injector, values=["Manual Map", "LoadLibrary"], variable=self.method_var, command=self.toggle_stealth_options)
        self.method_combo.pack(pady=10)

        self.stealth_frame = ctk.CTkFrame(self.tab_injector)
        self.stealth_frame.pack(pady=10)

        self.erase_headers_var = ctk.BooleanVar(value=False)
        self.erase_headers_cb = ctk.CTkCheckBox(self.stealth_frame, text="Erase PE Headers", variable=self.erase_headers_var)
        self.erase_headers_cb.pack(side="left", padx=10)

        self.hijack_var = ctk.BooleanVar(value=False)
        self.hijack_cb = ctk.CTkCheckBox(self.stealth_frame, text="Thread Hijacking", variable=self.hijack_var)
        self.hijack_cb.pack(side="left", padx=10)

        self.inject_btn = ctk.CTkButton(self.tab_injector, text="Inject DLL", command=self.inject_dll, fg_color="green", hover_color="darkgreen")
        self.inject_btn.pack(pady=20)

        self.dll_path = None

    # --- Actions ---

    def log(self, message, level="INFO"):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        color_tag = f"level_{level.lower()}"
        
        # Define tags if they don't exist
        if level == "ERROR":
            self.log_text.tag_config("level_error", foreground="red")
        elif level == "SUCCESS":
            self.log_text.tag_config("level_success", foreground="green")
        elif level == "WARNING":
            self.log_text.tag_config("level_warning", foreground="yellow")

        msg_formatted = f"[{timestamp}] [{level}] {message}\n"
        self.log_text.insert("end", msg_formatted, color_tag)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def refresh_processes(self):
        self.log("Refreshing process list...")
        try:
            self.all_processes = self.memory_manager.get_processes(filter_system=self.filter_system_var.get())
            proc_strings = [f"{p['name']} ({p['pid']})" for p in self.all_processes]
            self.proc_combo.configure(values=proc_strings)
            if proc_strings:
                self.proc_combo.set(proc_strings[0])
            self.log(f"Found {len(self.all_processes)} processes.", "SUCCESS")
        except Exception as e:
            self.log(f"Failed to refresh processes: {e}", "ERROR")

    def filter_process_list(self, event):
        search_query = self.proc_combo.get().lower()
        filtered = [f"{p['name']} ({p['pid']})" for p in self.all_processes if search_query in p['name'].lower()]
        self.proc_combo.configure(values=filtered)

    def on_process_select(self, value):
        try:
            pid = int(value.split("(")[-1].strip(")"))
            self.selected_process = pid
            self.log(f"Attached to target PID: {pid}", "SUCCESS")
            # Automatically refresh modules for the dumper tab
            self.refresh_modules()
        except:
            self.selected_process = None
            self.log("Invalid process selection.", "WARNING")

    def refresh_modules(self):
        if not self.selected_process:
            return

        self.log("Fetching modules for selected process...")
        def _task():
            if self.memory_manager.attach(self.selected_process):
                self.all_modules = self.memory_manager.get_modules()
                mod_strings = [m['name'] for m in self.all_modules]
                self.mod_combo.configure(values=mod_strings)
                if mod_strings:
                    self.mod_combo.set(mod_strings[0])
                    self.on_module_select(mod_strings[0])
                self.log(f"Loaded {len(self.all_modules)} modules.", "SUCCESS")
            else:
                self.log("Failed to attach for module enumeration.", "ERROR")

        threading.Thread(target=_task).start()

    def filter_module_list(self, event):
        search_query = self.mod_combo.get().lower()
        filtered = [m['name'] for m in self.all_modules if search_query in m['name'].lower()]
        self.mod_combo.configure(values=filtered)

    def on_module_select(self, value):
        module = next((m for m in self.all_modules if m['name'] == value), None)
        if module:
            self.info_box.configure(state="normal")
            self.info_box.delete("0.0", "end")
            info = f"Module Info:\nBase Address: {module['base_hex']}\nImage Size: {module['size']}\nPath: {module['path']}"
            self.info_box.insert("0.0", info)
            self.info_box.configure(state="disabled")

    def dump_module(self):
        if not self.selected_process:
            messagebox.showwarning("Warning", "Please select a process first.")
            return

        module_name = self.mod_combo.get()
        if not module_name:
            messagebox.showwarning("Warning", "Please select a module to dump.")
            return

        save_path = filedialog.asksaveasfilename(defaultextension=".bin", initialfile=f"dump_{module_name}")
        if not save_path:
            return

        self.log(f"Starting dump of {module_name}...")
        
        def _task():
            import json
            if self.memory_manager.attach(self.selected_process):
                success, msg, metadata = self.memory_manager.dump_module(module_name, save_path)
                if success:
                    # Save metadata to JSON
                    json_path = os.path.splitext(save_path)[0] + ".json"
                    with open(json_path, 'w') as jf:
                        json.dump(metadata, jf, indent=4)
                    
                    self.log(f"{msg}. Metadata saved to {os.path.basename(json_path)}", "SUCCESS")
                    messagebox.showinfo("Success", f"{msg}\nMetadata: {os.path.basename(json_path)}")
                else:
                    self.log(msg, "ERROR")
                    messagebox.showerror("Error", msg)
            else:
                self.log("Failed to attach to process for dumping.", "ERROR")

        threading.Thread(target=_task).start()

    def select_dll(self):
        path = filedialog.askopenfilename(filetypes=[("DLL files", "*.dll")])
        if path:
            self.dll_path = path
            self.dll_path_label.configure(text=os.path.basename(path))
            self.log(f"Selected DLL: {os.path.basename(path)}", "INFO")

    def toggle_stealth_options(self, value):
        state = "normal" if value == "Manual Map" else "disabled"
        self.erase_headers_cb.configure(state=state)
        self.hijack_cb.configure(state=state)

    def inject_dll(self):
        if not self.selected_process or not self.dll_path:
            messagebox.showwarning("Warning", "Select a process and a DLL.")
            return

        method = self.method_var.get()
        self.log(f"Initiating {method} injection into PID {self.selected_process}...", "WARNING")
        
        def _task():
            injector = ManualMapInjector(self.selected_process)
            
            if method == "Manual Map":
                success, msg = injector.inject(
                    self.dll_path, 
                    erase_headers=self.erase_headers_var.get(),
                    use_thread_hijack=self.hijack_var.get()
                )
            else:
                success, msg = injector.inject_load_library(self.dll_path)

            if success:
                self.log(msg, "SUCCESS")
                messagebox.showinfo("Injection Result", msg)
            else:
                self.log(msg, "ERROR")
                messagebox.showerror("Injection Error", msg)

        threading.Thread(target=_task).start()

if __name__ == "__main__":
    app = MemDumpApp()
    app.mainloop()
