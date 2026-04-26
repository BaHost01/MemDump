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
- `requirements.txt`: Project dependencies.
- `build.spec`: PyInstaller configuration for building the executable.
- `.github/workflows/release.yml`: GitHub Actions workflow for automated releases.

## Features & Stealth
- **Manual Mapping:** Injects DLLs without `LoadLibrary`, bypassing standard detection.
- **Header Erasure:** Optional post-injection step to erase PE headers from memory.
- **Architecture Validation:** (v1.0.1) Checks for x86/x64 mismatch before injection.
- **Thread Hijacking (WIP):** Concept implemented for stealthy execution.
- **Dumping:** Extracts module data directly from target process memory.
- **Revamped Logging:** (v1.0.1) Color-coded logs with timestamps for better debugging.

## Building and Running
### Local Development (Windows)
1. **Environment Setup:**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run Application:**
   ```bash
   python src/main.py
   ```

### Building Executable
```bash
pyinstaller build.spec
```
The output will be in the `dist/MemDump.exe` directory.

## Automated Releases
Pushing a tag matching `v*` (e.g., `v1.0.1`) triggers the GitHub Action to build the Windows executable (utilizing pip caching for speed) and attach it to a new GitHub Release.

## Development Conventions
- **Modular Design:** Keep memory logic (`core`) separate from the user interface (`ui`).
- **Stealth First:** Prioritize low-level API interactions (`ctypes`) for operations that are easily detected.
- **Error Handling:** Ensure operations are wrapped in try-except blocks to prevent app crashes during memory access.
