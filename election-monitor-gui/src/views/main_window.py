from tkinter import Tk, StringVar, OptionMenu, Frame
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from src.views.graph_panel import GraphPanel
from src.views.summary_panel import SummaryPanel
from src.data.constants import COUNTRIES

class MainWindow:
    def __init__(self, master):
        self.master = master
        self.master.title("Election Monitor")
        
        self.selected_country = StringVar(master)
        self.selected_country.set(COUNTRIES[0])  # Set default value
        
        self.country_menu = OptionMenu(master, self.selected_country, *COUNTRIES, command=self.update_graphs)
        self.country_menu.pack(pady=10)
        
        self.graph_frame = Frame(master)
        self.graph_frame.pack(pady=10)
        
        self.graph_panel = GraphPanel(self.graph_frame)
        self.graph_panel.pack()
        
        self.summary_panel = SummaryPanel(master)
        self.summary_panel.pack(pady=10)
        
        self.update_graphs(self.selected_country.get())

    def update_graphs(self, country):
        self.graph_panel.display_graphs(country)
        self.summary_panel.update_summary(country)

def run_app():
    root = Tk()
    app = MainWindow(root)
    root.mainloop()

if __name__ == "__main__":
    run_app()