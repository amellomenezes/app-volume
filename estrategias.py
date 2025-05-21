from abc import ABC, abstractmethod
import numpy as np
from statsmodels.nonparametric.smoothers_lowess import lowess

class SerieAnalitica(ABC):
    def __init__(self, nome):
        self.nome = nome
        self.params = {}

    @abstractmethod
    def configurar(self, st_container):
        """Define os parâmetros ajustáveis via Streamlit"""
        pass

    @abstractmethod
    def aplicar(self, serie: np.ndarray) -> dict:
        """Aplica a lógica à série e retorna resultados"""
        pass

class LOWESSManualLog(SerieAnalitica):
    def configurar(self, st_container):
        self.params["frac"] = st_container.slider("LOWESS frac (log)", 0.1, 1.0, 0.3, step=0.05, key=f"{self.nome}_frac_log_{id(self)}")

    def aplicar(self, serie):
        x = np.arange(len(serie))
        mask = ~np.isnan(serie)
        # Aplicar log (usando log1p para lidar com zeros)
        serie_log = np.log1p(serie[mask])
        # Suavização LOWESS no domínio log
        curva_log = lowess(serie_log, x[mask], frac=self.params["frac"], return_sorted=False)
        # Interpolação para todos os pontos
        curva_log_interp = np.interp(x, x[mask], curva_log)
        # Voltar ao nível original
        curva_nivel = np.expm1(curva_log_interp)
        return {"nome": f"LOWESS Manual Log ({self.params['frac']:.2f})", "curva": curva_nivel}

class LOWESSManual(SerieAnalitica):
    def configurar(self, st_container):
        self.params["frac"] = st_container.slider("LOWESS frac", 0.1, 1.0, 0.3, step=0.05, key=f"{self.nome}_frac_{id(self)}")

    def aplicar(self, serie):
        x = np.arange(len(serie))
        mask = ~np.isnan(serie)
        curva = lowess(serie[mask], x[mask], frac=self.params["frac"], return_sorted=False)
        curva_interp = np.interp(x, x[mask], curva)
        return {"nome": f"LOWESS Manual ({self.params['frac']:.2f})", "curva": curva_interp}

class LOWESSAuto(SerieAnalitica):
    def configurar(self, st_container):
        self.params["frac_range"] = st_container.slider("Range LOWESS Auto", 0.1, 1.0, (0.3, 0.6), step=0.05, key=f"{self.nome}_frac_range_{id(self)}")

    def aplicar(self, serie):
        x = np.arange(len(serie))
        mask = ~np.isnan(serie)
        fracs = np.linspace(*self.params["frac_range"], 7)
        scores, trends = [], []
        for f in fracs:
            curva = lowess(serie[mask], x[mask], frac=f, return_sorted=False)
            mad = np.median(np.abs(serie[mask] - curva)) or 1e-6
            scores.append(mad)
            trends.append(curva)
        i = np.argmin(scores)
        curva = np.interp(x, x[mask], trends[i])
        return {"nome": f"LOWESS Auto ({fracs[i]:.2f})", "curva": curva}

class LOWESSAutoAO(SerieAnalitica):
    def configurar(self, st_container):
        self.params["frac_range"] = st_container.slider("Range LOWESS Auto", 0.1, 1.0, (0.3, 0.6), step=0.05, key=f"{self.nome}_frac_range_{id(self)}")
        self.params["use_percentual"] = st_container.checkbox("Usar MAD percentual", value=False, key=f"{self.nome}_use_percentual_{id(self)}")

    def aplicar(self, serie):
        x = np.arange(len(serie))
        mask = ~np.isnan(serie)
        y = serie[mask]
        x_masked = x[mask]
        fracs = np.linspace(*self.params["frac_range"], 7)
        scores, trends, mad_list = [], [], []
        for f in fracs:
            curva = lowess(y, x_masked, frac=f, return_sorted=False)
            resid = y - curva
            if self.params["use_percentual"]:
                mad = np.median(np.abs(resid) / (np.abs(curva) + 1e-6))
            else:
                mad = np.median(np.abs(resid))
            scores.append(mad)
            trends.append(curva)
            mad_list.append(mad)
        i = np.argmin(scores)
        best_frac = fracs[i]
        curva = np.interp(x, x_masked, trends[i])
        resid = y - trends[i]
        if self.params["use_percentual"]:
            final_mad = np.median(np.abs(resid) / (np.abs(trends[i]) + 1e-6))
            ao_flags = np.abs(resid) / (np.abs(trends[i]) + 1e-6) > 3 * final_mad
        else:
            final_mad = np.median(np.abs(resid))
            ao_flags = np.abs(resid) > 3 * final_mad

        # Relatório
        info = (
            "Resumo da detecção de outliers (AO) via LOWESS:\n"
            f"- Suavização LOWESS automática (frac): {best_frac:.3f}\n"
            f"- {'MAD percentual' if self.params['use_percentual'] else 'MAD absoluto'} dos resíduos: {final_mad:.4f}\n"
            f"- Total de outliers identificados (AO): {int(np.sum(ao_flags))}"
        )

        return {
            "nome": f"LOWESS Auto AO ({best_frac:.2f})",
            "curva": curva,
            "info": info,
            "ao_flags": ao_flags
        }

class LevelShiftLS(SerieAnalitica):
    def configurar(self, st_container):
        self.params["K"] = st_container.slider("K (limiar para Z)", 1.0, 5.0, 3.0, step=0.1, key=f"{self.nome}_K_{id(self)}")

    def aplicar(self, serie):
        X = serie.astype(float)
        N = len(X)
        Y = np.diff(X)
        med_Y = np.median(Y)
        mad_Y = np.median(np.abs(Y - med_Y)) or 1.0
        Z = (Y - med_Y) / mad_Y
        Z_full = np.insert(Z, 0, np.nan)
        K = self.params["K"]
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

        # Texto de resumo
        info = (
            "Resumo da detecção de outliers:\n"
            f"- N = {N}\n"
            f"- Mediana global da série: {mediana_global:.4f}\n"
            f"- Total de AOs: {TO.count('AO')}\n"
            f"- Total de pontos LS: {TO.count('LS')}\n"
            f"- Segmentos LS distintos: {len(set(s for s, t in zip(SO, TO) if t == 'LS'))}\n"
            f"- Referência usada para correção: {'mediana global' if usar_global else 'mediana não-LS'}"
        )

        return {
            "nome": f"Level Shift LS (K={K:.2f})",
            "curva": np.array(corrigida),
            "info": info,
            "ls_flags": np.array([t == 'LS' for t in TO]),
            "ao_flags": np.array([t == 'AO' for t in TO])
        }

  
  