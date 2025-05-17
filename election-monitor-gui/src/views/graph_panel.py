from tkinter import Frame, Label, StringVar, OptionMenu
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from src.services.api_service import fetch_election_data  # Assuming this function exists
from src.data.constants import COUNTRIES

class GraphPanel(Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.selected_country = StringVar(value=COUNTRIES[0])
        self.create_widgets()

    def create_widgets(self):
        self.country_label = Label(self, text="Select Country:")
        self.country_label.pack()

        self.country_dropdown = OptionMenu(self, self.selected_country, *COUNTRIES, command=self.update_graphs)
        self.country_dropdown.pack()

        self.graph_frame = Frame(self)
        self.graph_frame.pack()

        self.pack()

    def update_graphs(self, *args):
        country = self.selected_country.get()
        self.display_graphs(country)

    def display_graphs(self, country):
        # Clear previous graphs
        for widget in self.graph_frame.winfo_children():
            widget.destroy()

        # Fetch election data for the selected country
        data = fetch_election_data(country)  # This function should return the necessary data

        # Example of creating a graph (replace with actual data processing and plotting)
        fig, ax = plt.subplots()
        ax.plot(data['dates'], data['votes'], label=f'Votes in {country}')
        ax.set_title(f'Voting Data for {country}')
        ax.set_xlabel('Date')
        ax.set_ylabel('Votes')
        ax.legend()

        # Embed the plot in the Tkinter window
        canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack()