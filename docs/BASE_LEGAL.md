# Base legal — política de origem, versionamento e atualização

Esta é a parte mais importante do repositório. Um número de parâmetro sem
procedência é opinião; com procedência, é dado técnico citável.

## Princípios

1. **Origem oficial obrigatória.** Todo valor vem de texto publicado pelo
   município (lei, decreto, anexo, diário oficial) ou de fonte oficial de
   zoneamento (GeoSampa, portal de Geosampa do Estado, etc.).
2. **Citação localizável.** Não basta "Lei 16.402": o `ref` aponta o artigo,
   parágrafo, inciso, linha do quadro ou nota de rodapé.
3. **Data de consolidação.** Toda fonte declara até quando o texto foi
   conferido. Dado sem data é dado que ninguém pode atualizar.
4. **Divergência registrada, não escondida.** Quando o texto legal é ambíguo ou
   quando a interpretação depende de caso concreto, o sistema **avisa** — não
   escolhe um valor silenciosamente.
5. **Ausência declarada.** Parâmetro que a lei não fixa para a zona fica
   `null` ("não se aplica"), e não recebe valor inventado.

## Fontes usadas na v0.1

| Chave | Documento | Onde consultar | Consolidação |
|---|---|---|---|
| `luos` | Lei nº 16.402/2016 — Parcelamento, uso e ocupação do solo (LUOS) | [legislacao.prefeitura.sp.gov.br](https://legislacao.prefeitura.sp.gov.br/lei-16402-de-22-de-marco-de-2016) | 2024-07-25 |
| `quadro3` | Anexo 3 da LUOS — Quadro 3: Parâmetros de ocupação (exceto Quota Ambiental) | [arquivo do anexo](https://app-plpconsulta-prd.azurewebsites.net/Forms/MostrarArquivo?TIPO=Lei&NUMERO=16402&ANO=2016&DOCUMENTO=ANEXO&Anexo=3) | 2024-07-25 |
| `pde` | Lei nº 16.050/2014 — Plano Diretor Estratégico | [legislacao.prefeitura.sp.gov.br](https://legislacao.prefeitura.sp.gov.br/lei-16050-de-31-de-julho-de-2014) | 2024-07-25 |

O texto da LUOS usado é o **compilado** pelo próprio município, que já
incorpora as alterações até a Lei nº 18.177/2024 (publicada em 2024). Para uso
em protocolo, confira a redação vigente na data.

### O que o Quadro 3 traz e o que ele traz só indiretamente

O Quadro 3 é a fonte direta de: coeficiente de aproveitamento (máximo, base,
mínimo), taxa de ocupação, gabarito (altura máxima) e recuos (frontal, lateral,
de fundo). Esses valores estão reproduzidos zona a zona em
`data/cities/sao-paulo/city.yaml`.

O restante vem do **corpo da lei** e foi convertido em regras condicionais:

| Artigo / nota | Regra convertida |
|---|---|
| Art. 66, I | Dispensa de recuos laterais e de fundo e de gabarito para edificações de até 10 m de altura (com exceções por zona) |
| Art. 66, II | Exigência de recuos de fundo (5 m) e de vão livre para embutir edificações — registrado como **atenção** por depender de caso concreto |
| Art. 67, §1º | Dispensa de recuo frontal para edificações de até 10 m de altura, observadas as exceções do Anexo 3 |
| Art. 69 | Dispensa de recuo frontal e lateral em Immutable |
| Art. 72 | Permeabilidade mínima de 20% (15% em recálques) — **aplica-se somente a UG‑I e a lotes com recálque**, não à regra geral |
| Art. 74 a 76 / Quadros 3A e 3B | Quota Ambiental: a exigência é a Quota Ambiental (o "percentual de permeabilidade" do art. 72 não é a regra geral) |
| Art. 76, §2º | Isenção de QA para lotes com área ≤ 500 m² |
| Art. 81 / Quadro 3A | Parâmetros de permeabilidade e de Quota Ambiental previstos no Quadro 3A |
| Art. 91 | Majoração do recuo frontal em zonas ZCOR (fator 1,4) |
| Notas (a) a (o) do Quadro 3 | Convertidas em `notes` dos parâmetros e em regras condicionais (nota (n): recuo de fundo de 5 m) |

> **Cuidado metodológico importante.** O art. 72 da LUOS fala em
> "percentual de permeabilidade", mas a Quota Ambiental (arts. 74 a 76) é o
> mecanismo geral de área permeável, calculado por planilha oficial do
> Executivo. Tratar 20% como "regra geral de permeabilidade" seria errado — e
> foi o erro que o modelo de dados deste repositório evita: o parâmetro
> `permeability_min_pct` tem regra condicionada e a exigência de QA aparece
> como item separado, com a base legal da QA.

### Sobre a Quota Ambiental

O sistema **indica** a exigência de QA (com base legal) mas **não calcula** a
pontuação: a planilha oficial do Executivo (Quadros 3A/3B) depende de
variáveis que o engenheiro precisa levantar no campo (declividade, visada,
soleira, permeabilidade solo, etc.). A automatização desse cálculo é item do
roadmap (N2), e depende de acesso à planilha vigente.

## Como o dado legal é versionado

- O **YAML é a fonte da verdade** e vive no Git. Toda alteração de valor é um
  commit, com a revisão de quem conhece a lei.
- O banco (SQLite/Postgres) é **derivado** e recriado a partir do YAML
  (loader idempotente, por hash do arquivo). Não se edita dado legal no banco.
- O hash do arquivo fica registrado, de modo que é possível saber qual versão
  do cadastro gerou uma análise salva.
- O teste de snapshot (`tests/test_sao_paulo.py`) fixa os valores do Quadro 3:
  qualquer mudança de valor **quebre o teste** e obriga a revisão explícita.

## Ciclo de atualização de um município

1. Verificar se houve alteração legislativa (diário oficial, legislação
   municipal e o compilador de textos do próprio município).
2. Ler o texto compilado (não o original) para pegar o consolidado.
3. Atualizar `consolidated_as_of` da fonte e `retrieved_at`.
4. Conferir cada valor afetado no YAML; atualizar `notes` se a redação mudou.
5. Atualizar ou criar o teste de snapshot.
6. Rodar `pytest` e `ruff`.
7. Abrir PR com a referência da lei alterada na mensagem.

Nenhuma atualização é aplicada "por conta própria" pelo sistema.

## Procedência em cada número exibido

Cada linha da tabela de parâmetros carrega:

```json
{
  "label": "Coeficiente de Aproveitamento máximo (CA)",
  "value": 2,
  "unit": "",
  "basis": {"source": "quadro3", "ref": "Quadro 3, linha ZM"},
  "notes": ["(m) Ver art. 362 da Lei nº 16.050/2014."]
}
```

E o relatório final lista as fontes com link oficial e data de consolidação,
permitindo que um terceiro reproduza a conclusão.

## Limites conhecidos desta base

- Cobertura de São Paulo: **Anexo 3 / Quadro 3** (ocupação do solo). Não
  inclui: Operação Urbana Consorciada, Estações Ferroviárias de Passageiros,
  Zoneamento Especial (ZEIS), planejamento urbano, áreas contaminadas,
  licenciamento ambiental, regras de circulação de veículos e quotas de
  garagem (item N2).
- A classificação da zona depende de consulta ao mapa oficial; o app não
  substitui essa consulta.
- Casos concretos (art. 66, II — vão livre e recuo de fundo em lote lindeiro
  a aro de rua) dependem de análise do órgão; o sistema sinaliza em vez de decidir.
