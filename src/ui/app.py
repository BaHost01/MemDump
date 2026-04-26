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

        self.refresh_btn = ctk.CTkButton(self.top_frame, text="Refresh", command=self.refresh_processes, width=100)
        self.refresh_btn.grid(row=0, column=2, padx=10, pady=10)

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

        self.dump_mod_label = ctk.CTkLabel(self.tab_dumper, text="Module Name (e.g., client.dll):")
        self.dump_mod_label.pack(pady=(20, 0))

        self.dump_mod_entry = ctk.CTkEntry(self.tab_dumper, placeholder_text="Enter module name...")
        self.dump_mod_entry.pack(pady=10, padx=50, fill="x")

        self.dump_btn = ctk.CTkButton(self.tab_dumper, text="Dump Module", command=self.dump_module)
        self.dump_btn.pack(pady=20)

    def _setup_injector_tab(self):
        self.tab_injector.grid_columnconfigure(0, weight=1)

        self.dll_path_label = ctk.CTkLabel(self.tab_injector, text="No DLL Selected")
        self.dll_path_label.pack(pady=(20, 0))

        self.select_dll_btn = ctk.CTkButton(self.tab_injector, text="Select DLL", command=self.select_dll)
        self.select_dll_btn.pack(pady=10)

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
            processes = self.memory_manager.get_processes()
            proc_strings = [f"{p['name']} ({p['pid']})" for p in processes]
            self.proc_combo.configure(values=proc_strings)
            if proc_strings:
                self.proc_combo.set(proc_strings[0])
            self.log(f"Found {len(processes)} processes.", "SUCCESS")
        except Exception as e:
            self.log(f"Failed to refresh processes: {e}", "ERROR")

    def on_process_select(self, value):
        try:
            pid = int(value.split("(")[-1].strip(")"))
            self.selected_process = pid
            self.log(f"Attached to target PID: {pid}", "SUCCESS")
        except:
            self.selected_process = None
            self.log("Invalid process selection.", "WARNING")

    def dump_module(self):
        if not self.selected_process:
            messagebox.showwarning("Warning", "Please select a process first.")
            return

        module_name = self.dump_mod_entry.get()
        if not module_name:
            messagebox.showwarning("Warning", "Please enter a module name.")
            return

        save_path = filedialog.asksaveasfilename(defaultextension=".bin", initialfile=f"dump_{module_name}")
        if not save_path:
            return

        self.log(f"Starting dump of {module_name}...")
        
        def _task():
            if self.memory_manager.attach(self.selected_process):
                success, msg = self.memory_manager.dump_module(module_name, save_path)
                if success:
                    self.log(msg, "SUCCESS")
                    messagebox.showinfo("Success", msg)
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

    def inject_dll(self):
        if not self.selected_process or not self.dll_path:
            messagebox.showwarning("Warning", "Select a process and a DLL.")
            return

        self.log(f"Initiating stealth injection into PID {self.selected_process}...", "WARNING")
        
        def _task():
            injector = ManualMapInjector(self.selected_process)
            success, msg = injector.inject(
                self.dll_path, 
                erase_headers=self.erase_headers_var.get(),
                use_thread_hijack=self.hijack_var.get()
            )
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
