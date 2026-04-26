import ctypes
import pefile
import pymem
import pymem.ressources.structure
import pymem.ressources.kernel32
import os

# Define required constants if not using the full import
PAGE_EXECUTE_READWRITE = 0x40
MEM_COMMIT = 0x00001000
MEM_RESERVE = 0x00002000

class ManualMapInjector:
    def __init__(self, process_id):
        self.process_id = process_id
        try:
            self.pm = pymem.Pymem()
            self.pm.open_process_from_id(process_id)
        except Exception as e:
            self.pm = None
            self.error = str(e)

    def get_proc_address(self, module_name, func_name):
        """Get the address of a function in the target process."""
        # 1. Get local handle and address
        local_handle = pymem.ressources.kernel32.GetModuleHandleW(module_name)
        if not local_handle:
            # Try to load it locally if not present
            local_handle = pymem.ressources.kernel32.LoadLibraryW(module_name)
        
        if not local_handle:
            return 0

        func_bytes = func_name.encode('utf-8') if isinstance(func_name, str) else func_name
        local_func_addr = pymem.ressources.kernel32.GetProcAddress(local_handle, func_bytes)
        if not local_func_addr:
            return 0

        # 2. Calculate offset
        offset = local_func_addr - local_handle

        # 3. Get remote module base
        remote_module = pymem.process.module_from_name(self.pm.process_handle, module_name)
        if not remote_module:
            return 0

        return remote_module.lpBaseOfDll + offset

    def inject_load_library(self, dll_path):
        """Standard injection using LoadLibraryA."""
        if not self.pm:
            return False, "Not attached."
        
        try:
            # 1. Allocate memory for the DLL path string
            path_bytes = dll_path.encode('ascii') + b'\x00'
            remote_path = self.pm.allocate(len(path_bytes))
            
            # 2. Write the path string
            self.pm.write_bytes(remote_path, path_bytes, len(path_bytes))
            
            # 3. Get address of LoadLibraryA in target
            load_library = self.get_proc_address("kernel32.dll", "LoadLibraryA")
            if not load_library:
                return False, "Failed to locate LoadLibraryA in target process."
            
            # 4. Start thread to call LoadLibraryA(remote_path)
            self.pm.start_thread(load_library, remote_path)
            
            return True, f"Standard injection successful via LoadLibraryA"
        except Exception as e:
            return False, f"LoadLibrary injection failed: {e}"

    def inject(self, dll_path, erase_headers=False, use_thread_hijack=False):
        """Perform manual map injection."""
        if not self.pm:
            return False, f"Not attached: {getattr(self, 'error', 'Unknown error')}"

        if not os.path.exists(dll_path):
            return False, f"DLL file not found: {dll_path}"

        try:
            # 1. Load and parse DLL
            pe = pefile.PE(dll_path)
            
            # Check for architecture mismatch
            target_is_64 = self.pm.is_64_bit
            dll_is_64 = pe.FILE_HEADER.Machine == 0x8664
            
            if target_is_64 != dll_is_64:
                return False, f"Architecture mismatch: DLL is {'x64' if dll_is_64 else 'x86'} but target process is {'x64' if target_is_64 else 'x86'}"

            dll_data = open(dll_path, 'rb').read()
            
            # 2. Allocate memory in target process
            image_size = pe.OPTIONAL_HEADER.SizeOfImage
            remote_base = self.pm.allocate(image_size)
            
            # 3. Write Headers
            header_size = pe.OPTIONAL_HEADER.SizeOfHeaders
            self.pm.write_bytes(remote_base, dll_data[:header_size], header_size)
            
            # 4. Write Sections
            for section in pe.sections:
                section_address = remote_base + section.VirtualAddress
                section_data = section.get_data()
                if section_data:
                    self.pm.write_bytes(section_address, section_data, len(section_data))

            # 5. Base Relocations
            self._apply_relocations(pe, remote_base)

            # 6. Resolve Imports
            self._resolve_imports(pe, remote_base)
            
            # 7. Execution
            entry_point = remote_base + pe.OPTIONAL_HEADER.AddressOfEntryPoint
            
            if use_thread_hijack:
                success, msg = self._thread_hijack(entry_point)
                if not success:
                    return False, msg
            else:
                # Standard Remote Thread
                try:
                    self.pm.start_thread(entry_point)
                except Exception as e:
                    return False, f"Failed to start thread: {e}"

            # 8. Stealth: Erase Headers
            if erase_headers:
                try:
                    empty_headers = b'\x00' * header_size
                    self.pm.write_bytes(remote_base, empty_headers, header_size)
                except:
                    pass # Non-critical failure

            return True, f"Stealthily injected at {hex(remote_base)}"

        except Exception as e:
            return False, f"Injection failed: {str(e)}"

    def _resolve_imports(self, pe, remote_base):
        if not hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
            return

        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            dll_name = entry.dll.decode('utf-8')
            
            # Ensure the dependency DLL is loaded in the target process
            # In a full injector, we'd use LoadLibrary in the target if not found
            # For this utility, we assume common DLLs (user32, kernel32) are present
            target_module = pymem.process.module_from_name(self.pm.process_handle, dll_name)
            if not target_module:
                continue

            for imp in entry.imports:
                if imp.name:
                    func_name = imp.name.decode('utf-8')
                    func_addr = self.get_proc_address(dll_name, func_name)
                else:
                    # Import by ordinal
                    func_addr = self.get_proc_address(dll_name, imp.ordinal)
                
                if func_addr:
                    # Write the address to the IAT
                    iat_address = remote_base + imp.address - pe.OPTIONAL_HEADER.ImageBase
                    if pe.FILE_HEADER.Machine == 0x8664:
                        self.pm.write_longlong(remote_base + (imp.address - pe.OPTIONAL_HEADER.ImageBase), func_addr)
                    else:
                        self.pm.write_int(remote_base + (imp.address - pe.OPTIONAL_HEADER.ImageBase), func_addr)

    def _apply_relocations(self, pe, remote_base):
        delta = remote_base - pe.OPTIONAL_HEADER.ImageBase
        if delta == 0:
            return

        if hasattr(pe, 'DIRECTORY_ENTRY_BASERELOC'):
            for base_reloc in pe.DIRECTORY_ENTRY_BASERELOC:
                for reloc in base_reloc.entries:
                    if reloc.type == 0: # IMAGE_REL_BASED_ABSOLUTE
                        continue
                    
                    # The absolute RVA is stored in the 'rva' attribute
                    reloc_address = remote_base + reloc.rva
                    
                    try:
                        if pe.FILE_HEADER.Machine == 0x8664: # x64
                            current_val = self.pm.read_longlong(reloc_address)
                            self.pm.write_longlong(reloc_address, current_val + delta)
                        else: # x86
                            current_val = self.pm.read_int(reloc_address)
                            self.pm.write_int(reloc_address, current_val + delta)
                    except:
                        continue

    def _thread_hijack(self, entry_point):
        """Stealthy execution via thread hijacking."""
        # Note: This is a simplified conceptual implementation.
        # Real thread hijacking requires finding a suitable thread, suspending it,
        # getting context, setting RIP/EIP, and resuming.
        # Python's pymem doesn't expose full Thread Context API directly easily,
        # so we'd typically use ctypes to call SuspendThread, GetThreadContext, etc.
        
        # For now, we'll log that it's a TODO or use a basic remote thread if not fully implemented.
        # Implementing full context manipulation in Python via ctypes:
        return False, "Thread Hijacking not fully implemented in this prototype."
