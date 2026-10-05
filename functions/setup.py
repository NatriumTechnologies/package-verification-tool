import json

def loadsetup():
    with open("data/setup.json", "r") as f:
        return json.load(f)

def savesetup(setup):
    with open("data/setup.json", "w") as f:
        json.dump(setup, f, indent=4)