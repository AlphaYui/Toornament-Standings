import json

class JSONStorage:
    "This class manages a JSON-array and adds methods to save it to a persistent file."

    def __init__(self, location: str):
        "location: Path to the JSON-file to load and save in."
        self.__location = location
        self.content = []
        self.__load()

    def save(self):
        "Saves the content of this storage to the given JSON-file."
        with open(self.__location, 'w', encoding='utf-8') as storage_file:
            json.dump(self.content, storage_file, indent=2)

    def __load(self):
        "Tries to load the content of this storage from the given JSON-file."
        try:
            with open(self.__location, 'r', encoding='utf-8') as storage_file:
                self.content = json.load(storage_file)
        except:
            pass
