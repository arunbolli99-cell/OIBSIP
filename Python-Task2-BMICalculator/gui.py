import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import re
import math

# Set Matplotlib backend to TkAgg BEFORE importing pyplot
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates

import database as db
import bmi_logic as logic

class BmiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BMI Tracker & Health Analytics")
        self.root.geometry("1040x680")
        self.root.minsize(1000, 620)
        self.root.configure(bg="#f8fafc") # slate-50 background
        
        # Initialize Database
        db.init_db()
        
        # App State
        self.users = []
        self.current_user = None  # Dict of current user {"id", "name", "age", "gender"}
        self.unit_system = tk.StringVar(value="metric")  # "metric" or "imperial"
        self.active_tab = "graph" # "graph" or "history"
        
        # Set up styles
        self.setup_styles()
        
        # Build UI Elements
        self.create_header()
        self.create_main_layout()
        
        # Load user profiles from DB
        self.refresh_users_list()

    def setup_styles(self):
        """Set up styles and custom themes for the application."""
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Configure global theme to match slate-50 background
        self.style.configure(".", background="#f8fafc", foreground="#0f172a")
        
        # Configure Treeview with custom fonts and clean list spacing
        self.style.configure(
            "Treeview", 
            font=("Segoe UI", 10), 
            rowheight=30, 
            background="#ffffff", 
            fieldbackground="#ffffff",
            bd=0
        )
        self.style.configure(
            "Treeview.Heading", 
            font=("Segoe UI", 9, "bold"), 
            background="#f1f5f9", 
            foreground="#475569", 
            relief="flat"
        )
        self.style.map("Treeview", background=[("selected", "#e0f2fe")], foreground=[("selected", "#0369a1")])
        
        # Combobox style
        self.style.configure("TCombobox", padding=5, relief="flat", arrowsize=12)

    def create_header(self):
        """Create the clean white header bar with a subtle bottom divider."""
        self.header_frame = tk.Frame(self.root, bg="#ffffff", height=70, bd=0, highlightbackground="#e2e8f0", highlightthickness=1)
        self.header_frame.pack(fill=tk.X, side=tk.TOP)
        self.header_frame.pack_propagate(False)
        
        # App Title
        title_label = tk.Label(
            self.header_frame, 
            text="BMI Health Analytics", 
            font=("Segoe UI", 14, "bold"), 
            bg="#ffffff", 
            fg="#0f172a"
        )
        title_label.pack(side=tk.LEFT, padx=24)
        
        # User Selector Controls
        user_mgmt_frame = tk.Frame(self.header_frame, bg="#ffffff")
        user_mgmt_frame.pack(side=tk.RIGHT, padx=24)
        
        user_label = tk.Label(user_mgmt_frame, text="Active Profile:", font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#64748b")
        user_label.pack(side=tk.LEFT, padx=(0, 8))
        
        self.user_var = tk.StringVar()
        self.user_combobox = ttk.Combobox(
            user_mgmt_frame, 
            textvariable=self.user_var, 
            state="readonly", 
            width=18,
            font=("Segoe UI", 9)
        )
        self.user_combobox.pack(side=tk.LEFT, padx=(0, 12))
        self.user_combobox.bind("<<ComboboxSelected>>", self.on_user_selected)
        
        # Custom styled buttons (flat with colored backgrounds)
        self.btn_new_user = tk.Button(
            user_mgmt_frame, 
            text="New Profile", 
            font=("Segoe UI", 9, "bold"),
            bg="#eff6ff", 
            fg="#2563eb", 
            relief="flat", 
            bd=0, 
            padx=12, 
            pady=6,
            cursor="hand2",
            activebackground="#dbeafe",
            activeforeground="#1d4ed8",
            command=self.open_new_user_dialog
        )
        self.btn_new_user.pack(side=tk.LEFT, padx=4)
        
        self.btn_delete_user = tk.Button(
            user_mgmt_frame, 
            text="Delete Profile", 
            font=("Segoe UI", 9, "bold"),
            bg="#fef2f2", 
            fg="#dc2626", 
            relief="flat", 
            bd=0, 
            padx=12, 
            pady=6,
            cursor="hand2",
            activebackground="#fee2e2",
            activeforeground="#b91c1c",
            command=self.delete_current_profile
        )
        self.btn_delete_user.pack(side=tk.LEFT, padx=4)

    def create_main_layout(self):
        """Assemble the main workspace grid containing the Left and Right cards."""
        self.main_container = tk.Frame(self.root, bg="#f8fafc")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)
        
        # Left Panel (Calculator Card)
        self.left_panel = tk.Frame(
            self.main_container, 
            bg="#ffffff", 
            highlightbackground="#e2e8f0", 
            highlightthickness=1, 
            bd=0,
            width=370
        )
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
        self.left_panel.pack_propagate(False)
        
        # Right Panel (Tabs & Content Card)
        self.right_panel = tk.Frame(
            self.main_container, 
            bg="#ffffff", 
            highlightbackground="#e2e8f0", 
            highlightthickness=1, 
            bd=0
        )
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(24, 0))
        
        self.build_calculator_card()
        self.build_analysis_tabs()

    def build_calculator_card(self):
        """Configure inputs, button, and dynamic gauge on the left card."""
        # Top title inside card
        lbl_title = tk.Label(self.left_panel, text="CALCULATOR", font=("Segoe UI", 11, "bold"), bg="#ffffff", fg="#0f172a")
        lbl_title.pack(anchor=tk.W, padx=20, pady=(20, 12))
        
        # Custom Toggle Tabs for Metric/Imperial units
        toggle_frame = tk.Frame(self.left_panel, bg="#ffffff")
        toggle_frame.pack(fill=tk.X, padx=20, pady=(0, 16))
        
        self.btn_metric = tk.Button(
            toggle_frame, 
            text="Metric (kg/cm)", 
            font=("Segoe UI", 9, "bold"),
            bg="#eff6ff", 
            fg="#2563eb", 
            relief="flat", 
            bd=0, 
            pady=8,
            cursor="hand2",
            command=lambda: self.toggle_units("metric")
        )
        self.btn_metric.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.btn_imperial = tk.Button(
            toggle_frame, 
            text="Imperial (lbs/in)", 
            font=("Segoe UI", 9, "bold"),
            bg="#f1f5f9", 
            fg="#475569", 
            relief="flat", 
            bd=0, 
            pady=8,
            cursor="hand2",
            command=lambda: self.toggle_units("imperial")
        )
        self.btn_imperial.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Form Container
        self.form_frame = tk.Frame(self.left_panel, bg="#ffffff")
        self.form_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        # Inputs definitions
        # Weight entry
        self.weight_label = tk.Label(self.form_frame, text="Weight (kg)", font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#475569")
        self.weight_label.grid(row=0, column=0, sticky=tk.W, pady=(8, 4))
        
        self.weight_entry = tk.Entry(
            self.form_frame, 
            relief="flat", 
            bd=0, 
            highlightthickness=1, 
            highlightbackground="#cbd5e1", 
            highlightcolor="#3b82f6", 
            bg="#f8fafc", 
            fg="#0f172a", 
            font=("Segoe UI", 10),
            insertbackground="#0f172a"
        )
        self.weight_entry.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10), ipady=6, ipadx=4)
        
        # Height entry
        self.height_label = tk.Label(self.form_frame, text="Height (cm)", font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#475569")
        self.height_label.grid(row=2, column=0, sticky=tk.W, pady=(8, 4))
        
        # Frame holding either single metric entry or side-by-side imperial entries
        self.height_entry_frame = tk.Frame(self.form_frame, bg="#ffffff")
        self.height_entry_frame.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10))
        
        self.height_entry = tk.Entry(
            self.height_entry_frame, 
            relief="flat", 
            bd=0, 
            highlightthickness=1, 
            highlightbackground="#cbd5e1", 
            highlightcolor="#3b82f6", 
            bg="#f8fafc", 
            fg="#0f172a", 
            font=("Segoe UI", 10),
            insertbackground="#0f172a"
        )
        self.height_entry.pack(fill=tk.X, expand=True, ipady=6, ipadx=4)
        
        # Imperial Feet & Inches inputs (hidden by default)
        self.height_ft_entry = tk.Entry(
            self.height_entry_frame, 
            relief="flat", 
            bd=0, 
            highlightthickness=1, 
            highlightbackground="#cbd5e1", 
            highlightcolor="#3b82f6", 
            bg="#f8fafc", 
            fg="#0f172a", 
            font=("Segoe UI", 10),
            insertbackground="#0f172a",
            width=6
        )
        self.lbl_ft = tk.Label(self.height_entry_frame, text="ft", bg="#ffffff", font=("Segoe UI", 9), fg="#64748b")
        
        self.height_in_entry = tk.Entry(
            self.height_entry_frame, 
            relief="flat", 
            bd=0, 
            highlightthickness=1, 
            highlightbackground="#cbd5e1", 
            highlightcolor="#3b82f6", 
            bg="#f8fafc", 
            fg="#0f172a", 
            font=("Segoe UI", 10),
            insertbackground="#0f172a",
            width=6
        )
        self.lbl_in = tk.Label(self.height_entry_frame, text="in", bg="#ffffff", font=("Segoe UI", 9), fg="#64748b")
        
        # Date input
        date_label = tk.Label(self.form_frame, text="Log Date", font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#475569")
        date_label.grid(row=4, column=0, sticky=tk.W, pady=(8, 4))
        
        self.date_entry = tk.Entry(
            self.form_frame, 
            relief="flat", 
            bd=0, 
            highlightthickness=1, 
            highlightbackground="#cbd5e1", 
            highlightcolor="#3b82f6", 
            bg="#f8fafc", 
            fg="#0f172a", 
            font=("Segoe UI", 10),
            insertbackground="#0f172a"
        )
        self.date_entry.grid(row=5, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10), ipady=6, ipadx=4)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        self.form_frame.columnconfigure(0, weight=1)
        
        # Calculate Action Button
        self.btn_calculate = tk.Button(
            self.left_panel, 
            text="Calculate & Log BMI", 
            font=("Segoe UI", 10, "bold"), 
            bg="#10b981", 
            fg="#ffffff", 
            relief="flat", 
            bd=0, 
            pady=10, 
            cursor="hand2",
            activebackground="#059669",
            activeforeground="#ffffff",
            command=self.calculate_and_save
        )
        self.btn_calculate.pack(fill=tk.X, padx=20, pady=(12, 16))
        
        # Visual Health Gauge Section
        gauge_title = tk.Label(self.left_panel, text="VISUAL HEALTH GAUGE", font=("Segoe UI", 9, "bold"), bg="#ffffff", fg="#64748b")
        gauge_title.pack(anchor=tk.W, padx=20, pady=(6, 4))
        
        self.gauge_canvas = tk.Canvas(self.left_panel, width=330, height=135, bg="#ffffff", highlightthickness=0)
        self.gauge_canvas.pack(fill=tk.X, padx=20, pady=(0, 4))
        
        # Status Card (soft colored box for BMI value and text classification)
        self.status_card = tk.Frame(self.left_panel, bg="#f8fafc", bd=0, padx=12, pady=10)
        self.status_card.pack(fill=tk.X, padx=20, pady=(4, 10))
        
        self.lbl_gauge_val = tk.Label(self.status_card, text="BMI: --", font=("Segoe UI", 12, "bold"), bg="#f8fafc", fg="#475569")
        self.lbl_gauge_val.pack(anchor=tk.W, pady=2)
        
        self.lbl_gauge_category = tk.Label(
            self.status_card, 
            text="Please create or select a profile.", 
            font=("Segoe UI", 9), 
            bg="#f8fafc", 
            fg="#64748b",
            wraplength=290,
            justify=tk.LEFT
        )
        self.lbl_gauge_category.pack(anchor=tk.W, pady=2)
        
        # Draw background gauge
        self.draw_gauge(None)

    def build_analysis_tabs(self):
        """Construct the customized tab selector and content containers."""
        # Custom Navigation Bar
        self.tab_bar = tk.Frame(self.right_panel, bg="#ffffff")
        self.tab_bar.pack(fill=tk.X, padx=20, pady=(15, 0))
        
        # Tab Buttons
        self.btn_tab_graph = tk.Button(
            self.tab_bar, 
            text="Trend Analytics", 
            font=("Segoe UI", 10, "bold"),
            relief="flat", 
            bd=0, 
            bg="#ffffff", 
            fg="#4f46e5", 
            padx=16, 
            pady=8,
            cursor="hand2",
            command=lambda: self.switch_tab("graph")
        )
        self.btn_tab_graph.pack(side=tk.LEFT)
        
        self.btn_tab_history = tk.Button(
            self.tab_bar, 
            text="History Logs", 
            font=("Segoe UI", 10, "bold"),
            relief="flat", 
            bd=0, 
            bg="#ffffff", 
            fg="#64748b", 
            padx=16, 
            pady=8,
            cursor="hand2",
            command=lambda: self.switch_tab("history")
        )
        self.btn_tab_history.pack(side=tk.LEFT)
        
        # Divider Line
        self.tab_divider = tk.Frame(self.right_panel, bg="#e2e8f0", height=1)
        self.tab_divider.pack(fill=tk.X, padx=20, pady=(0, 12))
        
        # TAB 1 Frame: Trend Graph
        self.graph_frame = tk.Frame(self.right_panel, bg="#ffffff")
        self.graph_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
        
        self.fig, self.ax = plt.subplots(figsize=(5.5, 4.2), dpi=100)
        self.fig.patch.set_facecolor('#ffffff')
        self.canvas_plot = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas_widget = self.canvas_plot.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)
        
        # TAB 2 Frame: History Table (hidden initially)
        self.history_frame = tk.Frame(self.right_panel, bg="#ffffff")
        
        table_container = tk.Frame(self.history_frame, bg="#ffffff")
        table_container.pack(fill=tk.BOTH, expand=True)
        
        scrollbar_y = ttk.Scrollbar(table_container, orient=tk.VERTICAL)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        cols = ("Date", "Weight", "Height", "BMI", "Category")
        self.tree = ttk.Treeview(table_container, columns=cols, show="headings", yscrollcommand=scrollbar_y.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar_y.config(command=self.tree.yview)
        
        # Heading definitions
        for col in cols:
            self.tree.heading(col, text=col, anchor=tk.CENTER)
            self.tree.column(col, anchor=tk.CENTER, width=90)
            
        # Action controls for history
        ctrl_frame = tk.Frame(self.history_frame, bg="#ffffff")
        ctrl_frame.pack(fill=tk.X, pady=(15, 0))
        
        self.btn_delete_record = tk.Button(
            ctrl_frame, 
            text="Delete Selected Record", 
            font=("Segoe UI", 9, "bold"),
            bg="#fef2f2", 
            fg="#dc2626", 
            relief="flat", 
            bd=0, 
            padx=12, 
            pady=8,
            cursor="hand2",
            activebackground="#fee2e2",
            activeforeground="#b91c1c",
            command=self.delete_selected_record
        )
        self.btn_delete_record.pack(side=tk.RIGHT)

    def switch_tab(self, target_tab):
        """Toggle active workspace visibility between Analytics and Table view."""
        if target_tab == self.active_tab:
            return
            
        self.active_tab = target_tab
        
        if target_tab == "graph":
            self.btn_tab_graph.configure(fg="#4f46e5")
            self.btn_tab_history.configure(fg="#64748b")
            
            self.history_frame.pack_forget()
            self.graph_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
        else:
            self.btn_tab_graph.configure(fg="#64748b")
            self.btn_tab_history.configure(fg="#4f46e5")
            
            self.graph_frame.pack_forget()
            self.history_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))

    def draw_gauge(self, bmi):
        """Draw the speedometer-style semi-circular arch dial gauge."""
        self.gauge_canvas.delete("all")
        
        # Center of the semi-circle dial
        cx, cy = 165, 120
        r_arc = 80 # Radius of the color ring
        
        # Bounding box for arc drawing
        x0, y0 = cx - r_arc, cy - r_arc
        x1, y1 = cx + r_arc, cy + r_arc
        
        # Segmented arcs with 3-degree gaps
        # Span: 180 degrees (from 180 on left to 0 on right)
        # BMI scale goes from 10 to 40 (span of 30)
        # 1 unit of BMI = 6 degrees
        self.gauge_canvas.create_arc(x0, y0, x1, y1, start=178, extent=-47, style="arc", width=16, outline="#38bdf8", tags="gauge") # Underweight
        self.gauge_canvas.create_arc(x0, y0, x1, y1, start=127, extent=-35, style="arc", width=16, outline="#34d399", tags="gauge") # Normal
        self.gauge_canvas.create_arc(x0, y0, x1, y1, start=88, extent=-26, style="arc", width=16, outline="#fbbf24", tags="gauge") # Overweight
        self.gauge_canvas.create_arc(x0, y0, x1, y1, start=58, extent=-56, style="arc", width=16, outline="#f87171", tags="gauge") # Obese
        
        # Draw labels/ticks around the outer circle
        r_label = 96
        ticks = [
            (10.0, 180),
            (18.5, 129),
            (25.0, 90),
            (30.0, 60),
            (40.0, 0)
        ]
        for val, angle in ticks:
            rad = math.radians(angle)
            lx = cx + r_label * math.cos(rad)
            ly = cy - r_label * math.sin(rad)
            
            # Anchor text depending on position
            if angle == 90:
                anchor_pos = tk.S
            elif angle > 90:
                anchor_pos = tk.SE if angle < 180 else tk.E
            else:
                anchor_pos = tk.SW if angle > 0 else tk.W
                
            self.gauge_canvas.create_text(
                lx, ly, 
                text=str(val), 
                font=("Segoe UI", 8, "bold"), 
                fill="#94a3b8", 
                anchor=anchor_pos
            )
            
        # Draw needle pointing to BMI value
        if bmi is not None:
            clamped_bmi = max(10.0, min(40.0, bmi))
            angle = 180 - (clamped_bmi - 10.0) * 6
            rad = math.radians(angle)
            
            # Needle tip coordinates
            r_needle = 68
            nx = cx + r_needle * math.cos(rad)
            ny = cy - r_needle * math.sin(rad)
            
            # Draw needle shaft
            self.gauge_canvas.create_line(cx, cy, nx, ny, fill="#0f172a", width=3.5, capstyle="round", tags="needle")
            
            # Draw needle hub (center button)
            self.gauge_canvas.create_oval(cx - 7, cy - 7, cx + 7, cy + 7, fill="#0f172a", outline="#ffffff", width=2, tags="needle")
            
            # Display current BMI text under the hub
            self.gauge_canvas.create_text(cx, cy - 22, text=f"{bmi:.1f}", font=("Segoe UI", 13, "bold"), fill="#0f172a")
        else:
            # Faint neutral center text when no records logged
            self.gauge_canvas.create_text(cx, cy - 20, text="--", font=("Segoe UI", 14, "bold"), fill="#94a3b8")

    def toggle_units(self, target_system):
        """Toggle layout labels and entry fields between Metric and Imperial."""
        if target_system == self.unit_system.get():
            return
            
        self.unit_system.set(target_system)
        
        if target_system == "metric":
            self.btn_metric.configure(bg="#eff6ff", fg="#2563eb")
            self.btn_imperial.configure(bg="#f1f5f9", fg="#475569")
            
            # Show single metric entry
            self.height_ft_entry.pack_forget()
            self.lbl_ft.pack_forget()
            self.height_in_entry.pack_forget()
            self.lbl_in.pack_forget()
            
            self.height_entry.pack(fill=tk.X, expand=True, ipady=6, ipadx=4)
            self.weight_label.configure(text="Weight (kg)")
            self.height_label.configure(text="Height (cm)")
        else:
            self.btn_metric.configure(bg="#f1f5f9", fg="#475569")
            self.btn_imperial.configure(bg="#eff6ff", fg="#2563eb")
            
            # Show imperial feet and inches fields
            self.height_entry.pack_forget()
            
            self.height_ft_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, ipadx=4)
            self.lbl_ft.pack(side=tk.LEFT, padx=(2, 6))
            self.height_in_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, ipadx=4)
            self.lbl_in.pack(side=tk.LEFT, padx=(2, 0))
            
            self.weight_label.configure(text="Weight (lbs)")
            self.height_label.configure(text="Height (ft / in)")
            
        self.clear_calculator_inputs()

    def clear_calculator_inputs(self):
        """Empty calculator text values."""
        self.weight_entry.delete(0, tk.END)
        self.height_entry.delete(0, tk.END)
        self.height_ft_entry.delete(0, tk.END)
        self.height_in_entry.delete(0, tk.END)

    def refresh_users_list(self, select_user_id=None):
        """Retrieve user profiles and update selector dropdown states."""
        try:
            self.users = db.get_users()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to retrieve user list:\n{str(e)}")
            return
            
        user_names = [u["name"] for u in self.users]
        self.user_combobox["values"] = user_names
        
        if not self.users:
            self.current_user = None
            self.user_var.set("No Profiles Found")
            self.update_ui_state(active=False)
        else:
            self.update_ui_state(active=True)
            if select_user_id:
                matched = [u for u in self.users if u["id"] == select_user_id]
                if matched:
                    self.current_user = matched[0]
                    
            if not self.current_user or self.current_user not in self.users:
                self.current_user = self.users[0]
                
            self.user_var.set(self.current_user["name"])
            self.on_load_user_data()

    def update_ui_state(self, active=True):
        """Toggle interactive component states based on profile availability."""
        state_tk = "normal" if active else "disabled"
        state_combo = "readonly" if active else "disabled"
        
        self.user_combobox.configure(state=state_combo)
        self.btn_delete_user.configure(state=state_tk)
        self.weight_entry.configure(state=state_tk)
        self.height_entry.configure(state=state_tk)
        self.height_ft_entry.configure(state=state_tk)
        self.height_in_entry.configure(state=state_tk)
        self.date_entry.configure(state=state_tk)
        
        if active:
            self.btn_calculate.configure(state="normal", bg="#10b981")
            self.btn_metric.configure(state="normal")
            self.btn_imperial.configure(state="normal")
            self.btn_delete_record.configure(state="normal")
            self.status_card.configure(bg="#f8fafc")
            self.lbl_gauge_val.configure(bg="#f8fafc", fg="#475569")
            self.lbl_gauge_category.configure(bg="#f8fafc", fg="#64748b")
        else:
            self.btn_calculate.configure(state="disabled", bg="#cbd5e1")
            self.btn_metric.configure(state="disabled")
            self.btn_imperial.configure(state="disabled")
            self.btn_delete_record.configure(state="disabled")
            
            # Clear Gauge status
            self.status_card.configure(bg="#f8fafc")
            self.lbl_gauge_val.configure(text="BMI: --", bg="#f8fafc", fg="#64748b")
            self.lbl_gauge_category.configure(text="Please create a profile.", bg="#f8fafc", fg="#64748b")
            self.draw_gauge(None)
            self.clear_calculator_inputs()
            
            # Clear graph/tables
            self.tree.delete(*self.tree.get_children())
            self.plot_trends([])

    def on_user_selected(self, event=None):
        """Event fired when profile dropdown value is changed."""
        selected_name = self.user_var.get()
        matched = [u for u in self.users if u["name"] == selected_name]
        if matched:
            self.current_user = matched[0]
            self.on_load_user_data()

    def on_load_user_data(self):
        """Load user database logs and refresh graphics/tables."""
        if not self.current_user:
            return
            
        try:
            records = db.get_records(self.current_user["id"])
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to retrieve user logs:\n{str(e)}")
            return
            
        # Re-populate Table with alternate row shading tags
        self.tree.delete(*self.tree.get_children())
        for idx, r in enumerate(records):
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.insert("", tk.END, iid=r["id"], values=(
                r["date"], 
                f"{r['weight']:.2f} kg", 
                f"{r['height']:.2f} m", 
                f"{r['bmi']:.2f}", 
                r["category"]
            ), tags=(tag,))
            
        self.tree.tag_configure("even", background="#f8fafc")
        self.tree.tag_configure("odd", background="#ffffff")
        
        # Load latest metrics to entry inputs
        self.clear_calculator_inputs()
        if records:
            last_r = records[-1]
            h_m = last_r["height"]
            w_kg = last_r["weight"]
            bmi_val = last_r["bmi"]
            
            # Fill inputs matching active unit system
            if self.unit_system.get() == "metric":
                self.height_entry.insert(0, f"{h_m * 100:.1f}")
                self.weight_entry.insert(0, f"{w_kg:.1f}")
            else:
                lbs, ft, inches = logic.convert_metric_to_imperial(w_kg, h_m)
                self.height_ft_entry.insert(0, str(ft))
                self.height_in_entry.insert(0, f"{inches:.1f}")
                self.weight_entry.insert(0, f"{lbs:.1f}")
                
            # Fetch dynamic pastel styles matching classifications
            cat_info = logic.get_category_info(bmi_val)
            
            # Redraw indicator gauge
            self.draw_gauge(bmi_val)
            
            # Update soft status card elements with category-specific colors
            # Pastel mapping:
            # Underweight: bg #e0f2fe (sky-100), text #0284c7
            # Normal: bg #d1fae5 (emerald-100), text #059669
            # Overweight: bg #fef3c7 (amber-100), text #d97706
            # Obese: bg #fee2e2 (red-100), text #dc2626
            pastel_colors = {
                "Underweight": {"bg": "#e0f2fe", "fg": "#0284c7"},
                "Normal weight": {"bg": "#d1fae5", "fg": "#059669"},
                "Overweight": {"bg": "#fef3c7", "fg": "#d97706"},
                "Obese": {"bg": "#fee2e2", "fg": "#dc2626"}
            }
            colors = pastel_colors.get(cat_info["category"], {"bg": "#f8fafc", "fg": "#475569"})
            
            self.status_card.configure(bg=colors["bg"])
            self.lbl_gauge_val.configure(text=f"BMI: {bmi_val:.2f}", bg=colors["bg"], fg=colors["fg"])
            self.lbl_gauge_category.configure(
                text=f"{cat_info['category']} — {cat_info['desc']}", 
                bg=colors["bg"], 
                fg=colors["fg"]
            )
        else:
            self.status_card.configure(bg="#f8fafc")
            self.lbl_gauge_val.configure(text="BMI: --", bg="#f8fafc", fg="#475569")
            self.lbl_gauge_category.configure(text="No logs recorded yet.", bg="#f8fafc", fg="#64748b")
            self.draw_gauge(None)
            
        # Draw matplotlib line plot
        self.plot_trends(records)

    def calculate_and_save(self):
        """Process validations, calculate BMI, save records and update panels."""
        if not self.current_user:
            return
            
        # Date pattern check
        date_str = self.date_entry.get().strip()
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            messagebox.showerror("Validation Error", "Date must be in format YYYY-MM-DD.")
            return
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Validation Error", "Invalid calendar date.")
            return
            
        # Calculate & Convert
        try:
            weight_str = self.weight_entry.get().strip()
            w_val = logic.validate_numeric(weight_str, "Weight")
            
            if self.unit_system.get() == "metric":
                height_str = self.height_entry.get().strip()
                h_val_cm = logic.validate_numeric(height_str, "Height")
                
                weight_kg = w_val
                height_m = h_val_cm / 100.0
            else:
                ft_str = self.height_ft_entry.get().strip()
                in_str = self.height_in_entry.get().strip()
                
                ft_val = logic.validate_numeric(ft_str, "Height (feet)")
                in_val = 0.0 if not in_str else logic.validate_numeric(in_str, "Height (inches)")
                
                weight_kg, height_m = logic.convert_imperial_to_metric(w_val, ft_val, in_val)
                
            bmi_val = logic.calculate_bmi(weight_kg, height_m)
            cat_info = logic.get_category_info(bmi_val)
            
        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
            return
            
        # Write Log to SQLite
        try:
            db.add_record(
                user_id=self.current_user["id"],
                date=date_str,
                weight=weight_kg,
                height=height_m,
                bmi=bmi_val,
                category=cat_info["category"]
            )
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to log record:\n{str(e)}")
            return
            
        messagebox.showinfo("Success", f"BMI Logged!\nBMI: {bmi_val:.2f}\nClassification: {cat_info['category']}")
        self.on_load_user_data()

    def delete_selected_record(self):
        """Remove a selected BMI log from Treeview and DB."""
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Required", "Please select a log entry from the table to delete.")
            return
            
        record_id = int(selected_item[0])
        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this record permanently?")
        if not confirm:
            return
            
        try:
            db.delete_record(record_id)
            self.on_load_user_data()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to delete record:\n{str(e)}")

    def delete_current_profile(self):
        """Delete active user profile and refresh list."""
        if not self.current_user:
            return
            
        confirm = messagebox.askyesno(
            "Confirm Delete", 
            f"Are you sure you want to delete user profile '{self.current_user['name']}'?\nAll associated history will be deleted."
        )
        if not confirm:
            return
            
        try:
            db.delete_user(self.current_user["id"])
            self.current_user = None
            self.refresh_users_list()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to delete profile:\n{str(e)}")

    def plot_trends(self, records):
        """Re-draw the progression line chart with soft pastel color bands."""
        self.ax.clear()
        
        if not records:
            self.ax.text(
                0.5, 0.5, 
                "No BMI records logged yet.\nCalculate and save records to view progress.", 
                ha="center", va="center", transform=self.ax.transAxes, 
                fontname="Segoe UI", fontsize=11, color="#94a3b8"
            )
            self.ax.set_axis_off()
            self.canvas_plot.draw()
            return
            
        self.ax.set_axis_on()
        
        dates = []
        bmis = []
        for r in records:
            try:
                dates.append(datetime.strptime(r["date"], "%Y-%m-%d"))
                bmis.append(r["bmi"])
            except ValueError:
                continue
                
        # Sleek indigo plot line with circles
        self.ax.plot(dates, bmis, marker='o', color='#4f46e5', linewidth=2.5, markersize=7, label="Your BMI")
        
        # Add labels to data points
        for x, y in zip(dates, bmis):
            self.ax.annotate(
                f"{y:.1f}", 
                (x, y), 
                textcoords="offset points", 
                xytext=(0, 10), 
                ha='center', 
                fontsize=8, 
                fontweight='bold', 
                color='#1e293b'
            )
            
        # Draw background health color bands (soft pastel alphas)
        min_y = min(15.0, min(bmis) - 2)
        max_y = max(35.0, max(bmis) + 2)
        
        # Soft pastel band fills:
        self.ax.axhspan(0, 18.5, facecolor='#f0f9ff', alpha=0.9, label='Underweight (<18.5)') # Sky-50
        self.ax.axhspan(18.5, 25.0, facecolor='#ecfdf5', alpha=0.9, label='Normal (18.5-25)')   # Emerald-50
        self.ax.axhspan(25.0, 30.0, facecolor='#fffbeb', alpha=0.9, label='Overweight (25-30)')   # Amber-50
        self.ax.axhspan(30.0, 60.0, facecolor='#fef2f2', alpha=0.9, label='Obese (≥30)')        # Red-50
        
        self.ax.set_ylim(min_y, max_y)
        
        # Date layout
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d\n%Y'))
        self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        
        # Soft spines and grid styling
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_color('#e2e8f0')
        self.ax.spines['bottom'].set_color('#e2e8f0')
        self.ax.tick_params(colors='#64748b', labelsize=9)
        self.ax.grid(True, linestyle="--", alpha=0.4, color="#cbd5e1")
        
        # Axis title labels
        self.ax.set_ylabel("BMI Value", fontsize=10, fontweight="bold", color="#475569")
        self.ax.set_title("Your BMI Progression Over Time", fontsize=11, fontweight="bold", pad=15, color="#0f172a")
        
        # Clean legend
        self.ax.legend(loc="upper left", fontsize=8, framealpha=0.95, facecolor="white", edgecolor="#e2e8f0")
        
        self.fig.tight_layout()
        self.canvas_plot.draw()

    def open_new_user_dialog(self):
        """Open modal to configure a new user profile."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Create User Profile")
        dialog.geometry("320x240")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg="white")
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 160
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 120
        dialog.geometry(f"+{x}+{y}")
        
        lbl_title = tk.Label(dialog, text="NEW USER PROFILE", font=("Segoe UI", 10, "bold"), bg="white", fg="#0f172a")
        lbl_title.pack(anchor=tk.W, padx=20, pady=(15, 10))
        
        form_frame = tk.Frame(dialog, bg="white")
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        
        tk.Label(form_frame, text="Full Name:", font=("Segoe UI", 9, "bold"), bg="white", fg="#475569").grid(row=0, column=0, sticky=tk.W, pady=6)
        name_entry = tk.Entry(
            form_frame, 
            relief="flat", 
            bd=0, 
            highlightthickness=1, 
            highlightbackground="#cbd5e1", 
            highlightcolor="#3b82f6", 
            bg="#f8fafc", 
            fg="#0f172a", 
            font=("Segoe UI", 9)
        )
        name_entry.grid(row=0, column=1, sticky=tk.EW, pady=6, padx=(10, 0), ipady=4)
        name_entry.focus()
        
        tk.Label(form_frame, text="Age (Years):", font=("Segoe UI", 9, "bold"), bg="white", fg="#475569").grid(row=1, column=0, sticky=tk.W, pady=6)
        age_spin = ttk.Spinbox(form_frame, from_=1, to=120, font=("Segoe UI", 9), width=8)
        age_spin.set(25)
        age_spin.grid(row=1, column=1, sticky=tk.W, pady=6, padx=(10, 0))
        
        tk.Label(form_frame, text="Gender:", font=("Segoe UI", 9, "bold"), bg="white", fg="#475569").grid(row=2, column=0, sticky=tk.W, pady=6)
        gender_combo = ttk.Combobox(form_frame, values=["Male", "Female", "Other", "Prefer not to say"], state="readonly", font=("Segoe UI", 9), width=18)
        gender_combo.set("Male")
        gender_combo.grid(row=2, column=1, sticky=tk.W, pady=6, padx=(10, 0))
        
        form_frame.columnconfigure(1, weight=1)
        
        def on_save():
            name = name_entry.get().strip()
            age_str = age_spin.get().strip()
            gender = gender_combo.get()
            
            if not name:
                messagebox.showerror("Input Error", "Please provide a valid name.", parent=dialog)
                return
            
            try:
                age = int(age_str)
                if age <= 0:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Input Error", "Age must be a valid positive integer.", parent=dialog)
                return
                
            try:
                new_id = db.add_user(name, age, gender)
                dialog.destroy()
                self.refresh_users_list(select_user_id=new_id)
                messagebox.showinfo("Success", f"User profile '{name}' has been created successfully!")
            except ValueError as ve:
                messagebox.showerror("Error", str(ve), parent=dialog)
            except Exception as e:
                messagebox.showerror("Database Error", f"Could not create user:\n{str(e)}", parent=dialog)
                
        btn_save = tk.Button(
            dialog, 
            text="Save Profile", 
            font=("Segoe UI", 9, "bold"), 
            bg="#10b981", 
            fg="white", 
            relief="flat", 
            bd=0, 
            pady=8,
            cursor="hand2",
            activebackground="#059669",
            activeforeground="white",
            command=on_save
        )
        btn_save.pack(fill=tk.X, padx=20, pady=(0, 20))
