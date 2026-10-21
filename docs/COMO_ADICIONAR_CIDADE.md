# Como adicionar uma cidade

O motor é genérico: adicionar um município é **descrever a legislação em YAML**.
Nenhuma alteração de código é necessária.

## 1. Estrutura de pastas

```
data/cities/<slug>/
  city.yaml        # zonas, parâmetros, regras, fontes, questionário
  zones.geojson    # opcional: polígonos para resolução geográfica
```

`<slug>` é o identificador usado na URL da API (minúsculo, com hífen):
`sao-paulo`, `curitiba`, `campinas`.

## 2. Fontes primeiro

Todo parâmetro referencia uma fonte. Declare-as com link oficial e data:

```yaml
sources:
  - key: lous
    kind: lei
    number: "16.402"
    year: 2016
    title: "Lei nº 16.402/2016 — Parcelamento, uso e ocupação do solo"
    url: "https://legislacao.prefeitura.sp.gov.br/lei-16402-de-22-de-marco-de-2016"
    consolidated_as_of: "2024-07-25"     # até quando o texto foi compilado
    retrieved_at: "2026-10-21"            # quando consultamos
    notes: "Texto compilado com as alterações das Leis nº 18.081/2024 e nº 18.177/2024."

  - key: quadro3
    kind: anexo
    title: "Anexo 3 — Quadro 3: Parâmetros de ocupação"
    url: "https://.../Anexo=3"
```

Regras para as fontes:

- `key` é o identificador usado em `basis: {source: ..., ref: ...}`.
- `url` deve ser o endereço **oficial** (prefeitura, câmara, diário oficial).
  PDF em repositório de terceiro não serve.
- `consolidated_as_of` é obrigatório na prática: sem ele não há como saber
  se o dado ainda vale.

## 3. Zonas e parâmetros

```yaml
zones:
  - code: ZM
    name: "Zona Mista"
    group: "ZM"
    description: "Zona mista de uso residencial e não residencial."
    params:
      ca_max:
        label: "Coeficiente de Aproveitamento máximo (CA)"
        unit: ""
        value: 2
        basis: {source: quadro3, ref: "Quadro 3, linha ZM"}
        check: {type: ratio_max, numerator: total_built_area, denominator: lot_area}
        notes: ["(m) Ver art. 362 da Lei nº 16.050/2014."]
```

### Chaves de parâmetro reconhecidas

| Chave | Significado |
|---|---|
| `label` | texto exibido (obrigatório) |
| `unit` | unidade exibida (`m²`, `m`, `%`, `""`) |
| `value` | número do quadro; `null` quando a lei diz "não se aplica" |
| `basis` | `{source, ref}` — **obrigatório** (a suíte de testes falha sem isso) |
| `notes` | notas de rodapé e ressalvas, exibidas junto do valor |
| `check` | como verificar (ver tabela abaixo) |
| `alternatives` | valores conditioned ao terreno (ver abaixo) |

### Tipos de verificação (`check`)

| `type` | Campos | Significado |
|---|---|---|
| `ratio_max` | `numerator`, `denominator` | `(num / den) ≤ valor` — CA, TO |
| `gte` | `field` ou `fields` | `campo ≥ valor` — recuos mínimos |
| `lte` | `field` ou `fields` | `campo ≤ valor` — gabarito máximo |
| `min_area_from_pct` | `field`, `base` | área mínima = `valor%` de `base` — permeabilidade |
| `max_area_per_unit` | `field`, `divisor` | `campo ≤ valor × divisor` — cota-parte |
| (ausente) | — | parâmetro apenas referencial (exibido, sem verificação) |

### Valores alternativos

```yaml
to_max:
  check: {type: ratio_max, numerator: footprint_area, denominator: lot_area}
  alternatives:
    - value: 0.85
      when: {lot_area: {lt: 500}}
      basis: {source: quadro3, ref: "Quadro 3 — TO até 500 m²"}
      message: "TO para lotes de até 500,00 m²."
    - value: 0.70
      when: {lot_area: {gte: 500}}
      basis: {source: quadro3, ref: "Quadro 3 — TO a partir de 500 m²"}
```

A primeira alternativa cuja condição é satisfeita vence. Se nenhuma for
satisfeita e não há `value` base, o parâmetro fica **pendente** (falta dado).

