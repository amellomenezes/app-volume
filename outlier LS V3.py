## detecta ouliers LS
##
import pandas as pd
import numpy as np
from google.colab import files
from io import BytesIO

# Upload do arquivo
print("Faça upload do arquivo Excel com as colunas 'ID' e 'Dep'.")
uploaded = files.upload()
filename = next(iter(uploaded))
df = pd.read_excel(BytesIO(uploaded[filename]))

# Série
X = df['Dep'].astype(float).values
N = len(X)
Y = np.diff(X)
med_Y = np.median(Y)
mad_Y = np.median(np.abs(Y - med_Y)) or 1.0
Z = (Y - med_Y) / mad_Y
Z_full = np.insert(Z, 0, np.nan)
K = 3.0
O = np.abs(Z) >= K

TO = [None] * N
SO = [0] * N
serial = 0
t = 1

while t < N:
    if not O[t - 1]:
        t += 1
        continue

    s = t
    while t < N and O[t - 1]:
        t += 1
    e = t - 1
    segment_len = e - s + 1
    serial += 1

    if segment_len == 1:
        u = s
        if u < N and u > 0:
            prev_val = X[u - 1]
            curr_val = X[u]
            if curr_val > prev_val and np.all(X[u + 1:] >= curr_val):
                for i in range(u, N):
                    TO[i] = 'LS'
                    SO[i] = serial
                break
        TO[u] = 'AO'
        SO[u] = serial
        continue

    signs = np.sign(Z[s - 1:e])
    unique_signs = np.unique(signs)

    if len(unique_signs) == 1:
        for i in range(s, e + 1):
            TO[i] = 'AO'
            SO[i] = serial
            serial += 1
    else:
        for i in range(s, e + 1):
            TO[i] = 'LS'
            SO[i] = serial

# Série corrigida
mediana_global = np.median(X)
nao_ls_vals = [X[i] for i in range(N) if TO[i] != 'LS']
usar_global = len(nao_ls_vals) < 5 or sum(t == 'LS' for t in TO) / N >= 0.7
referencia_base = mediana_global if usar_global else np.median(nao_ls_vals)

corrigida = []
for i in range(N):
    if TO[i] != 'LS':
        corrigida.append(X[i])
    else:
        serial_ls = SO[i]
        ls_vals = [X[j] for j in range(N) if TO[j] == 'LS' and SO[j] == serial_ls]
        med_ls = np.median(ls_vals)
        corrigida.append(X[i] - med_ls + referencia_base)

# Criar saída com colunas específicas
df_result = pd.DataFrame({
    'ID': df['ID'],
    'Dep': X,
    'Trend': [np.nan] * N,
    'Z': Z_full,
    'OutlierType': TO,
    'Serial': SO,
    'corrigida LS': corrigida
})

# Resumo
print("Resumo da detecção de outliers:")
print(f"- N = {N}")
print(f"- Mediana global da série: {mediana_global:.4f}")
print(f"- Total de AOs: {TO.count('AO')}")
print(f"- Total de pontos LS: {TO.count('LS')}")
print(f"- Segmentos LS distintos: {len(set(s for s, t in zip(SO, TO) if t == 'LS'))}")
print(f"- Referência usada para correção: {'mediana global' if usar_global else 'mediana não-LS'}")

# Exportar planilha
output_name = "outliers_ls_result_final.xlsx"
df_result.to_excel(output_name, index=False)
files.download(output_name)
