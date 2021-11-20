from PyQt5 import QtWidgets as qtw
import pandas as pd
import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'


def pandas_to_table_widget(df: pd.DataFrame, table: qtw.QTableWidget):
    table.clear()
    n_rows, n_columns = df.shape
    if n_columns > 0:
        table.setColumnCount(n_columns)
        table.setRowCount(n_rows)
        table.setHorizontalHeaderLabels(df.columns)
        # table.verticalHeader().setSectionResizeMode(qtw.QHeaderView.Stretch)
        # data insertion
        for i in range(table.rowCount()):
            for j in range(table.columnCount()):
                table.setItem(i, j, qtw.QTableWidgetItem(str(df.iloc[i, j])))
        table.horizontalHeader().setSectionResizeMode(qtw.QHeaderView.ResizeToContents)
        table.setSelectionBehavior(qtw.QAbstractItemView.SelectRows)


def unique(list1):
    unique_list = []
    for x in list1:
        if x not in unique_list:
            unique_list.append(x)
    return unique_list

