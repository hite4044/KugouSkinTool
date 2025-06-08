from os import makedirs, walk
from os.path import basename, isdir, isfile, split, join

from src.kugou_skin_tool.lib import suitskin


def extract_skin(file: str):
    dir_name = f"skin_extract_{basename(file)}"
    skin = suitskin.KugouSuitSkin(file)
    makedirs(dir_name, exist_ok=True)
    for file in skin.files:
        print(file.filename, file.file_size)
        with open(f"{dir_name}/{file.filename}", "wb") as f:
            f.write(file.content)


def merge_as_skin(dir_path: str):
    skin = suitskin.KugouSuitSkin()
    root, dirs, files = next(walk(dir_path))
    for file_name in files:
        file_path = join(root, file_name)
        with open(file_path, "rb") as f:
            skin.add_file(basename(file_path), f.read())
    name = "pack_" + split(dir_path)[-1].rstrip('.suitskin').lstrip('skin_extract_')
    skin.save(f"{name}.suitskin")


def main():
    print("1. 输入为空时导出工作目录下所有.suitskin文件")
    print("2. 输入为文件时导出该.suitskin文件")
    print("3. 输入为目录时将目录下的文件合成为.suitskin文件")
    data = input("输入数据: ")
    if data == "":
        root, dirs, files = next(walk("../../tools"))
        print(root, dirs, files)
        for file_name in files:
            print(file_name)
            file_path = join(root, file_name)
            if file_path.endswith(".suitskin"):
                extract_skin(file_path)
    elif isfile(data):
        extract_skin(data)
    elif isdir(data):
        merge_as_skin(data)


if __name__ == "__main__":
    main()
