import json

def loadconfig():
    with open("data/config.json", "r") as f:
        return json.load(f)
    
def saveconfig(data):
    with open('data/config.json', 'w') as file:
        json.dump(data, file, indent=4)