import json
import os

class Config:
    def __init__(self):
        self.screen_position = 'top'
        self.transparency = 0.8
        self.doc_sources = ['man', 'help', 'online']
        self.url_patterns = {'default': 'https://www.google.com/search?q={query}'}
        self.shortcut = '<Control>+<space>'
        self.config_file = os.path.expanduser('~/.config/wingman/config.json')

        self.load()

    def load(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
                self.__dict__.update(config_data)

    def save(self):
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.__dict__, f, indent=4)

if __name__ == '__main__':
    config = Config()
    print(f'Loaded config from {config.config_file}')
    print(f'Shortcut: {config.shortcut}')
    config.shortcut = '<Control>+<Alt>+<space>'
    config.save()
    print('Saved new shortcut')
