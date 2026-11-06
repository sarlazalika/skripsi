import sqlite3
import pandas as pd
from analysis.moving_average import calculate_moving_average

conn = sqlite3.connect('database.db')
df = pd.read_sql_query('SELECT tanggal, produk, jumlah FROM cleaned_transaksi', conn)

global_min = pd.to_datetime(df['tanggal']).min().strftime('%Y-%m-%d')
global_max = pd.to_datetime(df['tanggal']).max().strftime('%Y-%m-%d')
print(f'Periode Data: {global_min} s/d {global_max}')

with open('app.py', 'r', encoding='utf-8') as f:
    for line in f:
        if 'request.args.get(\'window\'' in line:
            print('Default window di app.py:', line.strip())

res_12 = calculate_moving_average(df, window=12)
print(f'Window 12 - MAE: {res_12["validation"]["mae"]}, MAPE: {res_12["validation"]["mape"]}%, N Data: {res_12["validation"]["n_data"]}')

res_3 = calculate_moving_average(df, window=3)
print(f'Window 3 - MAE: {res_3["validation"]["mae"]}, MAPE: {res_3["validation"]["mape"]}%, N Data: {res_3["validation"]["n_data"]}')
