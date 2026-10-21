# Arquitetura

## Princípio

> O número que decide é o número da lei. O software explica, compara e avisa —
> ele não "interpreta".

Isso elimina a classe de erro mais grave em uma ferramenta jurídica: alucinar
parâmetro. Um LLM errando "o recuo lateral em ZM é 5 m" é grave; um motor
determinístico que carrega o Quadro 3 e compara com o projeto é auditável.

## Camadas

```
┌─────────────────────────────────────────────────────────────────┐
│  1. BASE NORMATIVA ESTRUTURADA                                   │
│  fontes (lei/decreto/anexo) → artigos → parâmetros por zona      │
│  + vigência, consolidação, link oficial, notas de rodapé        │
│  formato: YAML versionado em data/cities/<municipio>/city.yaml   │
└─────────────────────────────────────────────────────────────────┘
                              │  (loader idempotente por hash)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. MOTOR DETERMINÍSTICO                                         │
│  fatos do projeto ← questionário                                │
│  resolução da zona (manual | questionário | geo)                │
│  resolução de valores (alternativas condicionais)               │
│  regras condicionais (dispensas, faculdades, exigências extras)  │
│  verificações (ratio_max, gte, lte, min_area_from_pct, ...)     │
└─────────────────────────────────────────────────────────────────┘
                              │  JSON determinístico
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. API + INTERFACE                                               │
│  FastAPI (/api/analyze, /api/cities, /api/projects)             │
│  interface HTML/CSS/JS sem build, com impressão e export JSON   │
└─────────────────────────────────────────────────────────────────┘
```

## Decisões e porquês

### Por que YAML, e não banco como fonte da verdade?

O cadastro legal é essencialmente texto com estrutura semi-regular. YAML com
*merge keys* (`<<: *modelo`) permite declarar 39 zonas sem repetir os rótulos,
as unidades e os tipos de verificação — e o diff no Git mostra exatamente qual
número mudou. O banco é gerado a partir do YAML (idempotente por hash de
arquivo), o que mantém a revisão por pull request como forma natural de
auditoria da base legal.

### Por que condições declarativas em vez de código Python?

Cada regra legal vira dados:

```yaml
when: {lot_area: {lt: 500}}
effects:
  - type: override_param
    param: ca_max
    value: 2
```

Vantagens: (a) um revisor não programador consegue auditar a regra; (b) a mesma
estrutura serve ao motor geográfico, ao motor de limites e ao futuro motor de
documentos; (c) é testável sem escrever código. O avaliador é propositalmente
pequeno (`conditions.py`) — sem Turing completo, sem eval.

### Por que três formas de resolver a zona?

| Modo | Quando | Quem usa |
|---|---|---|
| `manual` | município publica mapa georreferenciado e não há dado aberto no repositório | engenheiro que já consultou o mapa |
| `questionnaire` | regras de zoneamento são dedutíveis dos atributos do terreno | município com regra simples de uso |
| `geo` | existe GeoJSON de zonas | pipeline com dado oficial aberto |

Para São Paulo usamos `manual` de propósito: publicar um mapa de zoneamento
errado seria pior do que pedir ao engenheiro que informe a sigla que leu no
GeoSampa (link direto na interface).

### Por que o resultado mostra "pendente" em vez de estimar?

Dado faltando não é conformidade. Um sistema que "chuta" o recuo lateral para
fechar a tabela contamina a decisão do engenheiro. O motor marca `pendente` e lista
exatamente qual campo falta.

### Por que a base legal vem junto do número?

Toda saída da verificação carrega `basis: {source, ref}` e o item aparece em
"Fontes legais" com link para o documento oficial e data de consolidação.
Não é decoração: é o que permite a um terceiro reproduzir a conclusão.

## Modelo de dados

```
City ─┬─< Source        (lei, decreto, anexo; url, consolidado_as_of, retrieved_at)
      ├─< Zone ──< Parameter   (key, value, check, alternatives, basis, notes)
      ├─< Rule                (when, applies_to_zones, effects, basis)
      ├─< Question            (key, type, required, options, derivations)
      └─< Project             (análise salva: input + resultado)
```

`Parameter.alternatives` implementa os quadros com valor dependente da
condição do terreno — sem duplicar o parâmetro:

```yaml
to_max:
  alternatives:
    - value: 0.85
      when: {lot_area: {lt: 500}}
    - value: 0.70
      when: {lot_area: {gte: 500}}
```

`Rule.effects` implementa dispensas e exigências:

| Efeito | Efeito |
|---|---|
| `override_param` | substitui o valor do parâmetro (dispensa, majoração, recuo adicional) |
| `warning` / `add_requirement` | adiciona uma exigência ao relatório, com base legal |

## Fluxo de uma análise

1. `build_facts` — lê as respostas, aplica defaults e derivações
   (`building_height = floors × floor_height`).
2. `resolve_zone` — zona manual, geográfica ou deduzida; devolve candidatos quando
   há ambiguidade.
3. `_resolve_param_value` — escolhe o valor do parâmetro (base ou alternativa que
   satisfaz a condição).
4. Regras — filtra por zona, avalia `when` e aplica `effects` (overrides e exigências).
5. `run_check` — compara o limite com o fato do projeto e produz
   `conforme | nao_conforme | pendente | nao_aplicavel | referencia | atencao`.
6. Montagem do relatório — parâmetros, verificações, exigências, fontes, pendências.

## Extensões previstas

- **Novo tipo de verificação** — basta adicionar um `elif ctype == ...` em
  `app/engine/checks.py` e descrever o `check:` no YAML.
- **Nova fonte de parâmetros** — hoje o YAML é escrito à mão a partir do PDF
  oficial. O passo natural (N2) é um importador que lê o PDF do quadro e gera
  o esqueleto do YAML para revisão humana — nunca publicação automática.
- **Postgres + pgvector** — para quando houver histórico de análises e busca
  semântica sobre pareceres; o schema já é relacional e portátil.

## Segurança e privacidade

- O application store apenas parâmetros de terreno e o resultado da análise:
  não há dado pessoal do usuário.
- Nenhum dado é enviado a terceiros; a aplicação é local/self-hosted.
- Se for hospedada para uso multiusuário, autenticação, HTTPS e isolamento por
  escritório são requisitos prévios (fora do escopo da v0.1).
