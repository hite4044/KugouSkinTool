from copy import copy
from io import BytesIO, BufferedReader, BufferedWriter

BinaryReader = BufferedReader | BytesIO
BinaryWriter = BufferedWriter | BytesIO


def print_hex(msg: str, value: int):
    print(f"{msg}: {value:08X} -> {value}")


class DataInterface:
    def __init__(self):
        self.file: BinaryReader | None = None

    def __len__(self):
        return 0

    def load(self, file: BinaryReader):
        pass

    def save(self, file: BufferedWriter):
        pass

    def set_file(self, file: BinaryReader | BinaryWriter | None):
        self.file = file

    def read_int(self) -> int:
        return int.from_bytes(self.read_bytes(4), "little")

    def write_int(self, value: int):
        return self.write_bytes(value.to_bytes(4, "little"))

    def read_intB(self) -> int:
        return int.from_bytes(self.read_bytes(4), "big")

    def write_intB(self, value: int):
        return self.write_bytes(value.to_bytes(4, "big"))

    def write_char(self, value: int):
        return self.write_bytes(value.to_bytes(1, "little"))

    def read_bytes(self, length: int = 1) -> bytes:
        return self.file.read(length)

    def write_bytes(self, value: bytes):
        return self.file.write(value)

    def seek(self, offset: int):
        self.file.seek(offset)


class KugouSuitSkin(DataInterface):
    def __init__(self, file: BinaryReader | str | None = None):
        super().__init__()
        self.file_num: int = 0  # 4 Bytes Little
        self.file_entries: list[FileEntry] = []
        self.file_contents: list[FileContent] = []
        self.current_length: int = 4
        if isinstance(file, str):
            with open(file, "rb") as f:
                self.load(f)
        elif file is not None:
            self.load(file)

    def load(self, file: BinaryReader):
        try:
            self.set_file(file)
            self.file_num = self.read_int()
            content_offset = 4
            for i in range(self.file_num):
                file_entry = FileEntry()
                file_entry.load(self.file)
                content_offset += len(file_entry)
                self.file_entries.append(file_entry)
            print(content_offset)
            for i, entry in enumerate(self.file_entries):
                self.seek(content_offset + entry.file_start_offset)
                file_content = FileContent(self.read_bytes(entry.file_size))
                self.file_contents.append(file_content)
            self.current_length = sum([len(content) for content in self.file_contents]) + content_offset
        finally:
            self.set_file(None)

    def add_file(self, filename: str, content: bytes):
        entry = FileEntry()
        entry.set_filename(filename)
        entry.file_size = len(content)
        entry.file_start_offset = copy(self.current_length)
        content = FileContent(content)

        self.file_entries.append(entry)
        self.file_contents.append(content)
        self.file_num = len(self.file_entries)
        self.current_length += len(entry) + len(content)

    def save(self, file: BinaryWriter):
        try:
            bytes_io = BytesIO() if isinstance(file, str) else file
            self.set_file(bytes_io)
            self.write_int(self.file_num)
            for entry in self.file_entries:
                entry.save(bytes_io)
            for content in self.file_contents:
                self.write_bytes(content)
            if isinstance(file, str):
                with open(file, "wb") as f:
                    f.write(bytes_io.getbuffer())
        finally:
            self.set_file(None)

    @property
    def files(self) -> list['SkinInnerFile']:
        return [SkinInnerFile(entry, content) for entry, content in zip(self.file_entries, self.file_contents)]


class FileEntry(DataInterface):
    def __init__(self):
        super().__init__()
        self.filename_length = 0  # 4 Bytes Big
        self.filename = ""  # encoding: utf-16-le
        self.file_start_offset = 0  # 4 Bytes Little
        self.file_size = 0  # 4 Bytes Little

    def set_filename(self, filename: str):
        name_bytes = filename.encode("utf-16-le")
        self.filename_length = len(name_bytes)
        self.filename = filename

    def load(self, file: BinaryReader):
        self.set_file(file)
        print("Load A Entry")
        self.read_bytes()
        self.filename_length = self.read_intB()
        self.filename = self.read_bytes(self.filename_length).decode("utf-16-le")
        self.file_start_offset = self.read_int()
        self.file_size = self.read_int()
        print_hex("Filename length", self.filename_length)
        print("Filename:", self.filename)
        print_hex("File start offset", self.file_start_offset)
        print_hex("File size", self.file_size)

    def save(self, file: BinaryWriter):
        self.set_file(file)
        self.write_char(self.filename_length + 0xD)
        self.write_intB(self.filename_length)
        self.write_bytes(self.filename.encode("utf-16-le"))
        self.write_int(self.file_start_offset)
        self.write_int(self.file_size)

    def __len__(self):
        return 1 + 4 + self.filename_length + 4 + 4


class FileContent(bytes):
    pass


class SkinInnerFile:
    def __init__(self, entry: FileEntry, content: FileContent):
        self.filename = entry.filename
        self.file_size = entry.file_size
        self.file_start_offset = entry.file_start_offset
        self.content = content
