# Roadmap

O objetivo do projeto não é "responder perguntas sobre lei" — é
**encaminhar o engenheiro para o projeto correto na primeira tentativa**, com
rastreabilidade de cada número.

## N1 — Consulta com citação legal ✅ (v0.1, este repositório)

- [x] Cadastro estruturado da legislação (YAML versionado) por município e zona
- [x] Motor determinístico de conformidade (recuos, CA, TO, gabarito, permeabilidade)
- [x] Regras condicionais (dispensas, faculdades, majorações, notas de rodapé)
- [x] Base legal citada, com link oficial e data de consolidação
- [x] Questionário do projeto → fatos → verificações
- [x] São Paulo (39 zonas, 18 regras) + cidade de demonstração
- [x] Três modos de resolução de zona: manual, questionário, geográfico
- [x] Testes automatizados com snapshot dos valores legais
- [x] Relatório imprimível, export JSON e histórico de análises

## N2 — Relatório e checklist de não conformidades

- [ ] Exportação de PDF (relatório técnico com ART/RRT em branco) e DOCX
- [ ] Checklist por zona exportável para uso em campo
- [ ] Cálculo automático da Quota Ambiental (QA) a partir da planilha oficial
- [ ] Regras de circulação e quotas de garagem (Lei nº 16.402/2016, art. 133 e ss.)
- [ ] Importação de footprint/lote a partir de arquivo (DXF/GeoJSON/shapefile)
- [ ] Registro de histórico de versões da base legal por município

## N3 — Extração de parâmetros do projeto

- [ ] Leitura de planta/DWG para extrair área do lote, projeção, recuos propostos
- [ ] Conferência automática: projeto vs. limites, com highlight no desenho
- [ ] Sugestão de ajuste (ex.: "recuo frontal de 3 m → ajuste para 5 m")
- [ ] Cadastro de projetos (multi-empreendimento) e comparação de cenários

## N4 — Validação geométrica/BIM

- [ ] Plugin Revit/Dynamo ou script IFC (IfcOpenShell)
- [ ] Verificação de volume, pé-direito, recuos e área permeável sobre a geometria
- [ ] Relatório de conflitos entre modelo e parâmetros da zona

## N5 — Protocolo automático ⚠️ *não recomendado*

Tratar o sistema como substituto da análise municipal é tecnicamente errado
e juridicamente irresponsável. A interface deve deixar isso explícito.
**Não haverá feature de "aprovar/protocolar" neste projeto.**

## Backlog técnico

- [ ] Autenticação e multiusuário (hoje: local, single-user)
- [ ] Postgres + backup (o schema já é portátil)
- [ ] Cache de resolução geográfica (currently point-in-polygon linear)
- [ ] Internacionalização (hoje: somente pt-BR, de propósito)
- [ ] CI com checagem de link das fontes oficiais (link checker)
- [ ] Fila de verificação de vigência: consultar periodicamente a legislação do
      município e abrir issue quando o texto mudar

## Explicitamente fora do escopo

- Substituir a leitura da lei, o projeto ou a responsabilidade técnica
- Emitir ART/RRT
- Decidir casos concretos que dependem de interpretação do órgão
- Modelar zoneamento de municípios sem texto oficial aberto de forma estável
  (dados abertos primeiro, sempre)
