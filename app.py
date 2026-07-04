import sys
import secrets
import string
import math
import tkinter as tk
import customtkinter as ctk
import pyperclip

# --- Core Cryptography Logic ---

def secure_shuffle(lst):
    """Cryptographically secure Fisher-Yates shuffle."""
    n = len(lst)
    for i in range(n - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        lst[i], lst[j] = lst[j], lst[i]

def generate_password(length, use_upper, use_lower, use_digits, use_symbols, exclude_ambiguous):
    """
    Generates a cryptographically secure random password matching all criteria.
    Enforces inclusion of at least one character from each active category.
    """
    if length < 8:
        raise ValueError("Password length must be at least 8 characters.")
    
    # 1. Collate selected character types
    categories = []
    if use_upper:
        categories.append(string.ascii_uppercase)
    if use_lower:
        categories.append(string.ascii_lowercase)
    if use_digits:
        categories.append(string.digits)
    if use_symbols:
        categories.append("!@#$%^&*()-_=+[]{}|;:,.<>?/")

    if len(categories) < 2:
        raise ValueError("At least 2 character types must be selected.")
        
    # 2. Exclude ambiguous characters if requested
    # Ambiguous list: 0, O, o, l, 1, I, |
    ambiguous = set("0Ool1I|")
    
    filtered_categories = []
    for cat in categories:
        filtered_cat = "".join([c for c in cat if c not in ambiguous]) if exclude_ambiguous else cat
        if filtered_cat:
            filtered_categories.append(filtered_cat)
            
    if len(filtered_categories) < 2:
        raise ValueError("At least 2 character types required after filtering ambiguous characters.")
        
    # 3. Guarantee at least one character from each selected category
    password_chars = []
    for cat in filtered_categories:
        password_chars.append(secrets.choice(cat))
        
    # 4. Combine all selected categories for the remaining characters
    combined_pool = "".join(filtered_categories)
    
    # 5. Fill the remaining length
    for _ in range(length - len(password_chars)):
        password_chars.append(secrets.choice(combined_pool))
        
    # 6. Apply cryptographically secure shuffle to prevent any pattern leak
    secure_shuffle(password_chars)
    
    return "".join(password_chars)

def calculate_entropy(length, pool_size):
    """Calculates password entropy in bits."""
    if pool_size <= 0:
        return 0
    return length * math.log2(pool_size)

# --- GUI Application ---

class PasswordGeneratorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window settings
        self.title("Krypton • Secure Password Generator")
        self.geometry("540x740")
        self.resizable(False, False)
        
        # Set theme behavior
        ctk.set_appearance_mode("Dark")  # Default to premium Dark mode
        ctk.set_default_color_theme("blue")
        
        # State variables
        self.password_history = []
        
        # Build UI layout
        self.setup_ui()
        
        # Generate initial password without copying it to clipboard automatically on startup
        self.generate_and_display(auto_copy=False, is_startup=True)

    def setup_ui(self):
        # Configure Grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Main Frame with standard background colors for light/dark modes
        self.main_container = ctk.CTkFrame(self, fg_color=("#F3F4F6", "#0F172A"), corner_radius=0)
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.main_container.grid_columnconfigure(0, weight=1)
        
        # --- HEADER SECTION ---
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=25, pady=(20, 10))
        self.header_frame.grid_columnconfigure(0, weight=1)
        
        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="🔑 KRYPTON",
            font=("Segoe UI", 26, "bold"),
            text_color=("#2563EB", "#60A5FA")
        )
        self.title_label.grid(row=0, column=0, sticky="w")
        
        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="Cryptographically Secure Generator",
            font=("Segoe UI", 12),
            text_color=("#4B5563", "#94A3B8")
        )
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
        
        # Theme Toggle Switch (top right)
        self.theme_switch = ctk.CTkSwitch(
            self.header_frame,
            text="Dark Mode",
            command=self.toggle_theme,
            font=("Segoe UI", 11),
            text_color=("#4B5563", "#94A3B8")
        )
        self.theme_switch.grid(row=0, column=1, rowspan=2, sticky="e")
        self.theme_switch.select() # Start in Dark Mode
        
        # --- DISPLAY SECTION ---
        self.display_frame = ctk.CTkFrame(
            self.main_container,
            fg_color=("#FFFFFF", "#1E293B"),
            border_color=("#E5E7EB", "#334155"),
            border_width=1,
            corner_radius=12
        )
        self.display_frame.grid(row=1, column=0, sticky="ew", padx=25, pady=10)
        self.display_frame.grid_columnconfigure(0, weight=1)
        
        # Password entry field (ReadOnly but selectable)
        self.password_display = ctk.CTkEntry(
            self.display_frame,
            font=("Consolas", 18, "bold"),
            height=50,
            fg_color="transparent",
            border_width=0,
            text_color=("#111827", "#F3F4F6"),
            justify="center"
        )
        self.password_display.grid(row=0, column=0, sticky="ew", padx=(15, 5), pady=15)
        self.password_display.insert(0, "Generating...")
        self.password_display.configure(state="readonly")
        
        # Copy button
        self.copy_btn = ctk.CTkButton(
            self.display_frame,
            text="📋 Copy",
            width=80,
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color=("#2563EB", "#3B82F6"),
            hover_color=("#1D4ED8", "#2563EB"),
            command=self.copy_to_clipboard
        )
        self.copy_btn.grid(row=0, column=1, padx=(5, 15), pady=15)
        
        # --- STRENGTH INDICATOR SECTION ---
        self.strength_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.strength_frame.grid(row=2, column=0, sticky="ew", padx=25, pady=(5, 15))
        self.strength_frame.grid_columnconfigure(1, weight=1)
        
        self.strength_title = ctk.CTkLabel(
            self.strength_frame,
            text="Password Strength:",
            font=("Segoe UI", 12, "bold"),
            text_color=("#374151", "#E5E7EB")
        )
        self.strength_title.grid(row=0, column=0, sticky="w")
        
        self.strength_label = ctk.CTkLabel(
            self.strength_frame,
            text="Weak",
            font=("Segoe UI", 12, "bold"),
            text_color="#EF4444"
        )
        self.strength_label.grid(row=0, column=2, sticky="e")
        
        self.strength_bar = ctk.CTkProgressBar(
            self.strength_frame,
            height=8,
            progress_color="#EF4444"
        )
        self.strength_bar.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        self.strength_bar.set(0.33)
        
        # --- CONTROLS SECTION ---
        self.controls_frame = ctk.CTkFrame(
            self.main_container,
            fg_color=("#FFFFFF", "#1E293B"),
            border_color=("#E5E7EB", "#334155"),
            border_width=1,
            corner_radius=12
        )
        self.controls_frame.grid(row=3, column=0, sticky="ew", padx=25, pady=10)
        self.controls_frame.grid_columnconfigure(0, weight=1)
        
        # Slider length label
        self.length_val = tk.IntVar(value=16)
        self.length_label = ctk.CTkLabel(
            self.controls_frame,
            text="Password Length: 16",
            font=("Segoe UI", 13, "bold"),
            text_color=("#374151", "#E5E7EB")
        )
        self.length_label.grid(row=0, column=0, sticky="w", padx=20, pady=(15, 0))
        
        # Slider container (Slider + Numeric indicator)
        self.slider_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.slider_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(5, 15))
        self.slider_frame.grid_columnconfigure(0, weight=1)
        
        self.length_slider = ctk.CTkSlider(
            self.slider_frame,
            from_=8,
            to=64,
            number_of_steps=56,
            variable=self.length_val,
            command=self.on_slider_change
        )
        self.length_slider.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        self.length_num_label = ctk.CTkLabel(
            self.slider_frame,
            text="16",
            font=("Segoe UI", 14, "bold"),
            text_color=("#2563EB", "#60A5FA"),
            width=30
        )
        self.length_num_label.grid(row=0, column=1, sticky="e")
        
        # Dividers for premium grouping
        self.divider = ctk.CTkFrame(self.controls_frame, height=2, fg_color=("#E5E7EB", "#334155"))
        self.divider.grid(row=2, column=0, sticky="ew", padx=20, pady=5)
        
        # Checkboxes grid (2x2 layout)
        self.checkbox_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.checkbox_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=10)
        self.checkbox_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Selection states
        self.var_upper = tk.BooleanVar(value=True)
        self.var_lower = tk.BooleanVar(value=True)
        self.var_digits = tk.BooleanVar(value=True)
        self.var_symbols = tk.BooleanVar(value=True)
        self.var_exclude = tk.BooleanVar(value=False)
        
        self.chk_upper = ctk.CTkCheckBox(
            self.checkbox_frame,
            text="Uppercase (A-Z)",
            variable=self.var_upper,
            command=self.on_checkbox_toggle,
            font=("Segoe UI", 12)
        )
        self.chk_upper.grid(row=0, column=0, sticky="w", pady=8)
        
        self.chk_lower = ctk.CTkCheckBox(
            self.checkbox_frame,
            text="Lowercase (a-z)",
            variable=self.var_lower,
            command=self.on_checkbox_toggle,
            font=("Segoe UI", 12)
        )
        self.chk_lower.grid(row=0, column=1, sticky="w", pady=8)
        
        self.chk_digits = ctk.CTkCheckBox(
            self.checkbox_frame,
            text="Numbers (0-9)",
            variable=self.var_digits,
            command=self.on_checkbox_toggle,
            font=("Segoe UI", 12)
        )
        self.chk_digits.grid(row=1, column=0, sticky="w", pady=8)
        
        self.chk_symbols = ctk.CTkCheckBox(
            self.checkbox_frame,
            text="Symbols (!@#$)",
            variable=self.var_symbols,
            command=self.on_checkbox_toggle,
            font=("Segoe UI", 12)
        )
        self.chk_symbols.grid(row=1, column=1, sticky="w", pady=8)
        
        self.chk_exclude = ctk.CTkCheckBox(
            self.checkbox_frame,
            text="Exclude Ambiguous Characters (e.g. 0, O, l, 1)",
            variable=self.var_exclude,
            command=self.on_checkbox_toggle,
            font=("Segoe UI", 12),
            text_color=("#4B5563", "#94A3B8")
        )
        self.chk_exclude.grid(row=2, column=0, columnspan=2, sticky="w", pady=(12, 5))
        
        # --- GENERATE BUTTON ---
        self.generate_btn = ctk.CTkButton(
            self.main_container,
            text="⚡ Generate & Copy Secure Password",
            font=("Segoe UI", 15, "bold"),
            height=50,
            fg_color=("#10B981", "#059669"),
            hover_color=("#059669", "#047857"),
            command=lambda: self.generate_and_display(auto_copy=True)
        )
        self.generate_btn.grid(row=4, column=0, sticky="ew", padx=25, pady=15)
        
        # --- HISTORY SECTION ---
        self.history_frame = ctk.CTkFrame(
            self.main_container,
            fg_color=("#FFFFFF", "#1E293B"),
            border_color=("#E5E7EB", "#334155"),
            border_width=1,
            corner_radius=12
        )
        self.history_frame.grid(row=5, column=0, sticky="ew", padx=25, pady=10)
        self.history_frame.grid_columnconfigure(0, weight=1)
        
        self.history_title = ctk.CTkLabel(
            self.history_frame,
            text="Recent Session Passwords (Click to Load)",
            font=("Segoe UI", 12, "bold"),
            text_color=("#374151", "#E5E7EB")
        )
        self.history_title.grid(row=0, column=0, sticky="w", padx=20, pady=(10, 5))
        
        self.history_list_frame = ctk.CTkFrame(self.history_frame, fg_color="transparent")
        self.history_list_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.history_list_frame.grid_columnconfigure(0, weight=1)
        
        self.history_labels = []
        for i in range(5):
            row_frame = ctk.CTkFrame(self.history_list_frame, fg_color="transparent", height=28)
            row_frame.grid(row=i, column=0, sticky="ew", pady=2)
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_propagate(False)
            
            lbl = ctk.CTkLabel(
                row_frame,
                text="-",
                font=("Consolas", 12),
                text_color=("#4B5563", "#94A3B8"),
                anchor="w",
                cursor="hand2"
            )
            lbl.grid(row=0, column=0, sticky="w")
            # Bind both label click and hover effects
            lbl.bind("<Button-1>", lambda event, idx=i: self.load_from_history(idx))
            lbl.bind("<Enter>", lambda event, label=lbl: label.configure(text_color=("#1D4ED8", "#60A5FA")))
            lbl.bind("<Leave>", lambda event, label=lbl: label.configure(text_color=("#4B5563", "#94A3B8")))
            
            copy_lbl = ctk.CTkLabel(
                row_frame,
                text="Copy",
                font=("Segoe UI", 11, "underline"),
                text_color=("#2563EB", "#60A5FA"),
                cursor="hand2",
                width=45
            )
            copy_lbl.grid(row=0, column=1, sticky="e")
            copy_lbl.bind("<Button-1>", lambda event, idx=i: self.copy_from_history(idx))
            
            # Start hidden until passwords generated
            row_frame.grid_remove()
            self.history_labels.append((row_frame, lbl, copy_lbl))

    # --- UI INTERACTION & CALLBACKS ---

    def toggle_theme(self):
        """Switches between Dark and Light mode."""
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("Dark")
        else:
            ctk.set_appearance_mode("Light")

    def on_slider_change(self, value):
        """Updates length labels and automatically generates a new preview."""
        val = int(value)
        self.length_label.configure(text=f"Password Length: {val}")
        self.length_num_label.configure(text=str(val))
        self.generate_and_display(auto_copy=False)

    def on_checkbox_toggle(self):
        """Triggers automatic generation on configuration change."""
        self.generate_and_display(auto_copy=False)

    def adjust_font_size(self, password):
        """Dynamically adjusts display font size depending on length for premium readability."""
        length = len(password)
        if length > 36:
            self.password_display.configure(font=("Consolas", 12, "bold"))
        elif length > 22:
            self.password_display.configure(font=("Consolas", 15, "bold"))
        else:
            self.password_display.configure(font=("Consolas", 18, "bold"))

    def update_strength_meter(self, password, selected_count):
        """Calculates strength using entropy and diversity and updates the visual UI meter."""
        length = len(password)
        
        # Estimate pool size based on settings
        pool_size = 0
        if self.var_upper.get(): pool_size += 26
        if self.var_lower.get(): pool_size += 26
        if self.var_digits.get(): pool_size += 10
        if self.var_symbols.get(): pool_size += 29
        
        if self.var_exclude.get():
            pool_size -= 7 # subtract ambiguous characters roughly
            
        entropy = calculate_entropy(length, pool_size)
        
        # Classify and update colors/progress
        if entropy < 56 or length < 10 or selected_count < 3:
            self.strength_label.configure(text="Weak", text_color="#EF4444")
            self.strength_bar.configure(progress_color="#EF4444")
            self.strength_bar.set(0.33)
        elif entropy < 78 or selected_count < 4:
            self.strength_label.configure(text="Medium", text_color="#F59E0B")
            self.strength_bar.configure(progress_color="#F59E0B")
            self.strength_bar.set(0.66)
        else:
            self.strength_label.configure(text="Strong", text_color="#10B981")
            self.strength_bar.configure(progress_color="#10B981")
            self.strength_bar.set(1.0)

    def generate_and_display(self, auto_copy=False, is_startup=False):
        """Generates a secure password, checks constraints, updates UI, and manages history."""
        length = int(self.length_val.get())
        use_upper = self.var_upper.get()
        use_lower = self.var_lower.get()
        use_digits = self.var_digits.get()
        use_symbols = self.var_symbols.get()
        exclude_ambiguous = self.var_exclude.get()
        
        # Check constraints (min 2 types)
        selected_count = sum([use_upper, use_lower, use_digits, use_symbols])
        
        if selected_count < 2:
            self.password_display.configure(state="normal")
            self.password_display.delete(0, tk.END)
            self.password_display.insert(0, "Select at least 2 types")
            self.password_display.configure(state="readonly", text_color="#EF4444")
            
            # Disable buttons visually
            self.generate_btn.configure(state="disabled")
            self.copy_btn.configure(state="disabled")
            self.strength_label.configure(text="N/A", text_color=("#9CA3AF", "#4B5563"))
            self.strength_bar.set(0.0)
            return

        # Restore normal UI state if valid
        self.generate_btn.configure(state="normal")
        self.copy_btn.configure(state="normal")
        self.password_display.configure(text_color=("#111827", "#F3F4F6"))
        
        try:
            password = generate_password(
                length, use_upper, use_lower, use_digits, use_symbols, exclude_ambiguous
            )
            
            # Write to display
            self.password_display.configure(state="normal")
            self.password_display.delete(0, tk.END)
            self.password_display.insert(0, password)
            self.password_display.configure(state="readonly")
            
            # Adjust font sizing dynamically
            self.adjust_font_size(password)
            
            # Update strength bar
            self.update_strength_meter(password, selected_count)
            
            # Action: auto-copy and history recording
            # We add to history on startup or explicit generate button clicks
            if not is_startup:
                if auto_copy:
                    pyperclip.copy(password)
                    self.show_copied_feedback()
                    self.add_to_history(password)
                elif not self.password_history or self.password_display.get() != self.password_history[0]:
                    # For sliders, we update the preview but don't force copying unless clicked.
                    # However, we can add it to history if they pause or if it's the first.
                    # To prevent polluting history with 50 slider increments, we only log it
                    # when they click generate, copy, or when it's the initial password.
                    pass
            else:
                self.add_to_history(password)
                
        except Exception as e:
            self.password_display.configure(state="normal")
            self.password_display.delete(0, tk.END)
            self.password_display.insert(0, f"Error: {str(e)}")
            self.password_display.configure(state="readonly", text_color="#EF4444")

    def copy_to_clipboard(self):
        """Copies the currently displayed password to the clipboard and records it to history."""
        password = self.password_display.get()
        if password not in ["Select at least 2 types", "Generating..."] and not password.startswith("Error:"):
            pyperclip.copy(password)
            self.show_copied_feedback()
            self.add_to_history(password)

    def show_copied_feedback(self):
        """Flashing visual feedback on copy action."""
        original_text = self.copy_btn.cget("text")
        if original_text != "✓ Copied":
            self.copy_btn.configure(text="✓ Copied", fg_color=("#10B981", "#059669"))
            self.after(1500, lambda: self.copy_btn.configure(text="📋 Copy", fg_color=("#2563EB", "#3B82F6")))

    def add_to_history(self, password):
        """Appends password to session history list (up to 5)."""
        if self.password_history and self.password_history[0] == password:
            return
            
        self.password_history.insert(0, password)
        if len(self.password_history) > 5:
            self.password_history.pop()
            
        self.update_history_ui()

    def update_history_ui(self):
        """Updates the visual history list rows."""
        for idx, (row_frame, lbl, copy_lbl) in enumerate(self.history_labels):
            if idx < len(self.password_history):
                pwd = self.password_history[idx]
                display_pwd = pwd if len(pwd) <= 30 else pwd[:27] + "..."
                lbl.configure(text=f"{idx+1}. {display_pwd}")
                row_frame.grid()  # Show row widget
            else:
                row_frame.grid_remove()  # Hide row widget

    def load_from_history(self, idx):
        """Loads a past password from the history list back into the active view."""
        if idx < len(self.password_history):
            password = self.password_history[idx]
            
            # Write to main display
            self.password_display.configure(state="normal")
            self.password_display.delete(0, tk.END)
            self.password_display.insert(0, password)
            self.password_display.configure(state="readonly")
            
            self.adjust_font_size(password)
            
            # Approximate checkboxes matching the loaded password
            use_upper = any(c in string.ascii_uppercase for c in password)
            use_lower = any(c in string.ascii_lowercase for c in password)
            use_digits = any(c in string.digits for c in password)
            use_symbols = any(c not in (string.ascii_letters + string.digits) for c in password)
            
            selected_count = sum([use_upper, use_lower, use_digits, use_symbols])
            self.update_strength_meter(password, selected_count)

    def copy_from_history(self, idx):
        """Copies a history password directly to the clipboard with visual indicator."""
        if idx < len(self.password_history):
            password = self.password_history[idx]
            pyperclip.copy(password)
            
            row_frame, lbl, copy_lbl = self.history_labels[idx]
            original_color = copy_lbl.cget("text_color")
            copy_lbl.configure(text="Copied!", text_color="#10B981")
            self.after(1000, lambda: copy_lbl.configure(text="Copy", text_color=original_color))

if __name__ == "__main__":
    app = PasswordGeneratorApp()
    app.mainloop()
