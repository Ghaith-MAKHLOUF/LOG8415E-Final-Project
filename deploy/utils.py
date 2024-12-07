import os

def get_path(file_path):
    dirname = os.path.dirname(__file__)
    return os.path.join(dirname, file_path)

def write_file(file_path: str, data: str):
    filename = get_path(file_path)
    with open(filename, "w") as file:
        file.write(data)