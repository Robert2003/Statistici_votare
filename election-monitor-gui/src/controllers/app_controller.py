from tkinter import Tk, StringVar, OptionMenu, Frame
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from src.services.api_service import fetch_election_data
from src.views.graph_panel import GraphPanel

class AppController:
    def __init__(self, master):
        self.master = master
        self.master.title("Election Monitor")
        
        self.selected_country = StringVar()
        self.countries = ["REGATUL UNIT AL MARII BRITANII ȘI AL IRLANDEI DE NORD", "GERMANIA", "FRANȚA", "ITALIA", "SPANIA", "REGATUL ȚĂRILOR DE JOS", "REPUBLICA MOLDOVA"]
        self.selected_country.set(self.countries[0])  # Default selection
        
        self.create_widgets()
        self.graph_panel = GraphPanel(self.master)

    def create_widgets(self):
        frame = Frame(self.master)
        frame.pack(pady=20)

        dropdown = OptionMenu(frame, self.selected_country, *self.countries, command=self.update_graphs)
        dropdown.pack()

    def update_graphs(self, *args):
        country = self.selected_country.get()
        election_data = fetch_election_data(country)
        self.graph_panel.display_graphs(election_data)

def main():
    root = Tk()
    app = AppController(root)
    root.mainloop()

if __name__ == "__main__":
    main()