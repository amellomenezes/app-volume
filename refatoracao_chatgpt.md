# Discussão de Refatoração do Projeto

## Conversa com ChatGPT

Eu gostaria de refatorar app.py de modo que eu pudesse comparar implementações alternativas de suavização e detecção de outliers. Teríamos que definir uma interface (no sentido de código) que seria implementada por versões concorrentes. Na UI teria um quadro de parametrização para cada implementação. No gráfico cada implementação seria representada por uma linha.


O ChatGPT disse:
Memória salva atualizada
Perfeito. A proposta de refatoração pode ser estruturada com base em injeção de estratégia, criando uma interface comum para os algoritmos de suavização/outliers. Vamos organizar a refatoração em três partes principais:

1. Definir a Interface Padrão para Estratégias
Podemos usar uma classe base abstrata SerieAnalitica:

python
Copiar
Editar
from abc import ABC, abstractmethod

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
O método configurar() define os widgets, e aplicar() retorna:

python
Copiar
Editar
{
    "nome": str,
    "curva": np.ndarray,
    "flags_outliers": np.ndarray (opcional),
    "cor": str (opcional)
}
2. Exemplos de Implementações
LOWESS Manual:

python
Copiar
Editar
class LOWESSManual(SerieAnalitica):
    def configurar(self, st_container):
        self.params["frac"] = st_container.slider("LOWESS frac", 0.1, 1.0, 0.3, step=0.05)

    def aplicar(self, serie):
        x = np.arange(len(serie))
        mask = ~np.isnan(serie)
        curva = lowess(serie[mask], x[mask], frac=self.params["frac"], return_sorted=False)
        curva_interp = np.interp(x, x[mask], curva)
        return {"nome": f"LOWESS Manual ({self.params['frac']:.2f})", "curva": curva_interp}
LOWESS Automático:

python
Copiar
Editar
class LOWESSAuto(SerieAnalitica):
    def configurar(self, st_container):
        self.params["frac_range"] = st_container.slider("Range LOWESS Auto", 0.1, 1.0, (0.3, 0.6), step=0.05)

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
3. UI para Comparação e Exibição
Na interface principal:

python
Copiar
Editar
# Lista de estratégias registradas
estrategias = [LOWESSManual("LOWESS Manual"), LOWESSAuto("LOWESS Auto")]

for estr in estrategias:
    with st.expander(f"Parâmetros - {estr.nome}"):
        estr.configurar(st)

resultados = [estr.aplicar(y) for estr in estrategias]

# Plotar todos no mesmo gráfico
fig = go.Figure()
fig.add_trace(go.Scatter(x=str_index, y=y, name="Original", line=dict(width=2)))

for r in resultados:
    fig.add_trace(go.Scatter(x=str_index, y=r["curva"], name=r["nome"], line=dict(dash="dash")))
Deseja que eu:
Refatore diretamente seu app.py e te envie o código pronto?

Implemente um exemplo funcional mínimo (MVP) só com 2 versões para você expandir depois?

Crie um notebook para testes?

Só escolher!

## Pontos de Refatoração Sugeridos

1. **Definição de Interface para Estratégias Analíticas**
   - Criar uma classe base abstrata (ex: `SerieAnalitica`) para padronizar algoritmos de suavização e detecção de outliers.
   - Interface com métodos `configurar(st_container)` para parametrização via Streamlit e `aplicar(serie)` para aplicar a lógica.

2. **Implementação de Estratégias Concorrentes**
   - Exemplo: `LOWESSManual` e `LOWESSAuto`, cada uma com seus próprios parâmetros e lógica de aplicação.
   - Possibilidade de expandir para outros métodos de suavização ou detecção de outliers.

3. **UI Modular e Comparativa**
   - Cada estratégia tem seu quadro de parametrização (usando `st.expander`).
   - Resultados de todas as estratégias são plotados juntos para comparação visual.
   - Estrutura flexível para adicionar/remover estratégias facilmente.

4. **Padronização do Retorno das Estratégias**
   - Cada implementação retorna um dicionário padronizado com nome, curva, flags de outlier e cor (opcional).

## Próximos Passos

- [ ] Implementar a classe base `SerieAnalitica` e suas subclasses para cada estratégia.
- [ ] Refatorar o código do app para usar a lista de estratégias e gerar a interface de parametrização dinâmica.
- [ ] Garantir que o gráfico principal plote todas as curvas das estratégias selecionadas.
- [ ] (Opcional) Expandir para detecção de outliers e outras técnicas de suavização.
- [ ] Testar a flexibilidade para adicionar novas estratégias no futuro.

## Notas Adicionais

- Essa abordagem facilita a comparação entre diferentes métodos e torna o código mais modular e escalável.
- A interface baseada em classes permite reaproveitamento e fácil manutenção.
- O padrão pode ser expandido para outros tipos de análise além de suavização e outliers. 