from typing import List, Dict

class ElectionData:
    def __init__(self):
        self.data = {}

    def load_data(self, country: str) -> None:
        # Load election data for the specified country
        # This method should interact with the API service to fetch data
        pass

    def get_total_votes(self, country: str) -> int:
        # Return the total votes for the specified country
        return self.data.get(country, {}).get('total_votes', 0)

    def get_country_data(self, country: str) -> Dict:
        # Return all data related to the specified country
        return self.data.get(country, {})

    def update_data(self, country: str, new_data: Dict) -> None:
        # Update the election data for the specified country
        self.data[country] = new_data

    def get_all_countries(self) -> List[str]:
        # Return a list of all countries for which data is available
        return list(self.data.keys())