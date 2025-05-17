# Election Monitor GUI

This project is a graphical user interface (GUI) application designed to monitor and visualize election data. Users can select a country from a dropdown menu and view various graphs related to the election results.

## Project Structure

The project is organized as follows:

```
election-monitor-gui
├── src
│   ├── main.py                # Entry point of the application
│   ├── data
│   │   ├── cache.json         # Cached data to avoid repeated API calls
│   │   └── constants.py       # Configuration constants
│   ├── models
│   │   ├── __init__.py        # Empty initializer for models package
│   │   └── election_data.py    # Data models for election data
│   ├── services
│   │   ├── __init__.py        # Empty initializer for services package
│   │   ├── api_service.py      # Functions to interact with external APIs
│   │   └── data_processor.py    # Functions to process and analyze election data
│   ├── utils
│   │   ├── __init__.py        # Empty initializer for utils package
│   │   └── helpers.py          # Utility functions for various tasks
│   ├── views
│   │   ├── __init__.py        # Empty initializer for views package
│   │   ├── main_window.py      # Main window of the GUI
│   │   ├── graph_panel.py      # Implementation for displaying election graphs
│   │   └── summary_panel.py    # Summary view of election data
│   └── controllers
│       ├── __init__.py        # Empty initializer for controllers package
│       └── app_controller.py   # Manages application logic and user interactions
├── requirements.txt            # Project dependencies
├── setup.py                    # Setup script for the project
└── README.md                   # Documentation for the project
```

## Installation

To set up the project, follow these steps:

1. Clone the repository:
   ```
   git clone <repository-url>
   cd election-monitor-gui
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python src/main.py
   ```

## Usage

- Upon launching the application, you will see a dropdown menu to select a country.
- After selecting a country, the application will display various graphs related to the election data for that country.
- The application fetches data from external APIs and processes it for visualization.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any suggestions or improvements.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.