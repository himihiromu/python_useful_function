import xlrd
import csv


class XlsxToAny:
    """
    エクセルファイルを別の形式へ変換する

    Attributes
    ----------
    url : str
        対象のエクセルファイルのURL
    delimiter : str
        CSVに変更する際の区切り文字
    workBook
        エクセルファイルのインスタンス
    """
    def __init__(self, url: str, delimiter=','):
        """
        Parameters
        ----------
        url : str
        対象のエクセルファイルのURL
        delimiter : str
            CSVに変更する際の区切り文字
        """
        self.url = url
        self.workBook = xlrd.open_workbook(url)
        self.delimiter = delimiter

    def to_list_convert(self, sheet_number: int, start_row=0, end_row=None, start_col=0, end_col=None) -> list:
        """
        エクセルファイルをリストに変形させる

        Parameters
        ----------
        sheet_number : int
            リストへ変形させるシートの番号
        start_row : int
            何行目から変形させるかを決める
        end_row : int
            何行目まで変形させるかを決める
        start_col : int
            何列目から変形させるかを決める
        end_col : int
            何列目まで変形させるかを決める

        Returns
        -------
        sheet_col_list : list
            変形後のリスト
        """
        sheet = self.sheet_by_index(sheet_number)
        if end_row is None:
            end_row = sheet.nrows

        sheet_col_list = []
        for i in range(start_row, end_row):
            sheet_col_list.append(sheet.row_values(i, start_col, end_col + 1))

        return sheet_col_list

    def to_csv_convert(self, csv_url: str, sheet_number: int, start_row=0, end_row=None, start_col=0, end_col=None):
        """
        エクセルファイルをリストに変形させる

        Parameters
        ----------
        csv_url : str
            CSVファイルを保存するURL
        sheet_number : int
            リストへ変形させるシートの番号
        start_row : int
            何行目から変形させるかを決める
        end_row : int
            何行目まで変形させるかを決める
        start_col : int
            何列目から変形させるかを決める
        end_col : int
            何列目まで変形させるかを決める

        """
        with open(csv_url, 'w') as f:
            writer = csv.writer(f, delimiter=self.delimiter)
            writer.writerows(self.to_list_convert(sheet_number, start_row, end_row, start_col, end_col))
