import tkinter as tk
from gui import BmiApp

def main():
    """Main application launcher."""
    root = tk.Tk()
    app = BmiApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
