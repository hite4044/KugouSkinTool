import json
from dataclasses import dataclass, field
from enum import Enum

import wx


def create_color_icon(color: tuple[int, int, int], size=(32, 32)):
    print(color)
    color = wx.Colour(color)
    # 创建一个位图
    bitmap = wx.Bitmap(size[0], size[1])

    # 使用 MemoryDC 绘制颜色
    dc = wx.MemoryDC(bitmap)
    #    dc.FloodFill(0, 0, color, wx.SOLID)
    dc.SetBackground(wx.Brush(color))
    dc.Clear()
    dc.SelectObject(wx.NullBitmap)  # 确保释放 bitmap 的 DC

    # 将 bitmap 转换为 icon
    icon = wx.Icon(bitmap)
    return icon


class ThemeDataType(Enum):
    NORMAL = "normal"
    ALPHA = "alpha"
    MIX = "Mix"
    REDIRECT = "redirect"


@dataclass
class ThemeData:
    id: str
    color: str
    type: ThemeDataType

    alpha: int = -1

    mix_alpha: int = -1
    mix_color: str = ""
    parent: 'ThemeData' = None
    children: list['ThemeData'] = field(default_factory=list)

    def __str__(self) -> str:
        color = Color.from_hex(self.color) if self.color.startswith("#") else self.color
        if self.type == ThemeDataType.NORMAL:
            return f"{color}"
        elif self.type == ThemeDataType.ALPHA:
            return f"{color} +{self.alpha} Alpha"
        elif self.type == ThemeDataType.MIX:
            return f"{color} Mix:{self.mix_color} {self.mix_alpha}"
        elif self.type == ThemeDataType.REDIRECT:
            return f"<-{self.color}"
        return ""


@dataclass
class Color:
    r: int
    g: int
    b: int
    alpha: int = 255

    @classmethod
    def from_hex(cls, hex_str: str, alpha: int = 255):
        hex_str = hex_str.lstrip("#")
        r, g, b = [int(hex_str[i:i + 2], 16) for i in range(0, 6, 2)]
        return Color(r, g, b, alpha)

    def __add__(self, other: 'Color') -> 'Color':
        # 使用颜色覆盖算法计算两个颜色覆盖后的颜色
        a_per, b_per = self.alpha / (self.alpha + other.alpha), other.alpha / (self.alpha + other.alpha)
        r = clr_clamp(self.r * a_per + other.r * b_per)
        g = clr_clamp(self.g * a_per + other.g * b_per)
        b = clr_clamp(self.b * a_per + other.b * b_per)
        alpha = clr_clamp(self.alpha + other.alpha)
        return Color(r, g, b, alpha)

    def __str__(self) -> str:
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}-{self.alpha}"


def clr_clamp(value: float):
    return max(0, min(int(value), 255))


class ThemeDataParser:
    def __init__(self):
        self.data_map = None

    def set_theme_data_map(self, data_map: dict[str, ThemeData]):
        self.data_map = data_map

    def translate_color(self, data: ThemeData) -> Color:
        data_map: dict[str, ThemeData] = self.data_map
        if data.type == ThemeDataType.NORMAL:
            return Color.from_hex(data.color)
        color = self.translate_color(data_map[data.color])
        if data.type == ThemeDataType.ALPHA:
            color.alpha = clr_clamp(data.alpha / 255 * color.alpha)
        elif data.type == ThemeDataType.MIX:
            color = self.translate_color(data_map[data.color])
            mix_color = Color.from_hex(data.mix_color)
            mix_color.alpha = data.mix_alpha
            color = color + mix_color
        elif data.type == ThemeDataType.REDIRECT:
            return self.translate_color(data_map[data.color])
        return color

    def get_parent_data(self, data: ThemeData) -> ThemeData | None:
        data_map: dict[str, ThemeData] = self.data_map
        return data_map.get(data.color)


class StructTree(wx.TreeCtrl):
    def __init__(self, parent: wx.Window):
        super().__init__(parent, style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT | wx.TR_FULL_ROW_HIGHLIGHT)
        self.root_data_tree: list[ThemeData] = []
        self.parser = ThemeDataParser()
        self.image_list = wx.ImageList(16, 16)
        self.root = self.AddRoot("Theme.json")
        self.AssignImageList(self.image_list)

    def build_gui_tree(self):
        # 构建树结构
        def build_tree(parent_item: wx.TreeItemId, data: ThemeData):
            for child in data.children:
                child_color = self.parser.translate_color(child)
                color = Color(255, 255, 255, 128) + child_color
                print(child_color, color)
                icon = create_color_icon((color.r, color.g, color.b), (16, 16))
                icon_index = self.image_list.Add(icon)
                child_item = self.AppendItem(parent_item, f"{child.id} {child}", icon_index)
                if child.children:
                    build_tree(child_item, child)

        # 从根节点开始构建树
        self.image_list.RemoveAll()
        self.DeleteAllItems()
        root_data = ThemeData("%ROOT%", "", ThemeDataType.NORMAL)
        root_data.children = self.root_data_tree
        build_tree(self.root, root_data)

    def load_theme(self, json_path: str):
        json_data: dict[str, dict[str, int | str]] = {}
        with open(json_path) as f:
            json_data = json.loads(f.read())
        data_map: dict[str, ThemeData] = {}
        for data_id, value in json_data.items():
            data_type = ThemeDataType(value["type"])
            if data_type == ThemeDataType.ALPHA:
                data = ThemeData(data_id, value["color"], data_type, alpha=value["alpha"])
            elif data_type == ThemeDataType.MIX:
                data = ThemeData(data_id, value["color"], data_type, mix_alpha=value["mix_alpha"],
                                 mix_color=value["mix_color"])
            else:
                data = ThemeData(data_id, value["color"], data_type)
            data_map[data_id] = data
        self.root_data_tree.clear()
        for data in data_map.values():
            if data.type == ThemeDataType.NORMAL:
                self.root_data_tree.append(data)
                for child in data_map.values():
                    if child.color == data.id:
                        data.children.append(child)
        self.parser.set_theme_data_map(data_map)
        self.build_gui_tree()
        return data_map


class ThemeStructShower(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, title="Theme.json Struct Shower", size=(500, 800))
        self.tree = StructTree(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.EXPAND)
        self.SetSizer(sizer)


if __name__ == "__main__":
    app = wx.App()
    frame = ThemeStructShower()

    frame.tree.load_theme(
        r"C:\Users\69566\AppData\Roaming\KuGou8\Skin10\Locale\9b021217810ab25b9e7b6abe07f4c742\Theme.json")
    frame.Show()
    app.MainLoop()
