import json

def loaddwcdb():
    dwcdb = {}
    try:
        with open('data/dwcdb.json', 'r', encoding='utf-8') as f:
            dwcdb = json.load(f)
    except FileNotFoundError:
        pass
    except json.JSONDecodeError as e:
        print(f"Error loading JSON: {e}")
    return dwcdb

def savedwcdb(dwcdb):
    try:
        with open('data/dwcdb.json', 'w', encoding='utf-8') as f:
            json.dump(dwcdb, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving JSON file: {e}")
        raise