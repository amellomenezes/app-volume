## Identificar outliers AO via LOWESS
##
import pandas as pd
import numpy as np
from statistics import median
from statsmodels.nonparametric.smoothers_lowess import lowess
from google.colab import files

# --- Carregar dados ---
print("Faça upload do arquivo Excel com coluna 'ID' e 'Dep'.")
uploaded = files.upload()
filename = next(iter(uploaded))

df = pd.read_excel(filename)
required = {'ID', 'Dep'}
if not required.issubset(df.columns):
    raise ValueError(f"Colunas faltando: {required - set(df.columns)}")

# Extrair séries e inverter
df = df.reset_index(drop=True)
df_original = df.copy()
ids = df['ID'].tolist()
X = df['Dep'].astype(float).values

# Inverter a série para priorizar borda esquerda
X_rev = X[::-1]

# --- Seleção automática de suavização com LOWESS ---
def auto_lowess_ao(series, frac_candidates=None, K=3, use_percentual=True):
    if frac_candidates is None:
        frac_candidates = np.linspace(0.3, 0.6, 7)  # intervalo mais restrito para evitar overfitting

    scores = []
    trends = []

    for frac in frac_candidates:
        smoothed = lowess(series, np.arange(len(series)), frac=frac, it=3, return_sorted=False)
        resid = series - smoothed
        mad = np.median(np.abs(resid - np.median(resid))) or 1e-6
        score = mad
        scores.append(score)
        trends.append(smoothed)

    best_index = int(np.argmin(scores))
    best_frac = frac_candidates[best_index]
    trend = trends[best_index]

    if use_percentual:
        resid = (series - trend) / trend
    else:
        resid = series - trend

    med_resid = np.median(resid)
    mad_resid = np.median(np.abs(resid - med_resid)) or 1e-6
    Z = (resid - med_resid) / mad_resid
    ao_flags = np.abs(Z) >= K

    return trend, Z, ao_flags, best_frac, mad_resid

# --- Parâmetros configuráveis ---
K = 3
USE_PERCENTUAL = False  # Altere para False para usar resíduos simples

# --- Aplicar LOWESS e detectar AOs ---
trend_rev, Z_rev, ao_flags_rev, best_frac, final_mad = auto_lowess_ao(X_rev, K=K, use_percentual=USE_PERCENTUAL)

# Reverter de volta para ordem original
trend = trend_rev[::-1]
Z = Z_rev[::-1]
ao_flags = ao_flags_rev[::-1]

# --- Construir colunas de saída ---
TO = ["AO" if flag else None for flag in ao_flags]
SO = [i+1 if flag else 0 for i, flag in enumerate(ao_flags)]
Z_series = Z.tolist()
trend_series = trend.tolist()

# Série corrigida
corrected_series = [x if not flag else t for x, t, flag in zip(X, trend, ao_flags)]

# --- Relatório ---
print("Resumo da detecção de outliers (AO) via LOWESS:")
print(f"- Suavização LOWESS automática (frac): {best_frac:.3f}")
print(f"- {'MAD percentual' if USE_PERCENTUAL else 'MAD absoluto'} dos resíduos: {final_mad:.4f}")
print(f"- Total de outliers identificados (AO): {sum(ao_flags)}")

# --- Exportar resultados ---
df_original['Trend'] = trend_series
df_original['Z'] = Z_series
df_original['OutlierType'] = TO
df_original['Serial'] = SO
df_original['Corrected'] = corrected_series

out_filename = 'outliers_lowess_report.xlsx'
df_original.to_excel(out_filename, index=False)
print(f"Planilha de resultados exportada como {out_filename}")
files.download(out_filename)
