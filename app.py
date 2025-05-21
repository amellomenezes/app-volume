import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from statsmodels.nonparametric.smoothers_lowess import lowess
import numpy as np
from scipy.interpolate import interp1d
from cryptography.fernet import Fernet
import base64
import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import tempfile
from plotly.subplots import make_subplots
from estrategias import LOWESSManual, LOWESSAuto, LOWESSManualLog, LOWESSAutoAO, LevelShiftLS

# Configuração da página
st.set_page_config(page_title="Análise de Séries Temporais", layout="wide")

# Título e descrição
st.title("Análise de Séries Temporais")
st.info(
    "🔒 **Segurança dos Dados:**\n"
    "O arquivo criptografado enviado é utilizado apenas durante a sua sessão. "
    "Após o processamento, os dados descriptografados são removidos automaticamente. "
    "Nenhuma informação é armazenada no servidor após o término da sessão.\n\n"
    "**Importante:** Não compartilhe sua senha de descriptografia com terceiros."
)

def generate_key(password: str, salt: bytes) -> bytes:
    """Gera uma chave de criptografia a partir de uma senha e salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def decrypt_data(encrypted_file, password):
    """Descriptografa os dados usando a senha fornecida."""
    try:
        # Ler o arquivo criptografado
        with open(encrypted_file, 'rb') as file:
            salt = file.read(16)  # Primeiros 16 bytes são o salt
            encrypted_data = file.read()
        
        # Gerar chave e descriptografar
        key = generate_key(password, salt)
        f = Fernet(key)
        decrypted_data = f.decrypt(encrypted_data)
        
        # Criar um arquivo temporário com os dados descriptografados
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pkl') as temp_file:
            temp_file.write(decrypted_data)
            temp_path = temp_file.name
        
        # Carregar os dados do arquivo temporário
        df = pd.read_pickle(temp_path)
        
        # Remover o arquivo temporário
        os.unlink(temp_path)
        
        return df
    except Exception as e:
        st.error(f"Erro ao descriptografar os dados: {str(e)}")
        return None

# Upload do arquivo criptografado
uploaded_file = st.file_uploader("Faça upload do arquivo de dados criptografado", type=['encrypted'])

if uploaded_file is not None:
    # Salvar o arquivo temporariamente
    with tempfile.NamedTemporaryFile(delete=False, suffix='.encrypted') as temp_file:
        temp_file.write(uploaded_file.getvalue())
        temp_path = temp_file.name
    
    # Solicitar senha
    password = st.text_input("Digite a senha para descriptografar os dados", type="password")
    
    if password:
        # Descriptografar e carregar dados
        df = decrypt_data(temp_path, password)
        
        # Remover o arquivo temporário
        os.unlink(temp_path)
        
        if df is not None:
            # Converte a coluna Data para string
            df["Data"] = df["Data"].astype(str)
            
            # Criar DataFrame pivotado
            pivot_df = df.pivot_table(
                index=["Engarrafador", "Canal", "SKU_Regra2"],
                columns="Data",
                values="Vol_UC_Adj",
                aggfunc="sum"
            )
            
            # Remover nome do eixo das colunas
            pivot_df.columns.name = "Data"
            
            # Criar lista de séries disponíveis
            series_options = []
            for idx in pivot_df.index:
                engarrafador, canal, sku = idx
                series_options.append({
                    "label": f"{engarrafador} | {canal} | {sku}",
                    "value": idx
                })
            
            # Seleção da série
            selected_series = st.selectbox(
                "Selecione uma série para visualizar:",
                options=[opt["label"] for opt in series_options],
                index=0
            )
            
            # Obter dados da série selecionada
            selected_idx = next(opt["value"] for opt in series_options if opt["label"] == selected_series)
            serie_data = pivot_df.loc[selected_idx]
            
            # Formatar datas para datetime mensal
            serie_data.index = pd.to_datetime(serie_data.index, format='%Y%m%d', errors='coerce')
            # Criar índice mensal contínuo
            full_index = pd.date_range(serie_data.index.min(), serie_data.index.max(), freq='MS')
            serie_data_full = serie_data.reindex(full_index)
            
            # LOWESS Alternativo
            def auto_lowess_alternativo(series, frac_candidates=None):
                if frac_candidates is None:
                    frac_candidates = np.linspace(0.3, 0.6, 7)
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
                return trend, best_frac

            # LOWESS/LOESS
            st.subheader("Opções de Suavização LOESS (LOWESS)")
            loess_mode = st.radio("Modo de LOWESS:", ["Padrão (frac manual)", "Alternativo (frac automático)"])
            show_loess = st.checkbox("Exibir curva LOESS (LOWESS)", value=True)
            frac = st.slider("Parâmetro de suavização (frac)", min_value=0.1, max_value=1.0, value=0.3, step=0.05, disabled=(loess_mode=="Alternativo (frac automático)"))
            y = serie_data_full.values.astype(float)
            x = np.arange(len(y))
            mask = ~np.isnan(y)
            loess_curve_manual = None
            loess_curve_auto = None
            loess_full_interp_manual = None
            loess_full_interp_auto = None
            best_frac = None
            if mask.sum() > 1:
                # LOWESS manual
                loess_curve_manual = lowess(y[mask], x[mask], frac=frac, return_sorted=False)
                interp_func_manual = interp1d(x[mask], loess_curve_manual, kind='linear', fill_value='extrapolate')
                loess_full_interp_manual = interp_func_manual(x)
                # LOWESS automático
                loess_curve_auto, best_frac = auto_lowess_alternativo(y[mask])
                interp_func_auto = interp1d(x[mask], loess_curve_auto, kind='linear', fill_value='extrapolate')
                loess_full_interp_auto = interp_func_auto(x)

            # Formatar datas para mês/ano para exibição
            str_index = [d.strftime('%m/%Y') for d in full_index]
            
            # Opção para escala logarítmica
            st.subheader("Opções de Visualização")
            log_y = st.checkbox("Exibir eixo Y em escala logarítmica", value=False)
            
            # --- Função para detecção de Level Shift (LS) ---
            def detectar_ls(X, K=3.0):
                N = len(X)
                Y = np.diff(X)
                med_Y = np.median(Y)
                mad_Y = np.median(np.abs(Y - med_Y)) or 1.0
                Z = (Y - med_Y) / mad_Y
                Z_full = np.insert(Z, 0, np.nan)
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
                return np.array(TO)

            # Após obter y = serie_data_full.values.astype(float)
            ls_flags = detectar_ls(y)
            
            # Instanciar estratégias
            estrategias = [
                LOWESSManual("LOWESS Manual"),
                LOWESSAuto("LOWESS Auto"),
                LOWESSManualLog("LOWESS Manual Log"),
                LOWESSAutoAO("LOWESS Auto AO"),
                LevelShiftLS("Level Shift LS")
            ]

            # Quadro de seleção de estratégias
            st.subheader("Escolha as implementações que deseja visualizar:")
            nome_estrategias = [estr.nome for estr in estrategias]
            selecionadas = st.multiselect(
                "Implementações disponíveis:",
                options=nome_estrategias,
                default=nome_estrategias,
                key="estrategias_multiselect"
            )

            # Filtrar estratégias selecionadas
            estrategias_filtradas = [estr for estr in estrategias if estr.nome in selecionadas]

            # Parametrização dinâmica apenas das selecionadas
            resultados = []
            for estr in estrategias_filtradas:
                with st.expander(f"Parâmetros - {estr.nome}", expanded=True):
                    estr.configurar(st)
                    resultado = estr.aplicar(y)
                    resultados.append(resultado)
                    # Exibir texto informativo, se existir
                    if "info" in resultado and resultado["info"]:
                        st.info(resultado["info"])

            # Criar gráfico com Plotly
            fig = go.Figure()

            # Série original
            fig.add_trace(go.Scatter(
                x=str_index,
                y=y,
                mode='lines+markers',
                name='Volume',
                line=dict(width=2, color='#1f77b4'),
                marker=dict(size=8, color='#1f77b4'),
                hovertemplate='<b>Data:</b> %{x}<br><b>Volume:</b> %{y:,.2f}<extra></extra>'
            ))

            # Adicionar curvas das estratégias selecionadas
            cores = ['orange', 'purple', 'green', 'red', 'cyan']
            for i, r in enumerate(resultados):
                fig.add_trace(go.Scatter(
                    x=str_index,
                    y=r["curva"],
                    mode='lines',
                    name=r["nome"],
                    line=dict(width=3, dash='dash', color=cores[i % len(cores)]),
                    hovertemplate=f'<b>Data:</b> %{{x}}<br><b>{r["nome"]}:</b> %{{y:,.2f}}<extra></extra>'
                ))
                # Destacar AO
                if "ao_flags" in r:
                    ao_idx = np.where(r["ao_flags"])[0]
                    if len(ao_idx) > 0:
                        fig.add_trace(go.Scatter(
                            x=[str_index[j] for j in ao_idx],
                            y=[r["curva"][j] for j in ao_idx],
                            mode='markers',
                            name=f"AO - {r['nome']}",
                            marker=dict(size=10, color='black', symbol='circle-open'),
                            showlegend=True,
                            hovertemplate=f'<b>Data:</b> %{{x}}<br><b>AO:</b> %{{y:,.2f}}<extra></extra>'
                        ))
                # Destacar LS
                if "ls_flags" in r:
                    ls_idx = np.where(r["ls_flags"])[0]
                    if len(ls_idx) > 0:
                        fig.add_trace(go.Scatter(
                            x=[str_index[j] for j in ls_idx],
                            y=[r["curva"][j] for j in ls_idx],
                            mode='markers',
                            name=f"LS - {r['nome']}",
                            marker=dict(size=12, color='red', symbol='diamond'),
                            showlegend=True,
                            hovertemplate=f'<b>Data:</b> %{{x}}<br><b>LS:</b> %{{y:,.2f}}<extra></extra>'
                        ))

            # Pontos LS
            ls_indices = np.where(ls_flags == 'LS')[0]
            if len(ls_indices) > 0:
                fig.add_trace(go.Scatter(
                    x=[str_index[i] for i in ls_indices],
                    y=[y[i] for i in ls_indices],
                    mode='markers',
                    name='Level Shift (LS)',
                    marker=dict(size=12, color='red', symbol='diamond', line=dict(width=2, color='white')),
                    hovertemplate='<b>Data:</b> %{x}<br><b>Volume:</b> %{y:,.2f}<br><b>Tipo:</b> Level Shift<extra></extra>'
                ))

            # Layout do gráfico
            fig.update_layout(
                title=dict(
                    text=f"Série Temporal: {selected_series}",
                    x=0.5,
                    y=0.95,
                    xanchor='center',
                    yanchor='top'
                ),
                xaxis_title="Mês/Ano",
                yaxis_title="Volume Ajustado",
                hovermode="x unified",
                showlegend=True,
                height=600,
                template="plotly_dark",
                xaxis=dict(
                    tickangle=45,
                    tickmode='array',
                    ticktext=str_index,
                    tickvals=str_index,
                    gridcolor='rgba(128, 128, 128, 0.2)'
                ),
                yaxis=dict(
                    type='linear',
                    gridcolor='rgba(128, 128, 128, 0.2)'
                ),
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=0.01,
                    bgcolor='rgba(0, 0, 0, 0.5)'
                ),
                margin=dict(l=50, r=50, t=80, b=50),
                plot_bgcolor='rgba(0, 0, 0, 0)',
                paper_bgcolor='rgba(0, 0, 0, 0)'
            )

            # Adicionar botões de alternância de escala
            fig.update_layout(
                updatemenus=[
                    dict(
                        type="buttons",
                        direction="right",
                        x=0.1,
                        y=1.1,
                        showactive=True,
                        buttons=list([
                            dict(
                                args=[{"yaxis.type": "linear"}],
                                label="Linear",
                                method="relayout"
                            ),
                            dict(
                                args=[{"yaxis.type": "log"}],
                                label="Log",
                                method="relayout"
                            )
                        ])
                    )
                ]
            )

            # Exibir o gráfico
            st.plotly_chart(fig, use_container_width=True)

            # Exibir dados em formato de tabela
            st.subheader("Dados da Série")
            df_tabela = pd.DataFrame({"Mês/Ano": str_index, "Volume": y})
            st.dataframe(df_tabela)

            # Estatísticas básicas
            st.subheader("Estatísticas Básicas")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Média", f"{np.nanmean(y):,.2f}")
            with col2:
                st.metric("Mediana", f"{np.nanmedian(y):,.2f}")
            with col3:
                st.metric("Desvio Padrão", f"{np.nanstd(y):,.2f}")

            # Gráfico de distribuição
            st.subheader("Distribuição dos Volumes")
            fig_dist = px.histogram(
                x=y[~np.isnan(y)],
                nbins=30,
                title="Histograma de Volumes",
                template="plotly_dark"
            )
            fig_dist.update_layout(
                xaxis_title="Volume",
                yaxis_title="Frequência",
                plot_bgcolor='rgba(0, 0, 0, 0)',
                paper_bgcolor='rgba(0, 0, 0, 0)'
            )
            st.plotly_chart(fig_dist, use_container_width=True) 