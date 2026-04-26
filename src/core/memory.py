import pymem
import pymem.process
import os

class MemoryManager:
    def __init__(self):
        self.pm = None
        self.process_name = None
        self.process_id = None

    def get_processes(self, filter_system=True):
        """Enumerate running processes with optional system process filtering."""
        processes = []
        # Expanded list of common system process names
        system_procs = {
            "svchost.exe", "conhost.exe", "wininit.exe", "winlogon.exe", "lsass.exe",
            "services.exe", "smss.exe", "csrss.exe", "registry", "memory compression",
            "idle", "system", "spoolsv.exe", "searchindexer.exe", "runtimebroker.exe",
            "shellexperiencehost.exe", "searchhost.exe", "startmenuexperiencehost.exe",
            "taskhostw.exe", "fontdrvhost.exe", "dwm.exe", "ctfmon.exe", "sihost.exe",
            "smartscreen.exe", "dllhost.exe", "audiodg.exe", "wudfhost.exe"
        }

        for process in pymem.process.list_processes():
            try:
                name = process.szExeFile.decode('utf-8', errors='ignore')
                if filter_system and name.lower() in system_procs:
                    continue
                
                processes.append({
                    'name': name,
                    'pid': process.th32ProcessID
                })
            except:
                continue
        return sorted(processes, key=lambda x: x['name'].lower())

    def attach(self, process_id):
        """Attach to a process by ID."""
        try:
            self.pm = pymem.Pymem()
            self.pm.open_process_from_id(process_id)
            self.process_id = process_id
            return True
        except Exception as e:
            return False

    def get_modules(self):
        """Get all modules for the currently attached process."""
        if not self.pm:
            return []
        
        modules = []
        try:
            for module in self.pm.list_modules():
                modules.append({
                    'name': module.name,
                    'base': module.lpBaseOfDll,
                    'base_hex': hex(module.lpBaseOfDll),
                    'size': hex(module.SizeOfImage),
                    'path': module.filename
                })
        except Exception as e:
            print(f"Error listing modules: {e}")
            
        return sorted(modules, key=lambda x: x['name'].lower())

    def dump_module(self, module_name, output_path):
        """Dump a specific module from the attached process."""
        if not self.pm:
            return False, "Not attached to any process.", None

        try:
            module = pymem.process.module_from_name(self.pm.process_handle, module_name)
            if not module:
                return False, f"Module {module_name} not found.", None

            module_data = self.pm.read_bytes(module.lpBaseOfDll, module.SizeOfImage)
            
            with open(output_path, 'wb') as f:
                f.write(module_data)
            
            import pefile
            # Parse the dumped data to get entry point
            pe = pefile.PE(data=module_data)
            entry_point_offset = pe.OPTIONAL_HEADER.AddressOfEntryPoint
            
            metadata = {
                "module_name": module_name,
                "base_address": hex(module.lpBaseOfDll),
                "entry_point": hex(module.lpBaseOfDll + entry_point_offset),
                "entry_point_offset": hex(entry_point_offset),
                "image_size": hex(module.SizeOfImage),
                "path": module.filename,
                "dump_time": str(__import__('datetime').datetime.now())
            }
            
            return True, f"Successfully dumped {module_name}", metadata
        except Exception as e:
            return False, str(e), None

    def dump_region(self, base_address, size, output_path):
        """Dump a specific memory region."""
        if not self.pm:
            return False, "Not attached to any process."

        try:
            data = self.pm.read_bytes(base_address, size)
            with open(output_path, 'wb') as f:
                f.write(data)
            return True, f"Successfully dumped region at {hex(base_address)} to {output_path}"
        except Exception as e:
            return False, str(e)
