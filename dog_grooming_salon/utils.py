import yaml
from pathlib import Path
import os


CONFIG_FILE = os.path.join(Path(__file__).resolve().parent.parent, 'config.yml')


def load_config(config_param):
    """
    To load a config parameter from the config file.
    Returns a single value or a dictionary.
    """
    with open(CONFIG_FILE) as config_file:
        config = yaml.safe_load(config_file)
    return config[config_param]
