# Análise de Séries Temporais

Esta aplicação web permite visualizar e analisar séries temporais de volumes de produtos, com foco em:
- Visualização interativa de séries temporais
- Suavização LOESS (LOWESS) para análise de tendências
- Estatísticas básicas e distribuição dos volumes

## Acesso à Aplicação

A aplicação está disponível online através do Streamlit Cloud:
[Link para a aplicação](https://seu-usuario-projeto-ox.streamlit.app)

## Funcionalidades

- **Visualização de Séries**: Gráficos interativos usando Plotly
- **Suavização LOESS**: 
  - Ajuste do parâmetro de suavização
  - Visualização da curva suavizada
- **Estatísticas**:
  - Média, mediana e desvio padrão
  - Histograma de distribuição
- **Dados em Tabela**: Visualização tabular dos dados

## Tecnologias Utilizadas

- Python 3.8+
- Streamlit
- Pandas
- Plotly
- Statsmodels (LOWESS)
- NumPy
- SciPy

## Estrutura do Projeto

```
projeto_ox/
├── app.py              # Código principal da aplicação
├── requirements.txt    # Dependências do projeto
├── volume_ajustado.pkl # Dados da aplicação
└── README.md          # Este arquivo
``` 