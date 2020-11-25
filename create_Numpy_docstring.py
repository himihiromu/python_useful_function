import re


path = input("ドキュメントを自動生成したいファイルのフルパスを入力してください：\n")

def create_class_docstring(first_string, init_string=None):
    space_num = 4
    if first_string[0] == " ":
        for c in first_string:
            if c == " ":
                space_num += 1
            else:
                break

    first_space = " " * space_num
    docstring = first_space + '"""\n' + first_space + "クラスの説明\n\n"

    if init_string:
        docstring += _create_attribute_docstring(init_string, first_space, True)

    docstring += first_space + 'Returns\n' + first_space + "'-------\n" + first_space + "返還に使用する変数 : 変数の方\n" + first_space +\
                 "果物の値段を格納した配列。\n" + first_space + '"""'
    return docstring


def create_def_docstring(string):
    pass


def _create_attribute_docstring(string, first_space, attribute=False):
    self_exclusions = 2
    if string.count("self"):
        self_exclusions+= 1
    def_list = re.split("[ ,()]", string)[self_exclusions:-1]
    attributes = first_space + ("Attributes" if attribute else "Parameters") + "\n" + first_space + "----------\n"
    tmp_attr = ""
    for attr in def_list:
        tmp_attr += first_space + attr.split("=")[0] + ":"
        if attr in ":":
            tmp_attr += attr.split(":")[1] + "\n" + first_space + "変数の説明\n"
        else:
            tmp_attr += " 変数の型\n" + first_space + "変数の説明\n"

    attributes += tmp_attr

    return attributes
