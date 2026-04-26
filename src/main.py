import sys
import os

# Add the project root to sys.path to resolve 'src' imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.app import MemDumpApp

def main():
    app = MemDumpApp()
    app.mainloop()

if __name__ == "__main__":
    main()
