import csv


class CsvToAny:
    """
    CSVファイルを別の形式へ変換する

    Attributes
    ----------
    url : str
        対象のCSVファイルのURL
    delimiter : str
        CSVに変更する際の区切り文字
    """
    def __init__(self, url: str, delimiter=','):
        """
        CSVファイルを別の形式へ変換する

        Parameters
        ----------
        url : str
            対象のCSVファイルのURL
        delimiter : str
            CSVに変更する際の区切り文字
        """
        self.url = url
        self.delimiter = delimiter

    def to_list_convert(self):
        """
        CSVファイルをリストに変形させる

        Returns
        -------
        sheet_col_list : list
            変形後のリスト
        """
        with open(self.url, 'r') as f:
            csv_line = csv.reader(f)
            sheet_col_list = [row for row in csv_line]
        return sheet_col_list

    def to_dict_convert(self, key_num: object = 0, value_num: object = 1) -> object:
        """
        CSVファイルをリストに変形させる

        Parameters
        ----------
        key_num : int
            keyとして格納する列番号
        value_num : str
            valueとして格納する列番号

        Returns
        -------
        csv_dict : list
            変形後のリスト
        """
        list_object = self.to_list_convert()
        csv_dict = {}
        for l in list_object:
            csv_dict[l[key_num]] = l[value_num]
        return csv_dict
