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
        # List of common system process names to hide if filtering is enabled
        system_procs = {
            "svchost.exe", "conhost.exe", "wininit.exe", "winlogon.exe", "lsass.exe",
            "services.exe", "smss.exe", "csrss.exe", "registry", "memory compression",
            "idle", "system", "spoolsv.exe", "searchindexer.exe", "runtimebroker.exe"
        }

        for process in pymem.process.list_processes():
            name = process.szExeFile.decode('utf-8', errors='ignore')
            if filter_system and name.lower() in system_procs:
                continue
            
            processes.append({
                'name': name,
                'pid': process.th32ProcessID
            })
        return sorted(processes, key=lambda x: x['name'].lower())

    def attach(self, process_id):
        """Attach to a process by ID."""
        try:
            self.pm = pymem.Pymem()
            self.pm.open_process_from_id(process_id)
            self.process_id = process_id
            return True
        except Exception as e:
            print(f"Error attaching to process {process_id}: {e}")
            return False

    def dump_module(self, module_name, output_path):
        """Dump a specific module from the attached process."""
        if not self.pm:
            return False, "Not attached to any process."

        try:
            module = pymem.process.module_from_name(self.pm.process_handle, module_name)
            if not module:
                return False, f"Module {module_name} not found."

            module_data = self.pm.read_bytes(module.lpBaseOfDll, module.SizeOfImage)
            
            with open(output_path, 'wb') as f:
                f.write(module_data)
            
            return True, f"Successfully dumped {module_name} to {output_path}"
        except Exception as e:
            return False, str(e)

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
