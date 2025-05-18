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
        
        # Add ROMANIA to countries list and sort alphabetically
        if self.data_processor.countries:
            if ROMANIA_NAME not in self.data_processor.countries:
                self.data_processor.countries.append(ROMANIA_NAME)
            sorted_countries = sorted(self.data_processor.countries)
            self.data_processor.countries = sorted_countries
            self.selected_country = StringVar(root)
            # Start with ROMANIA selected by default
            self.selected_country.set(ROMANIA_NAME)
        else:
            countries_with_romania = COUNTRIES + [ROMANIA_NAME]
            sorted_countries = sorted(countries_with_romania)
            self.selected_country = StringVar(root)
            self.selected_country.set(ROMANIA_NAME)  # Default to ROMANIA
    
        # Variables for tracking vote changes
        self.hour_start_votes = 0      # Votes at the beginning of the hour
        self.current_total_votes = 0   # Current total votes
        
        # Add a flag to track if an update is in progress
        self.update_in_progress = False
        
        self.create_widgets()
        self.create_plots()
        
        # Initial update
        self.update_data()
        
        # After the initial update, properly initialize the hour_start_votes
        # based on the current hour
        now = datetime.now()
        if self.hour_start_votes == 0 and 'total' in self.data_processor.LATEST_DATA:
            # Use exactly the same total vote count from LATEST_DATA without estimation
            self.hour_start_votes = self.data_processor.LATEST_DATA['total']['round2']
            print(f"Initial baseline votes set to: {self.hour_start_votes:,} (from LATEST_DATA)")

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
        
        # Country selection - simple version without search
        ttk.Label(control_frame, text="Select Country:").pack(side=tk.LEFT, padx=5)
        
        # Create standard combobox
        self.country_menu = ttk.Combobox(control_frame, textvariable=self.selected_country, 
                      values=self.data_processor.countries, width=30, state="readonly")
        self.country_menu.pack(side=tk.LEFT, padx=5)
        
        # Bind the country selection event
        self.country_menu.bind("<<ComboboxSelected>>", self.on_country_changed)
        
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

    def on_country_changed(self, event=None):
        """Handle country selection change"""
        self.clear_console()
        
        # Get selected country
        selected_country = self.selected_country.get()
        dates = self.data_processor.get_dates()
        
        if dates:
            # Get console output for the selected country from existing data, don't fetch new data
            country_output, _, _ = self.data_processor.process_country_data_with_output(dates, selected_country)
            
            # Display in left console widget
            self.write_to_country_console(country_output)
            
            # Get total output for display in right console
            total_output = self.get_total_data_output(dates)
            self.write_to_summary_console(total_output)
            
            # Add summary section to right console
            summary_output = self.generate_summary_text()
            self.write_to_summary_console(summary_output)
            
            # Make sure plots are updated when country changes
            self.update_plots()

    def update_data(self):
        """Update all data from the API"""
        try:
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
                # Get the current live total from the API
                current_total = self.data_processor.get_live_total()
                
                # Update data processor
                self.data_processor.update_all_data()
                
                # Display selected country data
                country_output, today_data, last_time_data = self.data_processor.process_country_data_with_output(dates, selected_country)
                self.write_to_country_console(country_output)
                
                # Display summary data
                self.update_summary()
                
                # Update plots
                self.update_plots()
                
                # Store current total for next calculation
                if current_total > 0:
                    self.current_total_votes = current_total
    
                # Update hour_start_votes if this is a scheduled update
                now = datetime.now()
                if now.minute == UPDATE_MINUTE and now.second >= UPDATE_SECOND:
                    # Use the value from LATEST_DATA instead of current_total
                    if 'total' in self.data_processor.LATEST_DATA and 'round2' in self.data_processor.LATEST_DATA['total']:
                        self.hour_start_votes = self.data_processor.LATEST_DATA['total']['round2']
                        print(f"Regular update - reset baseline votes count to: {self.hour_start_votes}")
                # If hour_start_votes is not set (first run), set it to the value from LATEST_DATA
                elif self.hour_start_votes == 0:
                    if 'total' in self.data_processor.LATEST_DATA and 'round2' in self.data_processor.LATEST_DATA['total']:
                        self.hour_start_votes = self.data_processor.LATEST_DATA['total']['round2']
                        print(f"First run - initial baseline votes count: {self.hour_start_votes}")

            # Always update the display regardless of whether new data was fetched
            self.update_new_votes_display()  # This will update the status with vote count
            
            print("================= UPDATE DATA FINISHED =================")
            
        except Exception as e:
            # Log error and ensure UI isn't stuck
            print(f"Error during data update: {e}")
            import traceback
            traceback.print_exc()
            
            # Reset status to show error occurred
            now = datetime.now()
            self.status_var.set(f"Update failed at {now.strftime('%H:%M:%S')} - Check console for errors")

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
        
        selected_country = self.selected_country.get()
        
        # Special handling for ROMANIA - use the data from the ROMANIA key in country_data
        if selected_country == ROMANIA_NAME and ROMANIA_NAME in self.data_processor.country_data:
            today_data = self.data_processor.country_data[ROMANIA_NAME]['today']
            last_time_data = self.data_processor.country_data[ROMANIA_NAME]['previous']
            
            for i, (day, hour) in enumerate(dates):
                # Format the time string
                time_str = f"[{day:02d} {hour:02d}:01]"
                
                # Get values for this timestamp
                total_today = today_data[i] if i < len(today_data) else 0
                total_prev = last_time_data[i] if i < len(last_time_data) else 0
                diff = total_today - total_prev
                
                # Calculate hourly increase
                hourly_increase = total_today - prev_hour_data if i > 0 else 0
                hourly_str = f"{int(hourly_increase):+,d}" if i > 0 else "N/A"
                prev_hour_data = total_today
                
                # Calculate delta percentage
                delta_str = f"{(diff / total_prev * 100):+.2f}%" if total_prev > 0 else "N/A"
                
                output_lines.append(f"│{time_str:^{tw['time']}}│{int(total_today):>{tw['round']},d}│{int(total_prev):>{tw['round']},d}│{int(diff):>+{tw['diff']},d}│{hourly_str:^{tw['hourly']}}│{delta_str:^{tw['delta']}}│")
        # For any other country or total, use the regular data
        elif 'total' in self.data_processor.country_data and selected_country != ROMANIA_NAME:
            key = 'total' if selected_country == 'total' else selected_country
            if key in self.data_processor.country_data:
                today_data = self.data_processor.country_data[key]['today']
                last_time_data = self.data_processor.country_data[key]['previous']
                
                for i, (day, hour) in enumerate(dates):
                    # Format the time string
                    time_str = f"[{day:02d} {hour:02d}:01]"
                    
                    # Get values for this timestamp
                    total_today = today_data[i] if i < len(today_data) else 0
                    total_prev = last_time_data[i] if i < len(last_time_data) else 0
                    diff = total_today - total_prev
                    
                    # Calculate hourly increase
                    hourly_increase = total_today - prev_hour_data if i > 0 else 0
                    hourly_str = f"{int(hourly_increase):+,d}" if i > 0 else "N/A"
                    prev_hour_data = total_today
                    
                    # Calculate delta percentage
                    delta_str = f"{(diff / total_prev * 100):+.2f}%" if total_prev > 0 else "N/A"
                    
                    output_lines.append(f"│{time_str:^{tw['time']}}│{int(total_today):>{tw['round']},d}│{int(total_prev):>{tw['round']},d}│{int(diff):>+{tw['diff']},d}│{hourly_str:^{tw['hourly']}}│{delta_str:^{tw['delta']}}│")
    
        # Add table footer
        output_lines.append(f"└{'─'*tw['time']}┴{'─'*tw['round']}┴{'─'*tw['round']}┴{'─'*tw['diff']}┴{'─'*tw['hourly']}┴{'─'*tw['delta']}┘")
        
        return "\n".join(output_lines)

    def generate_summary_text(self):
        """Generate summary text for console display"""
        output_lines = []
    
        # Add total votes history section
        output_lines.append("\n" + TABLE_SUMMARY_DIVIDER_CHAR * TABLE_SUMMARY_HEADER_LEN)
        output_lines.append("  ISTORICUL VOTURILOR TOTALE  ".center(TABLE_SUMMARY_HEADER_LEN, TABLE_SUMMARY_DIVIDER_CHAR))
        output_lines.append(TABLE_SUMMARY_DIVIDER_CHAR * TABLE_SUMMARY_HEADER_LEN)
        
        # Get total votes history from data processor
        dates = self.data_processor.get_dates()
        if dates and 'total' in self.data_processor.country_data:
            today_data = self.data_processor.country_data['total']['today']
            last_time_data = self.data_processor.country_data['total']['previous']
            
            # Table header for history
            tw = TABLE_COL_WIDTHS
            output_lines.append(f"┌{'─'*tw['time']}┬{'─'*tw['round']}┬{'─'*tw['round']}┬{'─'*tw['diff']}┬{'─'*tw['hourly']}┬{'─'*tw['delta']}┐")
            output_lines.append(f"│{' Data ':^{tw['time']}}│{' Tur 2 ':^{tw['round']}}│{' Tur 1 ':^{tw['round']}}│{' Diferență ':^{tw['diff']}}│{' Creștere orară ':^{tw['hourly']}}│{' Delta ':^{tw['delta']}}│")
            output_lines.append(f"├{'─'*tw['time']}┼{'─'*tw['round']}┼{'─'*tw['round']}┼{'─'*tw['diff']}┼{'─'*tw['hourly']}┼{'─'*tw['delta']}┤")
            
            # Add rows for each timestamp
            prev_today = 0
            for i, (day, hour) in enumerate(dates):
                time_str = f"[{day:02d} {hour:02d}:00]"
                
                # Get values for this timestamp
                total_today = today_data[i] if i < len(today_data) else 0
                total_prev = last_time_data[i] if i < len(last_time_data) else 0
                diff = total_today - total_prev
                
                # Calculate hourly increase
                hourly_increase = total_today - prev_today if i > 0  else 0
                hourly_str = f"{int(hourly_increase):+,d}" if i > 0 else "N/A"
                prev_today = total_today
                
                # Calculate delta percentage
                delta_str = f"{(diff / total_prev * 100):+.2f}%" if total_prev > 0 else "N/A"
                
                # Convert to integers before formatting to avoid the "float" error
                output_lines.append(f"│{time_str:^{tw['time']}}│{int(total_today):>{tw['round']},d}│{int(total_prev):>{tw['round']},d}│{int(diff):>+{tw['diff']},d}│{hourly_str:^{tw['hourly']}}│{delta_str:^{tw['delta']}}│")
                
            # Table footer
            output_lines.append(f"└{'─'*tw['time']}┴{'─'*tw['round']}┴{'─'*tw['round']}┴{'─'*tw['diff']}┴{'─'*tw['hourly']}┴{'─'*tw['delta']}┘")

        # Header for summary section (existing code)
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
        
        # Generate rows for each country - using case-insensitive comparison 
        for country in [c for c in COUNTRIES if c.upper() != ROMANIA_NAME.upper()]:
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
        
        # Add Romania row - using case-insensitive lookup
        # Look for romania in any case form
        romania_key = next((k for k in self.data_processor.LATEST_DATA.keys() if k.upper() == ROMANIA_NAME.upper()), None)
        
        if romania_key:
            data = self.data_processor.LATEST_DATA.get(romania_key, {})
            r1 = data.get('round1', 0) 
            r2 = data.get('round2', 0)
            hourly = data.get('hourly_increase', 0)
            diff = r2 - r1
            
            display_name = f"{ROMANIA_NAME} (fără străinătate)"
            
            if r1 > 0:
                delta = round(diff / r1 * 100, 2)
                delta_str = f"{delta:+.2f}%"
            else:
                delta_str = "N/A"
            
            output_lines.append(f"│{time_str:^{tw['time']}}│{display_name:^{tw['country']}}│{r2:>{tw['round']},d}│{r1:>{tw['round']},d}│{diff:>+{tw['diff']},d}│{hourly:>+{tw['hourly']},d}│{delta_str:^{tw['delta']}}│")
        
        # Add Total row
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
        
        # Enable hover functionality by connecting the canvas events
        self.canvas.mpl_connect('motion_notify_event', self._on_hover)

    def _on_hover(self, event):
        # This method exists to ensure the figure redraws properly when hovering
        # The actual hover logic is handled in the plot_voting_data and plot_combined_stats methods
        pass

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
                # Get the latest total directly from LATEST_DATA
                new_total = self.data_processor.LATEST_DATA['total']['round2']
                
                # Update the current total
                self.current_total_votes = new_total
                
                # Initialize hour_start_votes if needed - use exact value from data
                if self.hour_start_votes == 0:
                    self.hour_start_votes = new_total
            
                # Update the display
                self.update_new_votes_display()
                return True
            return False
        except Exception as e:
            print(f"Error updating vote count: {e}")
            return False

    def update_new_votes_display(self):
        """Update the display of new votes in the current hour"""
        try:
            now = datetime.now()
            current_hour = now.hour
            
            # Make sure we have the most accurate current total
            # First try to get live total
            latest_total = self.data_processor.get_live_total()
            
            # If successful, use that value
            if latest_total > 0:
                self.current_total_votes = latest_total
            # Otherwise fall back to cached data
            elif 'total' in self.data_processor.LATEST_DATA and 'round2' in self.data_processor.LATEST_DATA['total']:
                self.current_total_votes = self.data_processor.LATEST_DATA['total']['round2']

            # Calculate new votes since hour start
            hourly_votes = 0
            if self.hour_start_votes > 0:
                hourly_votes = max(0, self.current_total_votes - self.hour_start_votes)
            
            # Get next update time
            next_update, seconds = self.data_processor.calculate_next_update_time()
            
            # Format the status message with vote count (removed Romania counter)
            status_msg = (f"Last updated: {now.strftime('%H:%M:%S')} - "
                        f"Next update: {next_update.strftime('%H:%M:%S')} - "
                        f"New votes since {current_hour:02d}:00: +{hourly_votes:,}")
            
            # Actually update the status var with the complete message
            self.status_var.set(status_msg)
            print(f"Display updated: Hour baseline: {self.hour_start_votes:,}, Current total: {self.current_total_votes:,}, "
                  f"New votes: +{hourly_votes:,}")
            
        except Exception as e:
            print(f"Error updating vote display: {e}")
            import traceback
            traceback.print_exc()

    def update_new_votes_count(self):
        """Update the vote count in the status bar"""
        try:
            # Get the latest total from data processor
            latest_total = self.data_processor.LATEST_DATA['total']['round2']
            
            # Calculate new votes since the hour start
            # Use abs() to ensure we always show a positive value
            new_votes = abs(latest_total - self.hour_start_votes) if self.hour_start_votes > 0 else 0
            
            # Update the status bar
            current_status = self.status_var.get()
            # Replace just the vote count part at the end of the status message
            now = datetime.now()
            current_hour = now.hour
            prefix = current_status.split(f"New votes since {current_hour:02d}:00:")[0]
            self.status_var.set(f"{prefix}New votes since {current_hour:02d}:00: +{abs(new_votes):,}")
            
            # Remove auto-scheduling - only update when button is clicked
        except Exception as e:
            print(f"Error updating vote count: {e}")
            # Remove auto-scheduling here too

    def schedule_next_hour_reset(self):
        """
        This method is no longer used as we synchronize vote counter resets 
        with the data updates at the configured time (UPDATE_MINUTE:UPDATE_SECOND)
        """
        pass

    def reset_hour_start_votes(self):
        """Reset the hour's starting vote count without checking for updates."""
        # Only reset the counter, don't check for new data
        self.hour_start_votes = self.current_total_votes
    
        # Schedule next hour reset
        self.schedule_next_hour_reset()

    def update_clock(self):
        """Update the clock display and check for scheduled updates."""
        # Update the clock display
        now = datetime.now()
        time_str = now.strftime("%d/%m/%Y %H:%M:%S")
        self.clock_var.set(time_str)
        
        # Check if it's time for a scheduled update (XX:01:01)
        if now.minute == UPDATE_MINUTE and now.second == UPDATE_SECOND:
            print(f"Auto update triggered at {now.strftime('%H:%M:%S')}")
            if not self.update_in_progress:
                # Start update in a background thread
                update_thread = threading.Thread(target=self.run_update)
                update_thread.daemon = True
                update_thread.start()
        
        # Schedule the next clock update in 1 second
        self.root.after(1000, self.update_clock)

    def run_update(self):  # Fixed indentation - moved out of update_clock to class level
        """Run the update in a separate thread to avoid freezing the UI"""
        try:
            self.update_in_progress = True
            self.update_data()
        finally:
            self.update_in_progress = False

# Add this at the end of the file
def main():
    root = tk.Tk()
    app = ElectionMonitorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()