from tkinter import Frame, Label, StringVar, OptionMenu
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

class SummaryPanel(Frame):
    def __init__(self, master, countries, data_fetcher):
        super().__init__(master)
        self.countries = countries
        self.data_fetcher = data_fetcher
        self.selected_country = StringVar(value=countries[0])
        
        self.create_widgets()
        
    def create_widgets(self):
        self.country_label = Label(self, text="Select Country:")
        self.country_label.pack()

        self.country_menu = OptionMenu(self, self.selected_country, *self.countries, command=self.update_graphs)
        self.country_menu.pack()

        self.graph_frame = Frame(self)
        self.graph_frame.pack()

        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.get_tk_widget().pack()

        self.update_graphs(self.selected_country.get())

    def update_graphs(self, country):
        self.ax.clear()
        data = self.data_fetcher.fetch_data_for_country(country)
        
        if data:
            self.ax.plot(data['x'], data['y'], label=f"Data for {country}")
            self.ax.set_title(f"Election Data for {country}")
            self.ax.set_xlabel("X-axis Label")
            self.ax.set_ylabel("Y-axis Label")
            self.ax.legend()
            self.canvas.draw()