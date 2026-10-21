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

## Porto Alegre (RS) — LC 1076/2026 e LC 1075/2026

### Fontes

| Chave | Documento | Onde consultar | Consolidação |
|---|---|---|---|
| `luos` | Lei Complementar nº 1.076/2026 — Parcelamento, uso e ocupação do solo (LUOS) | [legislacao.portoalegre.rs.gov.br](https://legislacao.portoalegre.rs.gov.br/norma/51486) | 2026-07-14 |
| `luos_anexo2` | Anexo 2 da LC 1076/2026 — Quadros de regime urbanístico por ZOT (fls. 1 a 54) e Anexo 1 (mapa de zoneamento) | [PDF do anexo](https://legislacao.portoalegre.rs.gov.br/media/sapl/public/anexonormajuridica/2026/1420/lc1076a.pdf) | 2026-07-14 |
| `pdus` | Lei Complementar nº 1.075/2026 — Plano Diretor Urbano Sustentável | [legislacao.portoalegre.rs.gov.br](https://legislacao.portoalegre.rs.gov.br/norma/51485) | — (fonte de referência) |

O `pdus` é citada apenas como referência de macrozoneamento e de finalidades
das ZOTs (art. 4 da LUOS); não fundamenta nenhum parâmetro numérico, e por
isso não tem data de consolidação.

A Lei nº 14.582/2026 (consultada em 21/10/2026) trata do calendário de
eventos da cidade e **não** altera a LC 1076/2026.

### Como o regime de Porto Alegre é diferente do de São Paulo

Porto Alegre não usa taxa de ocupação. O regime de cada **Zona de Ordenamento
Territorial (ZOT)** é composto por:

| Parâmetro | Regra |
|---|---|
| Coeficiente de Aproveitamento | **Básico** (potencial sem contrapartida, art. 72, I) e **Máximo** (limite de conformidade) |
| Altura máxima | por ZOT, com acréscimos do art. 81, §2º (rooftop e bem tombado) |
| Afastamentos lateral e de fundo | **18% da altura** a partir da Referência de Nível, aplicável **acima de 12,5 m** (nota 6 do Anexo 2); 15% nos trechos com 20 m entre divisas paralelas (nota 7) |
| Recuo de jardim | 4 m, ou 12 m em vias estruturantes ou arteriais (ZOTs 14 a 16) |
| Taxa de Permeabilidade (TP) | em degraus: por exemplo, na ZOT 4, 20% sobre os primeiros 1.500 m² e 30% sobre o excedente |
| Fator de conversão da TP | percentual máximo da TP convertível em medidas alternativas (nota de rodapé do Anexo) |

As ZOTs 8.1, 8.2 e 8.3 têm **sub-setores** identificados por letra no desenho
do Anexo 2 (fls. 2 e 3), o que leva a 29 zonas cadastradas a partir de 19
ZOTs.

### Regras condicionais convertidas

| Artigo / nota | Regra convertida |
|---|---|
| Art. 24, §1º | Base de aplicação do regime é a menor poligonal do imóvel (título x local), com acréscimo de até 5% a critério do requerente |
| Art. 24, §2º | Remembramento: aplicam-se os regimes de cada matrícula original |
| Art. 24, §3º | Imóvel em mais de uma ZOT: regime proporcional à área de cada ZOT (exceção: ZOTs 15 e 16) |
| Art. 24, §4º | CA das ZOTs 1 e 2: incide sobre toda a área (I), limitado ao Módulo de Fracionamento de 3.000 m² salvo parcelamento com equipamentos comunitários (II), reduzido em 50% em terreno de até 22.500 m² sem origem em parcelamento (III) |
| Art. 24, §5º | CA de uso não residencial incide sobre toda a área do terreno |
| Art. 26 | Traçado do Plano Diretor: cálculo sobre a área remanescente ou sobre a totalidade mediante TDC; na área atingida, altura limitada a 9 m |
| Art. 19, §2º | HIS na ZOT 14 adota o regime urbanístico da ZOT 1 |
| Art. 73 | Isenções de CA (garagem e circulações, residence unifamiliar, fachada ativa, entre outras) |
| Art. 74 | Regime Especial +4D na ZOT 8.2: CA básico 7,5 e máximo 13, mediante pontuação mínima do Anexo 2.8.2, fl. 3 |
| Art. 79 | Dispenas de TP: ampliação sobre área edificada, atividade incompatível, lote de até 150 m², Centro Histórico |
| Art. 81, §2º | Acréscimos de altura: rooftop (4 m) e bem tombado (9 m) |
| Art. 82 | Afastamentos laterais e de fundos = 18% da altura (15% em trechos com 20 m entre divisas) |
| Art. 83 | Recuo de jardim |
| Anexo 2, nota 6 | Afastamento de 18% da altura a partir da RN, aplicável acima de 12,5 m |

### Interpretações registradas (não escondidas)

Três pontos do texto não admitem valor único e foram tratados como
**pendência ou nota**, nunca como valor escolhido em silêncio:

1. **CA das ZOTs 1 e 2 (art. 24, §4º, III).** O texto reduz em 50% "o
   coeficiente de aproveitamento" sem distinguir entre o básico e o máximo. A
   redução foi aplicada a **ambos** (o básico não pode superar o máximo), e a
   nota do parâmetro pede confirmação ao órgão competente. Sem a informação
   sobre a origem do lote (parcelamento do solo aprovado pelo Município), o
   valor fica **pendente** — o motor não escolhe entre 1,25 e 2,5 sozinho.
2. **CA máximo das ZOTs 14, 15 e 16.** O Anexo 2 registra "Ajuste / TDC" em
   vez de número: o limite é caso a caso, e o parâmetro fica como
   **pendente**, com o texto do Anexo citado.
3. **Altura do Sítio Histórico (ZOT 8.1 G).** O Anexo 2 registra "Órgão
   Competente" (IPHAN/IPHAE): fica **pendente**, não estimado.

Da mesma forma, o limite de 12,5 m para aplicação do afastamento de 18% vem da
nota 6 do Anexo 2 e está reproduzido no `check` do parâmetro, com a nota de
rodapé na íntegra.

### Testes de snapshot

`tests/test_porto_alegre.py` fixa os 29 quadros do Anexo 2 e as regras
condicionais (redução de 50% do CA, base de cálculo limitada ao Módulo de
Fracionamento, TP em degraus, afastamento de 18% da altura, dispensa de TP em
lote de até 150 m², HIS na ZOT 14, +4D na ZOT 8.2). Qualquer alteração de valor
no YAML quebra o teste e exige revisão explícita.

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
