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
            
            # LOWESS/LOESS
            st.subheader("Opções de Suavização LOESS (LOWESS)")
            show_loess = st.checkbox("Exibir curva LOESS (LOWESS)", value=True)
            frac = st.slider("Parâmetro de suavização (frac)", min_value=0.1, max_value=1.0, value=0.3, step=0.05)
            y = serie_data_full.values.astype(float)
            x = np.arange(len(y))
            mask = ~np.isnan(y)
            loess_curve = None
            loess_full_interp = None
            if show_loess and mask.sum() > 1:
                # LOWESS nos pontos existentes
                loess_curve = lowess(y[mask], x[mask], frac=frac, return_sorted=False)
                # Interpolação para todos os meses
                interp_func = interp1d(x[mask], loess_curve, kind='linear', fill_value='extrapolate')
                loess_full_interp = interp_func(x)
            
            # Formatar datas para mês/ano para exibição
            str_index = [d.strftime('%m/%Y') for d in full_index]
            
            # Criar gráfico com Plotly
            fig = go.Figure()
            # Série original
            fig.add_trace(go.Scatter(
                x=str_index,
                y=y,
                mode='lines+markers',
                name='Volume',
                line=dict(width=2),
                marker=dict(size=8)
            ))
            # Curva LOESS interpolada
            if show_loess and loess_full_interp is not None:
                fig.add_trace(go.Scatter(
                    x=str_index,
                    y=loess_full_interp,
                    mode='lines',
                    name='LOESS (interpolado)',
                    line=dict(width=3, color='orange', dash='dash')
                ))
            # Layout
            fig.update_layout(
                title=f"Série Temporal: {selected_series}",
                xaxis_title="Mês/Ano",
                yaxis_title="Volume Ajustado",
                hovermode="x unified",
                showlegend=True,
                height=600,
                xaxis=dict(
                    tickangle=45,
                    tickmode='array',
                    ticktext=str_index,
                    tickvals=str_index
                )
            )
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
                title="Histograma de Volumes"
            )
            fig_dist.update_layout(
                xaxis_title="Volume",
                yaxis_title="Frequência"
            )
            st.plotly_chart(fig_dist, use_container_width=True) 