### Condições (`when`)

```yaml
when:
  lot_area: {lt: 500}          # lt, lte, gt, gte, eq, ne
  use: {in: [comercial, misto]} # in, not_in
  building_height: {between: [10, 20]}
  sidewalk_width: {gte: 5}
```

Todas as chaves são combinadas com AND. Fato ausente ⇒ condição falsa.

## 4. Questionário

O questionário é o que o engenheiro preenche:

```yaml
questions:
  - key: lot_area
    label: "Área do lote"
    type: number          # number | select | boolean | derived
    required: true
    unit: "m²"
    help: "Área do terreno conforme matrícula."

  - key: use
    label: "Uso predominante pretendido"
    type: select
    required: true
    options: [residencial, comercial, industrial, misto]

  - key: floors
    label: "Número de pavimentos"
    type: number
    unit: "pav."

  - key: floor_height
    label: "Pé-direito"
    type: number
    unit: "m"
    default: 3.0          # valor padrão já aplicado

  - key: building_height
    label: "Altura da edificação"
    type: derived         # não aparece no formulário
    derivations:
      - fact: building_height
        op: mul            # mul, div, add, sub, min, max
        args: [floors, floor_height]
```

Nomes de campo livre, mas **consistentes** com os `numerator`/`denominator`/`field`
dos `check` e com as condições das regras. Os fatos calculados
(`building_height`, `lot_area`...) ficam disponíveis para regras.

## 5. Regras condicionais

```yaml
rules:
  - code: dispensa-recuos-laterais-fundo-altura
    title: "Dispensa de recuos laterais e de fundo por altura"
    message: "Recuos laterais e de fundo dispensados."
    severity: info        # info | attention
    when: {building_height: {lte: 10}}
    exclude_zones: [ZDE-2, ZPI-1]
    effects:
      - type: override_param
        param: setback_side_back
        value: 0
        message: "Dispensado (art. 66, I)."
    basis: {source: lous, ref: "Art. 66, I"}
```

Efeitos disponíveis:

- `override_param` — troca o valor do parâmetro (dispensa, majoração, recuo extra).
- `warning` / `add_requirement` — acrescenta exigência ao relatório.

`applies_to_zones` limita a regra a determinadas zonas; `exclude_zones` exclui
caso contrário.

## 6. Resolução da zona

```yaml
zone_selection:
  method: manual          # manual | questionnaire | geo
  hint: "Consulte o mapa oficial e selecione a sigla da zona."
  helper_url: "https://..."
  rules:                  # usado quando method = questionnaire
    - when: {use: {in: [comercial, misto]}}
      zone: ZC
      priority: 10
      message: "Uso comercial ou misto: zona central."
```

Com `method: geo`, coloque `zones.geojson` ao lado do YAML:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": { "code": "ZC" },
      "geometry": { "type": "Polygon", "coordinates": [[[lon, lat], ...]] }
    }
  ]
}
```

A geometria usa **GeoJSON padrão: [longitude, latitude]**.

## 7. Checklist antes de abrir o PR

- [ ] Toda fonte tem `url` oficial e `consolidated_as_of`.
- [ ] Todo parâmetro tem `basis` com `source` válido e `ref` localizável
      (artigo, parágrafo, linha do quadro).
- [ ] Todo valor foi conferido **no texto oficial**, não em resumo de terceiros.
- [ ] Notas de rodapé do quadro foram convertidas em `notes` ou em regras.
- [ ] Valores condicionais estão em `alternatives`, com a condição explícita.
- [ ] `pytest` passa.
- [ ] Anexado um teste de snapshot com os valores da nova cidade
      (como `tests/test_sao_paulo.py` faz para o Quadro 3).

## 8. Teste de snapshot para a nova cidade

Copie `tests/test_sao_paulo.py` e adapte:

```python
def test_quadro3_valores(db):
    cidade = db.query(City).filter(City.slug == "minha-cidade").one()
    zona = db.query(Zone).filter(Zone.city_id == cidade.id, Zone.code == "ZC").one()
    params = {p.key: p for p in db.query(Parameter).filter(Parameter.zone_id == zona.id).all()}
    assert params["ca_max"].value_num == 2
    assert params["max_height"].value_num == 45
```

Esse teste é o que impede que uma alteração de lei (ou um erro de digitação)
passe despercebida.
