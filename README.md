# LegisUrb

**Assistente de parâmetros urbanísticos conforme a legislação municipal.**

O engenheiro informa os dados do terreno e do projeto; o sistema devolve os limites
da zona (CA, TO, recuos, gabarito, permeabilidade), verifica o projeto contra esses
limites e **mostra o artigo de lei que fundamenta cada número**.

Não é um chatbot: é um motor determinístico sobre uma base legal estruturada.
O resultado é reproduzível, auditável e citável — o que a área técnica precisa
para uso profissional.

---

## O problema

Hoje o engenheiro que projeta em um município:

1. Baixa o "Plano Diretor" / "LUOS" / "Código de Obras" em PDF (às vezes 300 páginas).
2. Acha a zona do terreno em um mapa georreferenciado.
3. Encontra o quadro de parâmetros (às vezes em anexo, às vezes em lei municipal).
4. Interpreta exceções, notas de rodapé, dispensas e regras condicionais.
5. Descobre no_analysis da análise de viabilidade que errou o recuo lateral.

O passo 4 é onde estão a maior parte dos erros — e é exatamente o que um sistema
estruturado resolve: cada regra vira uma condição declarativa com a citação ao lado.

## O que o sistema faz

| Entrada | Saída |
|---|---|
| Município, zona (ou respostas do questionário) | Tabela de limites da zona com base legal por linha |
| Área do lote, projeção, área construída, pavimentos, recuos propostos | Verificação item a item: conforme / não conforme / dado pendente |
| Testada, passeio público, vizinho encostado, terreno geotécnico | Regras condicionais disparadas (art. 66, 67, 69, 72, 76, 81, 91…) |
| — | Cálculo dos valores máximos admissíveis (área construída máxima, área de projeção máxima, área permeável mínima) |

Cada item verificado mostra: limite, valor do projeto, situação, **base legal** e
link para o documento oficial.

## Estado atual

- **São Paulo (SP)** — Lei nº 16.402/2016 (LUOS), Anexo 3 / Quadro 3, texto compilado
  com as Leis nº 18.081/2024 e nº 18.177/2024. 39 zonas cadastradas, 18 regras condicionais.
- **Cidade Exemplo** — município fictício, usado para demonstração e testes automatizados
  (exercita resolução de zona por questionário, por geolocalização e a verificação de permeabilidade).

> Nenhum número entra no sistema sem uma fonte oficial ao lado. Ver
> [`docs/BASE_LEGAL.md`](docs/BASE_LEGAL.md) para a política de origem e versionamento.

## Como rodar

Requisitos: Python 3.11+.

```bash
git clone <url-do-repo>
cd legis-urbana
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Abra <http://127.0.0.1:8000>. A documentação interativa da API fica em `/docs`.

Com Docker:

```bash
docker compose up --build
```

Variáveis de ambiente (`cp .env.example .env`):

| Variável | Padrão | Descrição |
|---|---|---|
| `LEGIS_DB_URL` | `sqlite:///data/legis.db` | Conexão do banco (SQLite ou Postgres) |
| `LEGIS_DATA_DIR` | `./data` | Pasta com as cidades em YAML |
| `LEGIS_SEED_ON_STARTUP` | `1` | Recarrega as cidades do YAML ao iniciar |

## Testes e lint

```bash
pytest          # 35 testes: motor, dados legais e API
ruff check .    # lint
ruff format .   # formatação
```

Os testes incluem **snapshots do Quadro 3** (CA/TO/gabarito/recuos de ZM, ZC, ZPR,
ZPI-2, ZEPAM, AC-2…), a alternância de TO por área do lote, o CA reduzido das ZEIS
(notas f/g/h), as dispensas do art. 66 e as exigências de QA dos arts. 76/81.
Se a lei mudar, esses testes acusam — de propósito.

## Estrutura

```
app/
  main.py              API FastAPI
  models.py            ORM (cidades, zonas, parâmetros, regras, fontes)
  engine/
    facts.py           respostas -> fatos do projeto (com derivações)
    conditions.py      avaliador de condições declarativas
    resolver.py        resolução da zona (manual / questionário / geo)
    checks.py          verificações determinísticas (ratio_max, gte, lte, ...)
    analyze.py         orquestrador: resolve, aplica regras, verifica
  seed/loader.py       YAML -> banco
  static/              interface (HTML/CSS/JS puro, sem build)
data/cities/<municipio>/
  city.yaml            zonas, parâmetros, regras, fontes, questionário
  zones.geojson        (opcional) polígonos para resolução geográfica
docs/                  arquitetura, base legal, como adicionar cidade, roadmap
tests/                 pytest
```

## Como adicionar uma cidade

Resumo (detalhes em [`docs/COMO_ADICIONAR_CIDADE.md`](docs/COMO_ADICIONAR_CIDADE.md)):

1. Crie `data/cities/<slug>/city.yaml`.
2. Declare as **fontes** (lei, decreto, anexo) com URL oficial e data de consolidação.
3. Descreva as **zonas** e seus **parâmetros**, cada um com `basis: {source, ref}`.
4. Declare as **regras condicionais** (`when` + `effects`).
5. Escreva o **questionário** que o engenheiro vai preencher.
6. Rode `pytest` — os testes de integridade exigem base legal em todo parâmetro.

Nenhuma alteração de código é necessária: o motor é genérico.

## Limitações (leia antes de usar em projeto)

- **Conformidade legal ≠ aprovação municipal.** O resultado é apoio técnico; não substitui
  ART/RRT, parecer, análise do órgão nem a responsabilidade profissional.
- **A zona precisa ser confirmada.** Sem o mapa oficial georreferenciado, em São Paulo
  a zona é informada manualmente pelo engenheiro (o app aponta o link do GeoSampa).
- **Interpretação é humana.** Notas de rodapé do Quadro 3 e casos concretos do art. 66, II
  dependem de análise do órgão; o sistema sinaliza ("atenção") em vez de decidir.
- **Vigência.** Os dados trazem a data de consolidação e a data de consulta da fonte;
  antes de protocolar, confira a redação vigente.
- A Quota Ambiental (QA) de São Paulo exige a planilha oficial do Executivo —
  o sistema indica a exigência e a base (arts. 74 a 76, Quadros 3A/3B), mas não calcula
  a pontuação.

## Roadmap

| Nível | Entrega |
|---|---|
| **N1** ✅ | Consulta com citação legal (este repositório) |
| **N2** | Relatório de não conformidades exportável (PDF/DOCX) e checklist por zona |
| **N3** | Extração de parâmetros do projeto (planta/DWG) e conferência automática |
| **N4** | Validação de geometria/BIM contra os parâmetros (Revit/Dynamo, IFC) |
| **N5** | ⚠️ Protocolo automático — **não recomendado** |

Detalhamento em [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Licença

MIT — ver [LICENSE](LICENSE).

## Aviso legal

Esta ferramenta é de apoio técnico. Os dados são extraídos de texto legislativo
público e devem ser verificados por um profissional habilitado antes do uso.
O uso como substituto da leitura da lei vigente, do projeto ou da responsabilidade
técnica é de responsabilidade exclusiva de quem o utiliza.
