# Como contribuir

Obrigado pelo interesse. Este projeto trata de **dado legal**, então a barra
de qualidade é alta: nenhum número entra sem fonte oficial e citação localizável.

## Fluxo

1. Abra uma issue descrevendo o que quer mudar (idealmente com o link da lei).
2. Trabalhe em um branch a partir de `main`.
3. Rode `pytest` e `ruff check .` — a CI faz o mesmo.
4. Abra o PR citando a base legal alterada.

## Regras para dados legais

- Fonte oficial obrigatória, com `consolidated_as_of`.
- Todo parâmetro com `basis: {source, ref}`.
- Valor conferido **no texto oficial**, nunca em resumo de terceiro.
- Ambiguidade vira `notes` ou regra de atenção — nunca valor escolhido em silêncio.
- Mudança de valor precisa de teste de snapshot atualizado no mesmo PR.

Detalhes em [`docs/COMO_ADICIONAR_CIDADE.md`](docs/COMO_ADICIONAR_CIDADE.md) e
[`docs/BASE_LEGAL.md`](docs/BASE_LEGAL.md).

## Código

- Python 3.11+, `ruff` para lint e formatação (linha de 100).
- Tipos nas funções públicas; docstrings em português.
- Nenhuma dependência de serviço externo em runtime.
- O motor (`app/engine/`) não pode deixar de ser determinístico: nada de
  chamada a modelo de linguagem dentro da camada de decisão.

## Como rodar localmente

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -e ".[dev]"
uvicorn app.main:app --reload
```
