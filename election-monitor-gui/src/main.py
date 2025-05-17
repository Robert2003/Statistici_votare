#!/usr/bin/env python3
# Copyright (c) 2025 Alexandru Sima (332CA) - Tema 3 PCLP 1

import tkinter as tk
from tkinter import ttk, StringVar
import json
import os
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import threading
import time
from datetime import datetime, timedelta
import numpy as np

from services.data_processor import DataProcessor
from data.constants import (
    COUNTRIES, ROMANIA_NAME, FIGURE_SIZE, PLOT_SPACE, 
    UPDATE_MINUTE, UPDATE_SECOND, ELECTION_DATE_ROUND1, 
    ELECTION_DATE_ROUND2, DATE_DIFF,
    # New UI constants
    WINDOW_TITLE, WINDOW_SIZE, CONTROL_PADDING, CONSOLE_PADDING, 
    FRAME_PADDING, BUTTON_PADDING, TEXT_HEIGHT, TEXT_WRAP, TEXT_FONT,
    CONSOLE_EXPAND_RATIO, PLOT_EXPAND_RATIO, PLOT_FIGURE_SIZE, PLOT_GRID_SIZE,
    TABLE_HEADER_LEN, TABLE_DIVIDER_CHAR, TABLE_SUMMARY_DIVIDER_CHAR, 
    TABLE_SUMMARY_HEADER_LEN, TABLE_COL_WIDTHS, FIRST_TEXT_BOX_RATIO
)

class ElectionMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Enable fullscreen mode
        self.root.attributes('-fullscreen', True)
        
        # Add a key binding to exit fullscreen mode with Escape key
        self.root.bind("<Escape>", self.exit_fullscreen)
        
        self.data_processor = DataProcessor()
        self.running = True
        
        # Now use the dynamic country list
        self.selected_country = StringVar(root)
        if self.data_processor.countries:
            self.selected_country.set(self.data_processor.countries[0])
        else:
            self.selected_country.set(COUNTRIES[0])  # Fallback
    
        # Variables for tracking vote changes
        self.hour_start_votes = 0      # Votes at the beginning of the hour
        self.current_total_votes = 0   # Current total votes
        
        self.create_widgets()
        self.create_plots()
        
        # Start update thread
        self.update_thread = threading.Thread(target=self.auto_update)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        # Initial update
        self.update_data()
        
        # Make sure the votes display gets updated even if initial data fetch failed
        if self.hour_start_votes == 0 and self.current_total_votes > 0:
            now = datetime.now()
            self.hour_start_votes = self.current_total_votes - int(self.current_total_votes * 0.1 * (now.minute / 60))
            self.update_new_votes_display()
    
        # Schedule regular vote count updates
        self.root.after(10000, self.update_new_votes_count)
        
        # Schedule reset at next hour
        self.schedule_next_hour_reset()

    def exit_fullscreen(self, event=None):
        """Exit fullscreen mode when Escape key is pressed"""
        self.root.attributes('-fullscreen', False)
        return "break"

    def toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode"""
        is_fullscreen = self.root.attributes('-fullscreen')
        self.root.attributes('-fullscreen', not is_fullscreen)

    def create_widgets(self):
        """Create the GUI widgets"""
        # Top control panel
        control_frame = ttk.Frame(self.root, padding=CONTROL_PADDING)
        control_frame.pack(fill=tk.X)
        
        # Country selection with integrated search - replace search frame and combobox
        ttk.Label(control_frame, text="Select Country:").pack(side=tk.LEFT, padx=5)
        
        # Create custom combobox with search - change to 'state="normal"' instead of readonly
        self.country_menu = ttk.Combobox(control_frame, textvariable=self.selected_country, 
                      values=self.data_processor.countries, width=30, state="normal")
        self.country_menu.pack(side=tk.LEFT, padx=5)
        
        # Add flag to track if typing has started in the combobox
        self.typing_started = False
        
        # Bind events for search functionality
        self.country_menu.bind("<KeyRelease>", self.on_combobox_keyrelease)
        self.country_menu.bind("<KeyPress>", self.on_combobox_keypress)  # New binding
        self.country_menu.bind("<<ComboboxSelected>>", self.on_country_selected)
        self.country_menu.bind("<Return>", self.on_combobox_enter)
        self.country_menu.bind("<FocusOut>", self.on_combobox_focus_lost)
        self.country_menu.bind("<FocusIn>", self.on_combobox_focus)  # New binding
        
        # Store the original country list for quick restoration
        self.original_country_list = list(self.data_processor.countries)
        
        # Variable to store the current search term
        self.last_search_term = ""
        
        # Update button
        update_button = ttk.Button(control_frame, text="Update Now", command=self.update_data)
        update_button.pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        # Fullscreen toggle button
        fullscreen_button = ttk.Button(control_frame, text="Toggle Fullscreen", command=self.toggle_fullscreen)
        fullscreen_button.pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        # Status frame (right side of control frame)
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(side=tk.RIGHT, padx=FRAME_PADDING)
        
        # Real-time clock display
        self.clock_var = StringVar()
        self.clock_var.set(datetime.now().strftime('%H:%M:%S'))
        clock_label = ttk.Label(status_frame, textvariable=self.clock_var, font=("Arial", 10, "bold"))
        clock_label.pack(side=tk.LEFT, padx=10)
        
        # Start the clock update
        self.update_clock()
        
        # Status label
        self.status_var = StringVar()
        self.status_var.set("Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(side=tk.RIGHT)

        # Console output frame with two columns
        console_frame = ttk.LabelFrame(self.root, text="Country Data Details", padding=CONSOLE_PADDING)
        console_frame.pack(fill=tk.BOTH, expand=CONSOLE_EXPAND_RATIO, padx=FRAME_PADDING, pady=FRAME_PADDING)
        
        # Create paned window for split view
        paned_window = ttk.PanedWindow(console_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left panel for country data
        country_panel = ttk.Frame(paned_window)
        paned_window.add(country_panel, weight=1)
        
        # Create scrollable text widget for country output
        self.country_text = tk.Text(country_panel, height=TEXT_HEIGHT, wrap=TEXT_WRAP, font=TEXT_FONT)
        self.country_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add scrollbar to country text
        country_scrollbar = ttk.Scrollbar(country_panel, command=self.country_text.yview)
        country_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.country_text.configure(yscrollcommand=country_scrollbar.set)
        
        # Right panel for total/summary data
        summary_panel = ttk.Frame(paned_window)
        paned_window.add(summary_panel, weight=1)
        
        # Create scrollable text widget for summary output
        self.summary_text = tk.Text(summary_panel, height=TEXT_HEIGHT, wrap=TEXT_WRAP, font=TEXT_FONT)
        self.summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add scrollbar to summary text
        summary_scrollbar = ttk.Scrollbar(summary_panel, command=self.summary_text.yview)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.summary_text.configure(yscrollcommand=summary_scrollbar.set)
        
        # Set initial sash position to divide the window equally
        self.root.update_idletasks()
        width = console_frame.winfo_width()
        self.root.after(100, lambda: paned_window.sashpos(0, int(width * FIRST_TEXT_BOX_RATIO)))

    def create_plots(self):
        """Create the matplotlib plots in a 2x2 grid"""
        # Plots frame
        plots_frame = ttk.Frame(self.root)
        plots_frame.pack(fill=tk.BOTH, expand=PLOT_EXPAND_RATIO, padx=FRAME_PADDING, pady=FRAME_PADDING)
        
        # Create figure with 2x2 grid of subplots
        self.fig = Figure(figsize=PLOT_FIGURE_SIZE)
        
        # Create a 2x2 grid of subplots
        rows, cols = PLOT_GRID_SIZE
        self.ax1 = self.fig.add_subplot(rows, cols, 1)  # Top-left
        self.ax2 = self.fig.add_subplot(rows, cols, 2)  # Top-right
        self.ax3 = self.fig.add_subplot(rows, cols, 3)  # Bottom-left
        self.ax4 = self.fig.add_subplot(rows, cols, 4)  # Bottom-right
        
        self.axes = [self.ax1, self.ax2, self.ax3, self.ax4]
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=plots_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add toolbar
        toolbar_frame = ttk.Frame(plots_frame)
        toolbar_frame.pack(fill=tk.X)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()

    def clear_console(self):
        """Clear both console text widgets"""
        self.country_text.delete(1.0, tk.END)
        self.summary_text.delete(1.0, tk.END)
        
    def write_to_country_console(self, text):
        """Write text to the country console widget"""
        self.country_text.insert(tk.END, text + "\n")
        self.country_text.see(tk.END)  # Auto-scroll to the end
        
    def write_to_summary_console(self, text):
        """Write text to the summary console widget"""
        self.summary_text.insert(tk.END, text + "\n")
        self.summary_text.see(tk.END)  # Auto-scroll to the end

    def on_combobox_keypress(self, event=None):
        """Handle first keypress in the combobox - clear the field"""
        # Skip special keys
        if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Escape', 'Tab', 'Return'):
            return
            
        # On first character typed, clear the field
        if not self.typing_started and event.char:
            self.typing_started = True
            self.country_menu.delete(0, 'end')

    def on_combobox_keyrelease(self, event=None):
        """Handle typing in the combobox"""
        # Skip special keys
        if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Escape', 'Tab', 'Return'):
            return
    
        # Get current text in combobox
        search_term = self.country_menu.get()
        self.last_search_term = search_term
        
        # Filter the country list
        if search_term:
            # Search for matching countries
            matching_countries = self.data_processor.search_countries(search_term)
            
            # Update dropdown list without changing the entry text
            current_text = self.country_menu.get()  # Save current text
            self.country_menu['values'] = matching_countries
            self.country_menu.set(current_text)  # Restore text
            
            # Keep the dropdown open but don't change selection
            current_position = self.country_menu.index('insert')  # Save cursor position
            self.country_menu.event_generate('<Down>')
            self.country_menu.icursor(current_position)  # Restore cursor position
        else:
            # Reset to full list if cleared
            self.country_menu['values'] = self.original_country_list

    def on_country_selected(self, event=None):
        """Handle selection from the dropdown"""
        # Get the selected value directly from the combobox
        selected = self.country_menu.get()
        
        # Search for the closest match in our country list
        if selected:
            exact_match = None
            # Try exact match first
            if selected in self.data_processor.countries:
                exact_match = selected
            else:
                # Try case-insensitive match
                for country in self.data_processor.countries:
                    if country.lower() == selected.lower():
                        exact_match = country
                        break
            
                # If still no match, try starting with
                if not exact_match:
                    for country in self.data_processor.countries:
                        if country.lower().startswith(selected.lower()):
                            exact_match = country
                            break
        
        # If we found a match, use it
        if exact_match:
            self.selected_country.set(exact_match)
            self.country_menu.set(exact_match)  # Set the visible text
            self.on_country_changed()
            
            # Reset search state and typing flag
            self.last_search_term = ""
            self.typing_started = False
            self.country_menu['values'] = self.original_country_list

    def on_combobox_enter(self, event=None):
        """Handle Enter key in combobox"""
        # Get current values in dropdown
        values = self.country_menu['values']
        
        # If there are values and current text matches or is a prefix of one
        if values and len(values) > 0:
            search_term = self.country_menu.get().lower()
            
            # Look for direct match first
            exact_match = None
            for country in values:
                if country.lower() == search_term:
                    exact_match = country
                    break
            
            # If no exact match, find closest match
            if not exact_match and search_term:
                for country in values:
                    if country.lower().startswith(search_term):
                        exact_match = country
                        break
            
            # If still no match, just use the first item
            if not exact_match and values:
                exact_match = values[0]
            
            if exact_match:
                # Select the matching item
                self.selected_country.set(exact_match)
                self.country_menu.set(exact_match)
                
                # Trigger the country changed event
                self.on_country_changed()
                
                # Reset search state
                self.last_search_term = ""
                self.country_menu['values'] = self.original_country_list

    def on_combobox_focus_lost(self, event=None):
        """Reset the combobox when it loses focus"""
        # Wait a moment to avoid conflicts with selection
        self.root.after(100, self._delayed_combobox_focus_lost)

    def _delayed_combobox_focus_lost(self):
        """Delayed handling of focus loss"""
        # Only reset if no selection was made
        if not self.typing_started:
            # Get current selected country
            current = self.selected_country.get()
            
            # Reset the dropdown text to match the selected country
            if current and current in self.data_processor.countries:
                self.country_menu.set(current)
    
        # Always reset typing flag and dropdown list
        self.typing_started = False
        self.country_menu['values'] = self.original_country_list
        self.last_search_term = ""

    def on_combobox_focus(self, event=None):
        """When focus enters the combobox, prepare for typing"""
        # Don't reset typing_started flag yet - wait for actual typing
        # Store the current text in case we need to restore it
        self.before_focus_text = self.country_menu.get()

    def on_country_changed(self, event=None):
        """Handle country selection change"""
        self.clear_console()
        
        # Get selected country
        selected_country = self.selected_country.get()
        dates = self.data_processor.get_dates()
        
        if dates:
            # Get console output for the selected country
            country_output, _, _ = self.data_processor.process_country_data_with_output(dates, selected_country)
            
            # Display in left console widget
            self.write_to_country_console(country_output)
            
            # Get total output for display in right console
            total_output = self.get_total_data_output(dates)
            self.write_to_summary_console(total_output)
            
            # Add summary section to right console
            summary_output = self.generate_summary_text()
            self.write_to_summary_console(summary_output)
    
        # Update plots
        self.update_plots()

    def update_data(self):
        """Update all data from the API"""
        # Add debug info
        print("================= UPDATE DATA STARTED =================")
        self.status_var.set("Updating data...")
        self.root.update_idletasks()
        
        # Clear console
        self.clear_console()
        
        # Process data
        selected_country = self.selected_country.get()
        dates = self.data_processor.get_dates()
        
        if dates:
            # Get console output for the selected country
            country_output, today_data, last_time_data = self.data_processor.process_country_data_with_output(dates, selected_country)
            
            # Display country data in left console
            self.write_to_country_console(country_output)
            
            # Process all other data normally
            self.data_processor.update_all_data()
            
            # Process total data for display in right console
            total_output = self.get_total_data_output(dates)
            self.write_to_summary_console(total_output)
            
            # Add summary section to right console
            summary_output = self.generate_summary_text()
            self.write_to_summary_console(summary_output)
            
            # Update plots
            self.update_plots()
            
            # IMPORTANT: Get FRESH current total votes directly from the website
            # This ensures we always have the latest data when clicking Update Now
            try:
                # Get the latest vote count
                fresh_total = self.data_processor.get_live_total()
                
                print(f"FRESH REQUEST:")
                print(f"  Using presence_now.json endpoint")
                print(f"  Old total: {self.current_total_votes}")
                print(f"  New total: {fresh_total}")
                
                if fresh_total > 0:
                    # Update current_total_votes with fresh data
                    self.current_total_votes = fresh_total
                    
                    # Initialize hour_start_votes if this is the first update
                    if self.hour_start_votes == 0:
                        now = datetime.now()
                        # If we're at the start of the hour (within first minute), set it to current
                        if now.minute < 2:
                            self.hour_start_votes = fresh_total
                        else:
                            # Otherwise, estimate the value at the start of the hour
                            hourly_inc = max(1, self.data_processor.LATEST_DATA['total'].get('hourly_increase', 1000))
                            estimated_hour_votes = int(hourly_inc * (now.minute / 60))
                            self.hour_start_votes = max(0, fresh_total - estimated_hour_votes)
                        
                        print(f"  Initialized hour_start_votes to: {self.hour_start_votes}")
            except Exception as e:
                print(f"Error fetching fresh data: {e}")
                # Fall back to the data from the normal update process
                if 'total' in self.data_processor.LATEST_DATA:
                    self.current_total_votes = self.data_processor.LATEST_DATA['total']['round2']
    
        # Update status with vote info
        now = datetime.now()
        current_hour = now.hour
        hourly_votes = 0
        if self.hour_start_votes > 0:
            hourly_votes = max(0, self.current_total_votes - self.hour_start_votes)
    
        print(f"STATUS UPDATE VALUES:")
        print(f"  hour_start_votes: {self.hour_start_votes}")
        print(f"  current_total_votes: {self.current_total_votes}")
        print(f"  calculated hourly_votes: {hourly_votes}")
        
        # Update status with vote info
        next_update, seconds = self.data_processor.calculate_next_update_time()

        # Format the status message with vote count
        status_msg = (f"Last updated: {now.strftime('%H:%M:%S')} - "
                    f"Next update: {next_update.strftime('%H:%M:%S')} - "
                    f"New votes since {current_hour:02d}:00: +{hourly_votes:,}")

        self.status_var.set(status_msg)
        print(f"  Status set to: {status_msg}")
        
        print("================= UPDATE DATA FINISHED =================")

    def get_total_data_output(self, dates):
        """Get formatted total data output for the console"""
        output_lines = []
        
        # Header
        output_lines.append("\n" + TABLE_DIVIDER_CHAR * TABLE_HEADER_LEN)
        output_lines.append(f"  DATE PENTRU TOTAL VOTURI  ".center(TABLE_HEADER_LEN, TABLE_DIVIDER_CHAR))
        output_lines.append(TABLE_DIVIDER_CHAR * TABLE_HEADER_LEN)
        
        # Table header
        tw = TABLE_COL_WIDTHS
        output_lines.append(f"┌{'─'*tw['time']}┬{'─'*tw['round']}┬{'─'*tw['round']}┬{'─'*tw['diff']}┬{'─'*tw['hourly']}┬{'─'*tw['delta']}┐")
        output_lines.append(f"│{' Data ':^{tw['time']}}│{' Tur 2 ':^{tw['round']}}│{' Tur 1 ':^{tw['round']}}│{' Diferență ':^{tw['diff']}}│{' Creștere orară ':^{tw['hourly']}}│{' Delta ':^{tw['delta']}}│")
        output_lines.append(f"├{'─'*tw['time']}┼{'─'*tw['round']}┼{'─'*tw['round']}┼{'─'*tw['diff']}┼{'─'*tw['hourly']}┼{'─'*tw['delta']}┤")
        
        # For tracking hourly increases
        prev_hour_data = 0
        
        today_data = []
        last_time_data = []
        
        for i, (day, hour) in enumerate(dates):
            # Build URLs
            url_today = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND2}/data/json/simpv/presence/presence_2025-05-{day:02d}_{hour:02d}-00.json"
            url_prev = f"https://prezenta.roaep.ro/prezidentiale{ELECTION_DATE_ROUND1}/data/json/simpv/presence/presence_2025-05-{(day-DATE_DIFF):02d}_{hour:02d}-00.json"
            
            # Get data
            _, total_today = self.data_processor.extract_total(url_today)
            _, total_prev = self.data_processor.extract_total(url_prev)
            
            today_data.append(total_today)
            last_time_data.append(total_prev)
            
            # Calculate hourly increase
            hourly_increase = total_today - prev_hour_data if i > 0 else total_today
            prev_hour_data = total_today
            
            # Format the time string
            time_str = f"[{day:02d} {hour:02d}:01]"
            
            # Add table row to output
            diff = total_today - total_prev
            hourly_str = f"{hourly_increase:+,d}" if i > 0 else "N/A"
            delta_str = f"{(diff / total_prev * 100):+.2f}%" if total_prev > 0 else "N/A"
            
            output_lines.append(f"│{time_str:^{tw['time']}}│{total_today:>{tw['round']},d}│{total_prev:>{tw['round']},d}│{diff:>+{tw['diff']},d}│{hourly_str:^{tw['hourly']}}│{delta_str:^{tw['delta']}}│")
        
        # Add table footer
        output_lines.append(f"└{'─'*tw['time']}┴{'─'*tw['round']}┴{'─'*tw['round']}┴{'─'*tw['diff']}┴{'─'*tw['hourly']}┴{'─'*tw['delta']}┘")
        
        return "\n".join(output_lines)

    def generate_summary_text(self):
        """Generate summary text for console display"""
        output_lines = []
        
        # Header
        output_lines.append("\n" + TABLE_SUMMARY_DIVIDER_CHAR * TABLE_SUMMARY_HEADER_LEN)
        output_lines.append("  REZUMAT DATE RECENTE  ".center(TABLE_SUMMARY_HEADER_LEN, TABLE_SUMMARY_DIVIDER_CHAR))
        output_lines.append(TABLE_SUMMARY_DIVIDER_CHAR * TABLE_SUMMARY_HEADER_LEN)
        
        # Get last date
        dates = self.data_processor.get_dates()
        if not dates:
            return "\nNo date information available"
        
        last_day, last_hour = dates[-1]
        
        # Table header
        tw = TABLE_COL_WIDTHS
        output_lines.append(f"┌{'─'*tw['time']}┬{'─'*tw['country']}┬{'─'*tw['round']}┬{'─'*tw['round']}┬{'─'*tw['diff']}┬{'─'*tw['hourly']}┬{'─'*tw['delta']}┐")
        output_lines.append(f"│{' Data ':^{tw['time']}}│{' Țară ':^{tw['country']}}│{' Tur 2 ':^{tw['round']}}│{' Tur 1 ':^{tw['round']}}│{' Diferență ':^{tw['diff']}}│{' Creștere orară ':^{tw['hourly']}}│{' Delta ':^{tw['delta']}}│")
        output_lines.append(f"├{'─'*tw['time']}┼{'─'*tw['country']}┼{'─'*tw['round']}┼{'─'*tw['round']}┼{'─'*tw['diff']}┼{'─'*tw['hourly']}┼{'─'*tw['delta']}┤")
        
        time_str = f"[{last_day:02d} {last_hour:02d}:00]"
        
        # Generate rows for each country
        for country in COUNTRIES:
            data = self.data_processor.LATEST_DATA.get(country, {})
            r1 = data.get('round1', 0)
            r2 = data.get('round2', 0)
            hourly = data.get('hourly_increase', 0)
            diff = r2 - r1
            
            # Shorten UK name for display
            display_country = "MAREA BRITANIE" if country == "REGATUL UNIT AL MARII BRITANII \u0218I AL IRLANDEI DE NORD" else country
            
            if r1 > 0:
                delta = round(diff / r1 * 100, 2)
                delta_str = f"{delta:+.2f}%"
            else:
                delta_str = "N/A"
            
            output_lines.append(f"│{time_str:^{tw['time']}}│{display_country:^{tw['country']}}│{r2:>{tw['round']},d}│{r1:>{tw['round']},d}│{diff:>+{tw['diff']},d}│{hourly:>+{tw['hourly']},d}│{delta_str:^{tw['delta']}}│")
        
        # Add Romania and Total rows
        self.add_summary_output_row(output_lines, time_str, ROMANIA_NAME, ROMANIA_NAME)
        self.add_summary_output_row(output_lines, time_str, 'total', 'TOTAL')
        
        # Table footer
        output_lines.append(f"└{'─'*tw['time']}┴{'─'*tw['country']}┴{'─'*tw['round']}┴{'─'*tw['round']}┴{'─'*tw['diff']}┴{'─'*tw['hourly']}┴{'─'*tw['delta']}┘")
        
        return "\n".join(output_lines)

    def add_summary_output_row(self, output_lines, time_str, data_key, display_name):
        """Add a summary row to the output lines list"""
        tw = TABLE_COL_WIDTHS
        data = self.data_processor.LATEST_DATA.get(data_key, {})
        r1 = data.get('round1', 0)
        r2 = data.get('round2', 0)
        hourly = data.get('hourly_increase', 0)
        diff = r2 - r1
        
        if r1 > 0:
            delta = round(diff / r1 * 100, 2)
            delta_str = f"{delta:+.2f}%"
        else:
            delta_str = "N/A"
        
        output_lines.append(f"│{time_str:^{tw['time']}}│{display_name:^{tw['country']}}│{r2:>{tw['round']},d}│{r1:>{tw['round']},d}│{diff:>+{tw['diff']},d}│{hourly:>+{tw['hourly']},d}│{delta_str:^{tw['delta']}}│")

    def update_plots(self):
        """Update the matplotlib plots"""
        selected_country = self.selected_country.get()
        dates = self.data_processor.get_dates()
        
        if not dates:
            return
        
        # Clear existing plots
        for ax in self.axes:
            ax.clear()
        
        # Plot selected country data
        if selected_country in self.data_processor.country_data:
            today_data = self.data_processor.country_data[selected_country]['today']
            last_time_data = self.data_processor.country_data[selected_country]['previous']
            self.data_processor.plot_voting_data(self.ax1, f"Voturi {selected_country}", 
                                              today_data, last_time_data, dates)
        
        # Plot Romania data
        if ROMANIA_NAME in self.data_processor.country_data:
            today_data = self.data_processor.country_data[ROMANIA_NAME]['today']
            last_time_data = self.data_processor.country_data[ROMANIA_NAME]['previous']
            self.data_processor.plot_voting_data(self.ax2, f"Voturi {ROMANIA_NAME} (fără străinătate)", 
                                              today_data, last_time_data, dates)
        
        # Plot total votes data
        if 'total' in self.data_processor.country_data:
            today_data = self.data_processor.country_data['total']['today']
            last_time_data = self.data_processor.country_data['total']['previous']
            self.data_processor.plot_voting_data(self.ax3, "Total voturi", 
                                              today_data, last_time_data, dates)
        
        # Plot combined stats
        delta_percents = self.data_processor.delta_percents
        hourly_increases = self.data_processor.hourly_increases
        if delta_percents and hourly_increases:
            self.data_processor.plot_combined_stats(self.ax4, delta_percents, hourly_increases, dates)
        
        # Adjust layout
        self.fig.tight_layout()
        self.canvas.draw()

    def update_summary(self):
        """Update the summary console with latest data"""
        # Clear summary console
        self.summary_text.delete(1.0, tk.END)
        
        # Generate and display summary text
        summary_output = self.generate_summary_text()
        self.write_to_summary_console(summary_output)

    def on_closing(self):
        """Clean up when closing the window"""
        self.running = False
        self.root.destroy()

    def update_vote_count(self):
        """Update the current total votes count and refresh the display"""
        try:
            # Only do this if we have data
            if 'total' in self.data_processor.LATEST_DATA:
                # Get the latest total
                new_total = self.data_processor.LATEST_DATA['total']['round2']
                
                # Update the current total
                self.current_total_votes = new_total
                
                # Initialize hour_start_votes if needed
                if self.hour_start_votes == 0:
                    now = datetime.now()
                    if now.minute < 2:
                        self.hour_start_votes = new_total
                    else:
                        hourly_inc = max(1, self.data_processor.LATEST_DATA['total'].get('hourly_increase', 1000))
                        estimated_hour_votes = int(hourly_inc * (now.minute / 60))
                        self.hour_start_votes = max(0, new_total - estimated_hour_votes)
                
                # Update the display
                self.update_new_votes_display()
                return True
            return False
        except Exception as e:
            print(f"Error updating vote count: {e}")
            return False

    # Add this method to your ElectionMonitorApp class
    def auto_update(self):
        """Background thread for automatic updates"""
        last_update_hour = datetime.now().hour
        
        while self.running:
            now = datetime.now()
            current_hour = now.hour
            current_minute = now.minute
            current_second = now.second
            
            # Update at the specified minute and second of each hour
            if (current_hour != last_update_hour and 
                current_minute >= UPDATE_MINUTE and current_second >= UPDATE_SECOND):
                
                # Update on the GUI thread
                self.root.after(0, self.update_data)
                last_update_hour = current_hour
            
            # Sleep briefly to avoid high CPU usage
            time.sleep(1)

    def update_new_votes_display(self):
        """Update the display of new votes in the current hour"""
        now = datetime.now()
        current_hour = now.hour
        
        # Calculate votes in current hour
        hourly_votes = 0
        if self.hour_start_votes > 0:
            hourly_votes = max(0, self.current_total_votes - self.hour_start_votes)
    
        # Update status with vote info
        next_update, seconds = self.data_processor.calculate_next_update_time()

        # Format the status message with vote count
        status_msg = (f"Last updated: {now.strftime('%H:%M:%S')} - "
                    f"Next update: {next_update.strftime('%H:%M:%S')} - "
                    f"New votes since {current_hour:02d}:00: +{hourly_votes:,}")

        self.status_var.set(status_msg)

    def update_new_votes_count(self):
        """Update only the time display without making web requests"""
        try:
            # Update just the time portion of the status message
            now = datetime.now()
            current_hour = now.hour
            next_update, seconds = self.data_processor.calculate_next_update_time()
            
            # Get the current vote count (without making a new request)
            hourly_votes = 0
            if self.hour_start_votes > 0:
                hourly_votes = max(0, self.current_total_votes - self.hour_start_votes)
            
            # Format the status message
            status_msg = (f"Last updated: {now.strftime('%H:%M:%S')} - "
                         f"Next update: {next_update.strftime('%H:%M:%S')} - "
                         f"New votes since {current_hour:02d}:00: +{hourly_votes:,}")
            
            self.status_var.set(status_msg)
                
        except Exception as e:
            print(f"Error updating time display: {e}")
        
        # Schedule next update in 1 second if still running
        if self.running:
            self.root.after(10000, self.update_new_votes_count)

    def schedule_next_hour_reset(self):
        """Schedule the next hourly reset of the vote counter"""
        now = datetime.now()
        
        # Calculate time until the next hour
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        delta = (next_hour - now).total_seconds() * 1000  # Convert to milliseconds for after()
        
        # Schedule the reset
        self.root.after(int(delta), self.reset_hour_start_votes)

    def reset_hour_start_votes(self):
        """Reset the vote counter at the start of a new hour"""
        self.hour_start_votes = self.current_total_votes
    
        # Update the display
        self.update_new_votes_display()
        
        # Schedule the next reset
        self.schedule_next_hour_reset()

    def update_clock(self):
        """Update the real-time clock display"""
        current_time = datetime.now().strftime('%H:%M:%S')
        self.clock_var.set(current_time)
        
        # Schedule the next update in 1000ms (1 second)
        if self.running:
            self.root.after(1000, self.update_clock)

# Add this at the end of the file
def main():
    root = tk.Tk()
    app = ElectionMonitorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()