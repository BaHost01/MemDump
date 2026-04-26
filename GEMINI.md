# MemDump Project Context

## Project Overview
MemDump is a stealthy, Windows-targeted utility designed for **Memory Dumping** and **Manual Map Injection**. It is implemented in **Python** and features a modern graphical interface built with `CustomTkinter`.

## Technical Stack
- **Language:** Python 3.10+
- **UI Framework:** CustomTkinter
- **Core Libraries:** `pymem`, `pefile`, `ctypes`
- **Distribution:** PyInstaller (Standalone `.exe`)
- **CI/CD:** GitHub Actions (Automated Release on tags)

## Directory Structure
- `src/main.py`: Application entry point.
- `src/core/memory.py`: Logic for process enumeration and memory dumping.
- `src/core/injector.py`: Stealthy Manual Map injection logic (relocations, header erasure).
- `src/ui/app.py`: Main GUI implementation.
- `test_dll/`: Simple C++ DLL for testing injection (shows a MessageBox on attach).
- `requirements.txt`: Project dependencies.
- `build.spec`: PyInstaller configuration for building the executable.
- `.github/workflows/release.yml`: GitHub Actions workflow for Python releases.
- `.github/workflows/cpp-dll.yml`: GitHub Actions workflow for building the test DLL.

## Features & Stealth
- **Manual Mapping:** Injects DLLs without `LoadLibrary`, bypassing standard detection.
- **Test DLL:** (v1.0.6) Includes a simple C++ DLL that triggers a "Success" message box upon successful injection.
- **Architecture Validation:** (v1.0.1) Checks for x86/x64 mismatch before injection.
- **Thread Hijacking (WIP):** Concept implemented for stealthy execution.
- **Dumping:** Extracts module data directly from target process memory.
- **Revamped Logging:** (v1.0.1) Color-coded logs with timestamps for better debugging.

## Building and Running
### Building the Test DLL (C++)
```bash
cmake -S test_dll -B build_dll
cmake --build build_dll --config Release
```
The resulting `test_dll.dll` will be in `build_dll/Release/`.

## Development Conventions
- **Modular Design:** Keep memory logic (`core`) separate from the user interface (`ui`).
- **Stealth First:** Prioritize low-level API interactions (`ctypes`) for operations that are easily detected.
- **Error Handling:** Ensure operations are wrapped in try-except blocks to prevent app crashes during memory access.
