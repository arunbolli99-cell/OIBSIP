import os
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import webbrowser
from datetime import datetime

# Import local helper modules
import config_manager
import weather_api

# Colors & Theme Constants (Modern Slate Dark Theme)
BG_APP = "#0F172A"         # Deep Slate (App Background)
BG_CARD = "#1E293B"        # Slate 800 (Card Background)
BG_CARD_HOVER = "#334155"  # Slate 700 (Card Hover)
ACCENT = "#0EA5E9"         # Sky 500 (Primary accent / Buttons)
ACCENT_HOVER = "#38BDF8"   # Sky 400 (Accent hover)
FG_PRIMARY = "#F8FAFC"     # Slate 50 (Primary Text)
FG_SECONDARY = "#94A3B8"   # Slate 400 (Secondary Text)
BORDER = "#334155"         # Slate 700 (Card borders)
ERROR_RED = "#EF4444"      # Red 500 (Error highlights)
SUCCESS_GREEN = "#10B981"  # Green 500 (Success indicators)

# Emoji mapping fallback in case icons fail to download
WEATHER_EMOJIS = {
    "01d": "☀️", "01n": "🌙",
    "02d": "⛅", "02n": "☁️",
    "03d": "☁️", "03n": "☁️",
    "04d": "☁️", "04n": "☁️",
    "09d": "🌧️", "09n": "🌧️",
    "10d": "🌦️", "10n": "🌧️",
    "11d": "⛈️", "11n": "⛈️",
    "13d": "❄️", "13n": "❄️",
    "50d": "🌫️", "50n": "🌫️"
}

class WeatherDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("AeroWeather | Dashboard")
        self.root.geometry("1080x720")
        self.root.configure(bg=BG_APP)
        self.root.minsize(1000, 680)

        # Threading communication queue
        self.task_queue = queue.Queue()
        self.root.after(100, self.process_queue)
        
        # Load user configurations
        self.config = config_manager.load_config()
        self.current_weather_data = None
        self.active_search_thread = None

        # Build GUI Layout
        self.setup_styles()
        self.build_ui()
        
        # Check API key on startup
        api_key = config_manager.get_api_key()
        if not api_key:
            # Delay opening settings modal slightly to let GUI render first
            self.root.after(500, self.open_settings_modal)
        else:
            # Auto-detect location if key is available
            self.root.after(200, self.auto_detect_location)

    def setup_styles(self):
        """Configure native Tkinter styles for scrollbars and text widgets."""
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Configure custom scrollbar style for modern dark appearance
        self.style.configure("Vertical.TScrollbar", 
                             gripcount=0,
                             background=BG_CARD,
                             troughcolor=BG_APP,
                             bordercolor=BG_APP,
                             arrowcolor=FG_SECONDARY)
        self.style.map("Vertical.TScrollbar",
                       background=[("active", BG_CARD_HOVER)])

    def build_ui(self):
        """Constructs the dashboard interface layout."""
        # Top Bar frame
        self.top_bar = tk.Frame(self.root, bg=BG_APP, height=80)
        self.top_bar.pack(fill="x", padx=30, pady=(20, 10))
        self.top_bar.pack_propagate(False)
        
        # Logo section
        logo_frame = tk.Frame(self.top_bar, bg=BG_APP)
        logo_frame.pack(side="left", fill="y")
        
        logo_lbl = tk.Label(logo_frame, text="AeroWeather", font=("Segoe UI", 20, "bold"), fg=ACCENT, bg=BG_APP)
        logo_lbl.pack(anchor="w", pady=(5, 0))
        
        subtitle_lbl = tk.Label(logo_frame, text="Real-time Weather Dashboard", font=("Segoe UI", 9), fg=FG_SECONDARY, bg=BG_APP)
        subtitle_lbl.pack(anchor="w")

        # Controls section (Search, Geolocation, Unit Toggle, Settings)
        controls_frame = tk.Frame(self.top_bar, bg=BG_APP)
        controls_frame.pack(side="right", fill="y", pady=10)

        # Search box container (for rounded border effect)
        search_container = tk.Frame(controls_frame, bg=BORDER, padx=1, pady=1)
        search_container.pack(side="left", padx=(0, 10))

        self.search_entry = tk.Entry(
            search_container, 
            bg=BG_CARD, 
            fg=FG_PRIMARY, 
            insertbackground=FG_PRIMARY,
            font=("Segoe UI", 11), 
            bd=0, 
            width=24,
            highlightthickness=5,
            highlightbackground=BG_CARD,
            highlightcolor=BG_CARD
        )
        self.search_entry.pack(padx=2, pady=2)
        
        # Placeholder functionality
        self.placeholder_text = "Enter city or ZIP code..."
        self.search_entry.insert(0, self.placeholder_text)
        self.search_entry.configure(fg=FG_SECONDARY)
        self.search_entry.bind("<FocusIn>", self.clear_placeholder)
        self.search_entry.bind("<FocusOut>", self.restore_placeholder)
        self.search_entry.bind("<Return>", lambda e: self.perform_search())

        # Search Button
        self.btn_search = tk.Label(
            controls_frame, 
            text="🔍 Search", 
            font=("Segoe UI", 10, "bold"), 
            bg=ACCENT, 
            fg=FG_PRIMARY, 
            padx=15, 
            pady=8, 
            cursor="hand2"
        )
        self.btn_search.pack(side="left", padx=5)
        self.btn_search.bind("<Button-1>", lambda e: self.perform_search())
        self.btn_search.bind("<Enter>", lambda e: self.btn_search.configure(bg=ACCENT_HOVER))
        self.btn_search.bind("<Leave>", lambda e: self.btn_search.configure(bg=ACCENT))

        # Location Button
        self.btn_locate = tk.Label(
            controls_frame, 
            text="📍 Locate", 
            font=("Segoe UI", 10, "bold"), 
            bg=BG_CARD, 
            fg=FG_PRIMARY, 
            padx=12, 
            pady=8, 
            cursor="hand2",
            highlightbackground=BORDER,
            highlightthickness=1
        )
        self.btn_locate.pack(side="left", padx=5)
        self.btn_locate.bind("<Button-1>", lambda e: self.auto_detect_location())
        self.btn_locate.bind("<Enter>", lambda e: self.btn_locate.configure(bg=BG_CARD_HOVER))
        self.btn_locate.bind("<Leave>", lambda e: self.btn_locate.configure(bg=BG_CARD))

        # Unit Switch Button
        self.btn_unit = tk.Label(
            controls_frame, 
            text="°C ⇄ °F", 
            font=("Segoe UI", 10, "bold"), 
            bg=BG_CARD, 
            fg=FG_PRIMARY, 
            padx=12, 
            pady=8, 
            cursor="hand2",
            highlightbackground=BORDER,
            highlightthickness=1
        )
        self.btn_unit.pack(side="left", padx=5)
        self.btn_unit.bind("<Button-1>", lambda e: self.toggle_units())
        self.btn_unit.bind("<Enter>", lambda e: self.btn_unit.configure(bg=BG_CARD_HOVER))
        self.btn_unit.bind("<Leave>", lambda e: self.btn_unit.configure(bg=BG_CARD))

        # Settings Gear Button
        self.btn_settings = tk.Label(
            controls_frame, 
            text="⚙️ Settings", 
            font=("Segoe UI", 10, "bold"), 
            bg=BG_CARD, 
            fg=FG_PRIMARY, 
            padx=12, 
            pady=8, 
            cursor="hand2",
            highlightbackground=BORDER,
            highlightthickness=1
        )
        self.btn_settings.pack(side="left", padx=(5, 0))
        self.btn_settings.bind("<Button-1>", lambda e: self.open_settings_modal())
        self.btn_settings.bind("<Enter>", lambda e: self.btn_settings.configure(bg=BG_CARD_HOVER))
        self.btn_settings.bind("<Leave>", lambda e: self.btn_settings.configure(bg=BG_CARD))

        # Error notification bar (initially hidden)
        self.error_bar = tk.Frame(self.root, bg=ERROR_RED, height=0)
        self.error_bar.pack(fill="x", padx=30, pady=(5, 5))
        self.error_lbl = tk.Label(self.error_bar, text="", font=("Segoe UI", 10, "bold"), fg=FG_PRIMARY, bg=ERROR_RED)
        self.error_lbl.pack(side="left", padx=15, pady=8)
        self.error_close = tk.Label(self.error_bar, text="✕", font=("Segoe UI", 10, "bold"), fg=FG_PRIMARY, bg=ERROR_RED, cursor="hand2")
        self.error_close.pack(side="right", padx=15, pady=8)
        self.error_close.bind("<Button-1>", lambda e: self.hide_error())

        # Main Content Layout Area
        self.main_content = tk.Frame(self.root, bg=BG_APP)
        self.main_content.pack(fill="both", expand=True, padx=30, pady=(10, 20))
        self.main_content.rowconfigure(0, weight=1)
        self.main_content.columnconfigure(0, weight=6) # Left main dashboard
        self.main_content.columnconfigure(1, weight=4) # Right 5-day forecast

        # LEFT FRAME (Current weather details + Hourly list)
        left_column = tk.Frame(self.main_content, bg=BG_APP)
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_column.rowconfigure(0, weight=3) # Current Panel
        left_column.rowconfigure(1, weight=2) # Hourly Panel
        left_column.columnconfigure(0, weight=1)

        # 1. Current Weather Panel
        self.panel_current = tk.Frame(left_column, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        self.panel_current.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        
        # Details inside current panel
        self.lbl_city = tk.Label(self.panel_current, text="No Location Loaded", font=("Segoe UI", 24, "bold"), fg=FG_PRIMARY, bg=BG_CARD)
        self.lbl_city.pack(anchor="w", padx=25, pady=(20, 2))
        
        self.lbl_date = tk.Label(self.panel_current, text="Search for a city or click 'Locate' to begin", font=("Segoe UI", 11), fg=FG_SECONDARY, bg=BG_CARD)
        self.lbl_date.pack(anchor="w", padx=25)

        # Big Temp and Icon side-by-side
        middle_weather_frame = tk.Frame(self.panel_current, bg=BG_CARD)
        middle_weather_frame.pack(fill="x", padx=25, pady=15)
        
        self.lbl_weather_icon = tk.Label(middle_weather_frame, text="", bg=BG_CARD)
        self.lbl_weather_icon.pack(side="left")
        
        self.lbl_temp = tk.Label(middle_weather_frame, text="--°", font=("Segoe UI", 68, "bold"), fg=FG_PRIMARY, bg=BG_CARD)
        self.lbl_temp.pack(side="left", padx=20)
        
        self.lbl_condition = tk.Label(self.panel_current, text="Weather details will show up here", font=("Segoe UI", 15, "bold"), fg=ACCENT, bg=BG_CARD)
        self.lbl_condition.pack(anchor="w", padx=25, pady=(0, 10))

        # Divider line
        divider = tk.Frame(self.panel_current, bg=BORDER, height=1)
        divider.pack(fill="x", padx=25, pady=10)

        # 2x2 Info Grid for details
        info_grid = tk.Frame(self.panel_current, bg=BG_CARD)
        info_grid.pack(fill="both", expand=True, padx=25, pady=(5, 20))
        info_grid.columnconfigure(0, weight=1)
        info_grid.columnconfigure(1, weight=1)
        info_grid.columnconfigure(2, weight=1)
        info_grid.rowconfigure(0, weight=1)
        info_grid.rowconfigure(1, weight=1)

        self.lbl_detail_feels = tk.Label(info_grid, text="🌡️ Feels Like: --", font=("Segoe UI", 11), fg=FG_PRIMARY, bg=BG_CARD, anchor="w")
        self.lbl_detail_feels.grid(row=0, column=0, sticky="w", pady=5)
        
        self.lbl_detail_humidity = tk.Label(info_grid, text="💧 Humidity: --", font=("Segoe UI", 11), fg=FG_PRIMARY, bg=BG_CARD, anchor="w")
        self.lbl_detail_humidity.grid(row=0, column=1, sticky="w", pady=5)

        self.lbl_detail_wind = tk.Label(info_grid, text="💨 Wind: --", font=("Segoe UI", 11), fg=FG_PRIMARY, bg=BG_CARD, anchor="w")
        self.lbl_detail_wind.grid(row=0, column=2, sticky="w", pady=5)

        self.lbl_detail_pressure = tk.Label(info_grid, text="🎈 Pressure: --", font=("Segoe UI", 11), fg=FG_PRIMARY, bg=BG_CARD, anchor="w")
        self.lbl_detail_pressure.grid(row=1, column=0, sticky="w", pady=5)

        self.lbl_detail_direction = tk.Label(info_grid, text="🧭 Direction: --", font=("Segoe UI", 11), fg=FG_PRIMARY, bg=BG_CARD, anchor="w")
        self.lbl_detail_direction.grid(row=1, column=1, sticky="w", pady=5)

        self.lbl_detail_updated = tk.Label(info_grid, text="🕒 Updated: --", font=("Segoe UI", 11), fg=FG_PRIMARY, bg=BG_CARD, anchor="w")
        self.lbl_detail_updated.grid(row=1, column=2, sticky="w", pady=5)

        # 2. Hourly Forecast Panel
        self.panel_hourly = tk.Frame(left_column, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        self.panel_hourly.grid(row=1, column=0, sticky="nsew")
        
        lbl_hourly_title = tk.Label(self.panel_hourly, text="HOURLY FORECAST (NEXT 15 HOURS)", font=("Segoe UI", 10, "bold"), fg=FG_SECONDARY, bg=BG_CARD)
        lbl_hourly_title.pack(anchor="w", padx=25, pady=(15, 10))
        
        # Horizontal list container
        self.hourly_list_frame = tk.Frame(self.panel_hourly, bg=BG_CARD)
        self.hourly_list_frame.pack(fill="both", expand=True, padx=25, pady=(0, 15))
        self.hourly_list_frame.rowconfigure(0, weight=1)
        for i in range(5):
            self.hourly_list_frame.columnconfigure(i, weight=1)

        # Initialize hourly sub-cards
        self.hourly_cards = []
        for i in range(5):
            h_card = tk.Frame(self.hourly_list_frame, bg=BG_APP, highlightbackground=BORDER, highlightthickness=1)
            h_card.grid(row=0, column=i, sticky="nsew", padx=4)
            
            lbl_time = tk.Label(h_card, text="--:--", font=("Segoe UI", 9, "bold"), fg=FG_SECONDARY, bg=BG_APP)
            lbl_time.pack(pady=(8, 2))
            
            lbl_icon = tk.Label(h_card, text="--", font=("Segoe UI", 18), fg=FG_PRIMARY, bg=BG_APP)
            lbl_icon.pack(pady=2)
            
            lbl_temp = tk.Label(h_card, text="--°", font=("Segoe UI", 12, "bold"), fg=FG_PRIMARY, bg=BG_APP)
            lbl_temp.pack(pady=(2, 8))
            
            self.hourly_cards.append({
                "frame": h_card,
                "time": lbl_time,
                "icon": lbl_icon,
                "temp": lbl_temp
            })

        # RIGHT FRAME (5-Day Forecast Card)
        self.panel_daily = tk.Frame(self.main_content, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        self.panel_daily.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        lbl_daily_title = tk.Label(self.panel_daily, text="5-DAY FORECAST", font=("Segoe UI", 10, "bold"), fg=FG_SECONDARY, bg=BG_CARD)
        lbl_daily_title.pack(anchor="w", padx=25, pady=(20, 15))
        
        # Vertical list container
        self.daily_list_frame = tk.Frame(self.panel_daily, bg=BG_CARD)
        self.daily_list_frame.pack(fill="both", expand=True, padx=25, pady=(0, 20))
        self.daily_list_frame.columnconfigure(0, weight=1)
        for i in range(5):
            self.daily_list_frame.rowconfigure(i, weight=1)

        # Initialize daily rows
        self.daily_rows = []
        for i in range(5):
            row_frame = tk.Frame(self.daily_list_frame, bg=BG_CARD)
            row_frame.grid(row=i, column=0, sticky="nsew", pady=4)
            
            # Subdivider inside list
            if i > 0:
                row_divider = tk.Frame(row_frame, bg=BORDER, height=1)
                row_divider.pack(fill="x", side="top")
                
            content_row = tk.Frame(row_frame, bg=BG_CARD)
            content_row.pack(fill="both", expand=True, pady=8)
            
            lbl_day = tk.Label(content_row, text="DayName", font=("Segoe UI", 11, "bold"), fg=FG_PRIMARY, bg=BG_CARD, anchor="w", width=10)
            lbl_day.pack(side="left", padx=(10, 0))
            
            lbl_icon = tk.Label(content_row, text="--", font=("Segoe UI", 16), fg=FG_PRIMARY, bg=BG_CARD, width=4)
            lbl_icon.pack(side="left", padx=10)
            
            lbl_desc = tk.Label(content_row, text="Condition", font=("Segoe UI", 10), fg=FG_SECONDARY, bg=BG_CARD, anchor="w", width=15)
            lbl_desc.pack(side="left", padx=5)
            
            lbl_temps = tk.Label(content_row, text="--° / --°", font=("Segoe UI", 11, "bold"), fg=FG_PRIMARY, bg=BG_CARD, anchor="e")
            lbl_temps.pack(side="right", padx=(0, 10))
            
            self.daily_rows.append({
                "day": lbl_day,
                "icon": lbl_icon,
                "desc": lbl_desc,
                "temps": lbl_temps
            })

        # Overlay Glassmorphic Loading panel (Initially Hidden)
        self.loading_overlay = tk.Frame(self.root, bg=BG_APP)
        self.lbl_loading_text = tk.Label(
            self.loading_overlay, 
            text="Fetching Weather Data...", 
            font=("Segoe UI", 16, "bold"), 
            fg=FG_PRIMARY, 
            bg=BG_APP
        )
        self.lbl_loading_text.pack(expand=True)
        self.is_loading = False

    # Loading Panel Handlers
    def show_loading(self, message="Fetching Weather Data..."):
        self.is_loading = True
        self.lbl_loading_text.configure(text=message)
        # Place loading overlay directly on top of the main content
        self.loading_overlay.place(relx=0, rely=0.12, relwidth=1, relheight=0.88)
        self.animate_loading(0)
        
    def hide_loading(self):
        self.is_loading = False
        self.loading_overlay.place_forget()

    def animate_loading(self, dot_count):
        if not self.is_loading:
            return
        dots = "." * (dot_count % 4)
        base_text = self.lbl_loading_text.cget("text").rstrip(".")
        self.lbl_loading_text.configure(text=f"{base_text}{dots}")
        self.root.after(300, lambda: self.animate_loading(dot_count + 1))

    # Error Notification Handlers
    def show_error(self, message):
        self.error_lbl.configure(text=message)
        self.error_bar.pack(fill="x", padx=30, pady=(5, 5), before=self.main_content)
        # Automatically close error banner after 8 seconds
        self.root.after(8000, self.hide_error)

    def hide_error(self):
        self.error_bar.pack_forget()

    # Search Box Placeholder Handlers
    def clear_placeholder(self, event):
        if self.search_entry.get() == self.placeholder_text:
            self.search_entry.delete(0, tk.END)
            self.search_entry.configure(fg=FG_PRIMARY)

    def restore_placeholder(self, event):
        if not self.search_entry.get().strip():
            self.search_entry.delete(0, tk.END)
            self.search_entry.insert(0, self.placeholder_text)
            self.search_entry.configure(fg=FG_SECONDARY)

    # Unit management
    def toggle_units(self):
        """Toggles between Celsius (metric) and Fahrenheit (imperial) locally."""
        current_unit = config_manager.get_units()
        new_unit = "imperial" if current_unit == "metric" else "metric"
        config_manager.set_units(new_unit)
        
        # Redraw UI with new unit conversion instantly if weather data exists
        if self.current_weather_data:
            self.update_ui_elements(self.current_weather_data)
        else:
            self.show_error("No weather data loaded to convert.")

    # Geolocation Handler
    def auto_detect_location(self):
        """Triggers geolocation thread."""
        api_key = config_manager.get_api_key()
        if not api_key:
            self.show_error("Please configure your OpenWeatherMap API key first.")
            self.open_settings_modal()
            return
            
        self.show_loading("Detecting Location...")
        threading.Thread(target=self._run_auto_detect, daemon=True).start()

    def _run_auto_detect(self):
        try:
            location = weather_api.get_current_location()
            if location:
                # Dispatch weather query back to the main thread
                self.task_queue.put(lambda: self.fetch_weather_details(location))
            else:
                self.task_queue.put(self.hide_loading)
                self.task_queue.put(lambda: self.show_error("Could not detect location automatically. Try search."))
        except Exception as e:
            err_msg = str(e)
            self.task_queue.put(self.hide_loading)
            self.task_queue.put(lambda msg=err_msg: self.show_error(msg))

    # Search Handler
    def perform_search(self):
        query = self.search_entry.get().strip()
        if not query or query == self.placeholder_text:
            self.show_error("Please enter a valid city name or ZIP code.")
            return
        
        api_key = config_manager.get_api_key()
        if not api_key:
            self.show_error("Please configure your API key first.")
            self.open_settings_modal()
            return

        self.fetch_weather_details(query)

    def fetch_weather_details(self, location_query):
        """Starts a background thread to fetch weather details for location."""
        self.hide_error()
        self.show_loading(f"Fetching Weather for '{location_query}'...")
        
        api_key = config_manager.get_api_key()
        
        # Run request in background thread
        thread = threading.Thread(
            target=self._run_fetch_weather, 
            args=(location_query, api_key), 
            daemon=True
        )
        thread.start()

    def _run_fetch_weather(self, query, api_key):
        try:
            # We always fetch in metric and convert locally to enable instant unit switching
            data = weather_api.fetch_weather_data(query, api_key, units="metric")
            
            # Queue UI updates on main thread
            self.task_queue.put(lambda: self.on_fetch_success(data))
        except Exception as e:
            self.task_queue.put(lambda err=e: self.on_fetch_failure(err))

    def on_fetch_success(self, data):
        self.hide_loading()
        self.current_weather_data = data
        self.update_ui_elements(data)
        
        # Clear search box and restore placeholder
        self.search_entry.delete(0, tk.END)
        self.restore_placeholder(None)
        # Drop focus
        self.root.focus_set()

    def on_fetch_failure(self, exception):
        self.hide_loading()
        error_msg = str(exception)
        self.show_error(error_msg)

    # Thread Queue Processor
    def process_queue(self):
        """Processes pending UI callbacks dispatched from other threads."""
        try:
            while True:
                callback = self.task_queue.get_nowait()
                callback()
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    # Redraw UI Data
    def update_ui_elements(self, data):
        """Updates the dashboard widgets with new parsed weather data."""
        units = config_manager.get_units()
        
        current = data["current"]
        hourly = data["hourly"]
        daily = data["daily"]
        
        # Temp Formatter helpers
        def convert_temp(c_temp):
            if units == "imperial":
                return round(c_temp * 9/5 + 32)
            return round(c_temp)

        def convert_speed(m_speed):
            if units == "imperial":
                return f"{round(m_speed * 2.23694, 1)} mph"
            return f"{round(m_speed, 1)} m/s"

        unit_suffix = "°F" if units == "imperial" else "°C"
        
        # 1. Update Current Weather Panel
        self.lbl_city.configure(text=f"{current['city']}, {current['country']}")
        
        # Dynamic Date string
        local_time = datetime.fromtimestamp(current['dt']).strftime("%A, %B %d — %I:%M %p")
        self.lbl_date.configure(text=local_time)
        
        self.lbl_temp.configure(text=f"{convert_temp(current['temp'])}{unit_suffix}")
        self.lbl_condition.configure(text=current["description"])
        
        # Current Weather Icon
        icon_photo = weather_api.get_weather_icon(current["icon"], size=100)
        if icon_photo:
            self.lbl_weather_icon.configure(image=icon_photo, text="")
            # Store reference to prevent garbage collection
            self.lbl_weather_icon.image = icon_photo
        else:
            fallback_emoji = WEATHER_EMOJIS.get(current["icon"], "☀️")
            self.lbl_weather_icon.configure(text=fallback_emoji, font=("Segoe UI", 48), image="")

        # 2x2 Details Grid
        self.lbl_detail_feels.configure(text=f"🌡️ Feels Like: {convert_temp(current['feels_like'])}{unit_suffix}")
        self.lbl_detail_humidity.configure(text=f"💧 Humidity: {current['humidity']}%")
        self.lbl_detail_wind.configure(text=f"💨 Wind: {convert_speed(current['wind_speed'])}")
        self.lbl_detail_pressure.configure(text=f"🎈 Pressure: {current['pressure']} hPa")
        
        cardinal_dir = weather_api.get_cardinal_direction(current["wind_deg"])
        self.lbl_detail_direction.configure(text=f"🧭 Direction: {current['wind_deg']}° ({cardinal_dir})")
        
        now_str = datetime.now().strftime("%I:%M %p")
        self.lbl_detail_updated.configure(text=f"🕒 Updated: {now_str}")

        # 2. Update Hourly Forecast cards
        for idx, card in enumerate(self.hourly_cards):
            if idx < len(hourly):
                h_data = hourly[idx]
                card["frame"].grid(row=0, column=idx, sticky="nsew", padx=4)
                card["time"].configure(text=h_data["time"])
                card["temp"].configure(text=f"{convert_temp(h_data['temp'])}°")
                
                h_icon = weather_api.get_weather_icon(h_data["icon"], size=50)
                if h_icon:
                    card["icon"].configure(image=h_icon, text="")
                    card["icon"].image = h_icon
                else:
                    fallback_emoji = WEATHER_EMOJIS.get(h_data["icon"], "☀️")
                    card["icon"].configure(text=fallback_emoji, font=("Segoe UI", 20), image="")
            else:
                card["frame"].grid_forget()

        # 3. Update 5-Day Forecast list
        for idx, row in enumerate(self.daily_rows):
            if idx < len(daily):
                d_data = daily[idx]
                row["day"].configure(text=d_data["day"])
                row["desc"].configure(text=d_data["description"])
                
                min_t = convert_temp(d_data["temp_min"])
                max_t = convert_temp(d_data["temp_max"])
                row["temps"].configure(text=f"{min_t}° / {max_t}°")
                
                d_icon = weather_api.get_weather_icon(d_data["icon"], size=40)
                if d_icon:
                    row["icon"].configure(image=d_icon, text="")
                    row["icon"].image = d_icon
                else:
                    fallback_emoji = WEATHER_EMOJIS.get(d_data["icon"], "☀️")
                    row["icon"].configure(text=fallback_emoji, font=("Segoe UI", 18), image="")

    # Settings Modal View
    def open_settings_modal(self):
        """Displays settings top-level window for API key configuration."""
        modal = tk.Toplevel(self.root)
        modal.title("AeroWeather Settings")
        modal.geometry("450x320")
        modal.configure(bg=BG_CARD)
        modal.resizable(False, False)
        
        # Center modal on the parent window
        parent_x = self.root.winfo_x()
        parent_y = self.root.winfo_y()
        parent_w = self.root.winfo_width()
        parent_h = self.root.winfo_height()
        modal.geometry(f"+{parent_x + (parent_w - 450) // 2}+{parent_y + (parent_h - 320) // 2}")
        
        modal.transient(self.root)
        modal.grab_set()

        # Modal Title
        tk.Label(
            modal, 
            text="Settings", 
            font=("Segoe UI", 16, "bold"), 
            fg=FG_PRIMARY, 
            bg=BG_CARD
        ).pack(anchor="w", padx=25, pady=(20, 5))

        tk.Label(
            modal, 
            text="WeatherAPI.com API Configuration", 
            font=("Segoe UI", 10, "bold"), 
            fg=ACCENT, 
            bg=BG_CARD
        ).pack(anchor="w", padx=25, pady=(0, 15))

        # Instructions / Link
        link_frame = tk.Frame(modal, bg=BG_CARD)
        link_frame.pack(anchor="w", padx=25, pady=(0, 15))
        
        tk.Label(
            link_frame, 
            text="Don't have an API key? Register at ", 
            font=("Segoe UI", 9), 
            fg=FG_SECONDARY, 
            bg=BG_CARD
        ).pack(side="left")
        
        link_lbl = tk.Label(
            link_frame, 
            text="weatherapi.com", 
            font=("Segoe UI", 9, "underline"), 
            fg=ACCENT, 
            bg=BG_CARD, 
            cursor="hand2"
        )
        link_lbl.pack(side="left")
        link_lbl.bind("<Button-1>", lambda e: webbrowser.open_new("https://www.weatherapi.com/signup.aspx"))

        # Input label
        tk.Label(
            modal, 
            text="Enter API Key:", 
            font=("Segoe UI", 10), 
            fg=FG_PRIMARY, 
            bg=BG_CARD
        ).pack(anchor="w", padx=25, pady=(0, 5))

        # Input field container
        key_container = tk.Frame(modal, bg=BORDER, padx=1, pady=1)
        key_container.pack(fill="x", padx=25, pady=(0, 20))

        key_entry = tk.Entry(
            key_container, 
            bg=BG_APP, 
            fg=FG_PRIMARY, 
            insertbackground=FG_PRIMARY,
            font=("Segoe UI", 11), 
            bd=0,
            highlightthickness=5,
            highlightbackground=BG_APP,
            highlightcolor=BG_APP
        )
        key_entry.pack(fill="x", padx=2, pady=2)
        
        # Populate with existing key if available
        curr_key = config_manager.get_api_key()
        if curr_key:
            key_entry.insert(0, curr_key)

        # Status text inside modal
        status_lbl = tk.Label(modal, text="", font=("Segoe UI", 9, "bold"), fg=SUCCESS_GREEN, bg=BG_CARD)
        status_lbl.pack(anchor="w", padx=25, pady=(0, 10))

        # Buttons container
        btns_frame = tk.Frame(modal, bg=BG_CARD)
        btns_frame.pack(fill="x", padx=25, pady=5)

        # Helper validator inside setting thread
        def validate_and_save():
            key = key_entry.get().strip()
            if not key:
                status_lbl.configure(text="API key cannot be empty.", fg=ERROR_RED)
                return
                
            status_lbl.configure(text="Validating key...", fg=FG_SECONDARY)
            
            # Start background validation call
            def run_val():
                try:
                    # 1. Test WeatherAPI key by fetching London
                    test_url_wa = "http://api.weatherapi.com/v1/current.json"
                    try:
                        res_wa = requests.get(test_url_wa, params={"q": "London", "key": key}, timeout=5)
                        if res_wa.status_code == 200:
                            config_manager.set_provider("weatherapi")
                            config_manager.set_api_key(key)
                            def success_ui_wa():
                                status_lbl.configure(text="WeatherAPI Key saved!", fg=SUCCESS_GREEN)
                                self.root.after(1000, lambda: [modal.destroy(), self.auto_detect_location()])
                            self.task_queue.put(success_ui_wa)
                            return
                    except Exception:
                        pass
                        
                    # 2. Test OpenWeatherMap key by fetching London
                    test_url_owm = "https://api.openweathermap.org/data/2.5/weather"
                    try:
                        res_owm = requests.get(test_url_owm, params={"q": "London", "appid": key}, timeout=5)
                        if res_owm.status_code == 200:
                            config_manager.set_provider("openweathermap")
                            config_manager.set_api_key(key)
                            def success_ui_owm():
                                status_lbl.configure(text="OpenWeatherMap Key saved!", fg=SUCCESS_GREEN)
                                self.root.after(1000, lambda: [modal.destroy(), self.auto_detect_location()])
                            self.task_queue.put(success_ui_owm)
                            return
                    except Exception:
                        pass
                        
                    # Both failed
                    err_msg = "Invalid key. Verification failed."
                    self.task_queue.put(lambda: status_lbl.configure(text=err_msg, fg=ERROR_RED))
                except Exception as e:
                    err_msg = f"Network Error: {e}"
                    self.task_queue.put(lambda msg=err_msg: status_lbl.configure(text=msg, fg=ERROR_RED))

            threading.Thread(target=run_val, daemon=True).start()

        # Save Button
        btn_save = tk.Label(
            btns_frame, 
            text="Validate & Save", 
            font=("Segoe UI", 10, "bold"), 
            bg=ACCENT, 
            fg=FG_PRIMARY, 
            padx=15, 
            pady=8, 
            cursor="hand2"
        )
        btn_save.pack(side="right", padx=(10, 0))
        btn_save.bind("<Button-1>", lambda e: validate_and_save())
        btn_save.bind("<Enter>", lambda e: btn_save.configure(bg=ACCENT_HOVER))
        btn_save.bind("<Leave>", lambda e: btn_save.configure(bg=ACCENT))

        # Cancel Button
        btn_cancel = tk.Label(
            btns_frame, 
            text="Cancel", 
            font=("Segoe UI", 10, "bold"), 
            bg=BG_APP, 
            fg=FG_PRIMARY, 
            padx=15, 
            pady=8, 
            cursor="hand2",
            highlightbackground=BORDER,
            highlightthickness=1
        )
        btn_cancel.pack(side="right")
        btn_cancel.bind("<Button-1>", lambda e: modal.destroy())
        btn_cancel.bind("<Enter>", lambda e: btn_cancel.configure(bg=BG_CARD_HOVER))
        btn_cancel.bind("<Leave>", lambda e: btn_cancel.configure(bg=BG_APP))

        # Demo Mode Button (for offline or keyless testing)
        def activate_demo():
            config_manager.set_api_key("demo")
            status_lbl.configure(text="Demo Mode Activated!", fg=SUCCESS_GREEN)
            self.root.after(1000, lambda: [modal.destroy(), self.auto_detect_location()])

        btn_demo = tk.Label(
            btns_frame, 
            text="Demo Mode", 
            font=("Segoe UI", 10, "bold"), 
            bg=BG_CARD_HOVER, 
            fg=FG_PRIMARY, 
            padx=15, 
            pady=8, 
            cursor="hand2",
            highlightbackground=BORDER,
            highlightthickness=1
        )
        btn_demo.pack(side="left")
        btn_demo.bind("<Button-1>", lambda e: activate_demo())
        btn_demo.bind("<Enter>", lambda e: btn_demo.configure(bg=ACCENT))
        btn_demo.bind("<Leave>", lambda e: btn_demo.configure(bg=BG_CARD_HOVER))


if __name__ == "__main__":
    # Ensure requests and Pillow dependencies are handled correctly
    try:
        import requests
        from PIL import Image, ImageTk
    except ImportError as e:
        print(f"Required libraries missing. Run: pip install requests pillow")
        messagebox.showerror("Dependencies Missing", "Missing required libraries. Please install 'requests' and 'pillow'.")
        exit(1)

    root = tk.Tk()
    
    # Modern flat window styling
    # Sets icon if available (or uses standard)
    app = WeatherDashboard(root)
    root.mainloop()
