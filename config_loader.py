import yaml

def load_config(path="config.yaml"):
    with open(path, "r", encoding='utf-8') as file:
        return yaml.safe_load(file)
