/* LegisUrb - interface (vanilla JS, sem build). */

const state = {
  cities: [],
  city: null,
  zones: [],
  questions: [],
  lastResult: null,
};

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
};

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (_) { /* ignore */ }
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

/* ------------------------------------------------------------------ boot */
async function boot() {
  const data = await api('/api/cities');
  state.cities = data.items;
  const select = $('#city');
  state.cities.forEach((c) => {
    const opt = el('option', null, `${c.name} — ${c.uf}`);
    opt.value = c.slug;
    select.appendChild(opt);
  });
  $('#disclaimer').textContent =
    'Ferramenta de apoio técnico: os parâmetros exibidos provêm do texto legislativo e ' +
    'dependem de interpretação, de verificações específicas e de parecer do responsável ' +
    'técnico (ART/RRT). Não substitui a leitura da lei vigente nem a análise do órgão municipal.';

  select.addEventListener('change', () => loadCity(select.value));
  $('#zone').addEventListener('change', () => render());
  $('#btn-analyze').addEventListener('click', analyze);
  $('#btn-clear').addEventListener('click', clearForm);
  $('#btn-save').addEventListener('click', saveAnalysis);
  $('#btn-print').addEventListener('click', () => window.print());
  $('#btn-saved').addEventListener('click', openSaved);
  $('#btn-close-modal').addEventListener('click', () => $('#modal').hidden = true);

  if (state.cities.length) await loadCity(state.cities[0].slug);
}

/* -------------------------------------------------------------- city load */
async function loadCity(slug) {
  const city = await api(`/api/cities/${slug}`);
  state.city = city;
  state.zones = city.zones;
  state.questions = city.questions;

  $('#city-help').textContent = city.description || '';

  const zoneSelect = $('#zone');
  zoneSelect.innerHTML = '';
  const first = el('option', null, '— selecione —');
  first.value = '';
  zoneSelect.appendChild(first);
  city.zones.forEach((z) => {
    const opt = el('option', null, `${z.code} — ${z.name}`);
    opt.value = z.code;
    zoneSelect.appendChild(opt);
  });

  const manual = city.zone_selection.method === 'manual';
  $('#zone-field').hidden = false;
  $('#zone-help').textContent = manual
    ? (city.zone_selection.hint || '')
    : 'A zona é deduzida a partir das respostas. Se quiser, selecione manualmente.';
  const helper = $('#zone-helper');
  if (city.zone_selection.helper_url) {
    helper.href = city.zone_selection.helper_url;
    helper.hidden = false;
  } else {
    helper.hidden = true;
  }

  // A resolucao por geolocalizacao usa o bloco dedicado de lat/lon. Quando a
  // cidade ja traz lat/lon como perguntas do questionario, o bloco e omitido
  // para nao duplicar o mesmo campo na tela.
  const temGeoNoQuestionario = city.questions.some((q) => q.key === 'lat' || q.key === 'lon');
  const querGeo =
    city.zone_selection.method === 'geo' ||
    city.zone_selection.method === 'questionnaire' ||
    temGeoNoQuestionario;
  $('#geo-field').hidden = !(querGeo && !temGeoNoQuestionario);

  renderQuestions();
  clearResults();
}

/* ------------------------------------------------------------- questions */
function renderQuestions() {
  const box = $('#questionnaire');
  box.innerHTML = '';
  state.questions.forEach((q) => {
    const row = el('div', `q-row ${q.type === 'boolean' ? 'boolean' : ''}`);
    const labelBox = el('div');
    const label = el('div', 'q-label');
    label.append(document.createTextNode(q.label));
    if (q.unit) label.append(el('span', 'muted', ` (${q.unit})`));
    labelBox.appendChild(label);
    if (q.help) labelBox.appendChild(el('div', 'q-help', q.help));
    row.appendChild(labelBox);

    const inputBox = el('div', 'q-input');
    if (q.type === 'boolean') {
      const wrap = el('label');
      const input = el('input');
      input.type = 'checkbox';
      input.id = `q-${q.key}`;
      wrap.appendChild(input);
      wrap.appendChild(document.createTextNode('sim'));
      inputBox.appendChild(wrap);
    } else if (q.type === 'select') {
      const select = el('select');
      select.id = `q-${q.key}`;
      const blank = el('option', null, '— selecione —');
      blank.value = '';
      select.appendChild(blank);
      (q.options || []).forEach((opt) => {
        const o = el('option', null, opt);
        o.value = opt;
        select.appendChild(o);
      });
      if (q.default) select.value = q.default;
      inputBox.appendChild(select);
      row.classList.add('wide');
    } else {
      const input = el('input');
      input.type = 'number';
      input.step = 'any';
      input.id = `q-${q.key}`;
      if (q.default !== null && q.default !== undefined) input.value = q.default;
      inputBox.appendChild(input);
    }
    row.appendChild(inputBox);
    box.appendChild(row);
  });
}

function collectAnswers() {
  const answers = {};
  state.questions.forEach((q) => {
    const node = document.getElementById(`q-${q.key}`);
    if (!node) return;
    if (q.type === 'boolean') {
      if (node.checked) answers[q.key] = true;
    } else if (node.value !== '' && node.value !== undefined) {
      answers[q.key] = q.type === 'number' ? Number(node.value) : node.value;
    }
  });

  // Bloco dedicado de geolocalizacao (usado quando a cidade nao traz
  // lat/lon como perguntas do questionario).
  const lat = document.getElementById('lat');
  const lon = document.getElementById('lon');
  if (lat && lat.value !== '') answers.lat = Number(lat.value);
  if (lon && lon.value !== '') answers.lon = Number(lon.value);

  return answers;
}

/* --------------------------------------------------------------- analyze */
async function analyze() {
  const btn = $('#btn-analyze');
  btn.disabled = true;
  btn.textContent = 'Consultando...';
  try {
    const payload = {
      city: state.city.slug,
      zone: $('#zone').value || null,
      answers: collectAnswers(),
    };
    state.lastResult = await api('/api/analyze', { method: 'POST', body: JSON.stringify(payload) });
    render();
  } catch (err) {
    showError(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Consultar regras';
  }
}

async function saveAnalysis() {
  try {
    const payload = {
      city: state.city.slug,
      zone: $('#zone').value || null,
      answers: collectAnswers(),
      name: `${state.city.name} — ${$('#zone').value || 'sem zona'}`,
    };
    await api('/api/projects', { method: 'POST', body: JSON.stringify(payload) });
    await refreshSavedCount();
  } catch (err) {
    showError(err.message);
  }
}

/* ---------------------------------------------------------------- render */
function render() {
  const box = $('#results');
  box.innerHTML = '';
  const result = state.lastResult;
  if (!result) {
    box.appendChild(emptyState());
    return;
  }

  const head = el('div', 'result-head');
  const zoneWrap = el('div');
  const zoneName = el('div', 'zone');
  zoneName.textContent = result.zone ? result.zone.code : 'Zona não definida';
  if (result.zone) {
    const small = el('small', null, result.zone.name);
    zoneName.appendChild(small);
  }
  zoneWrap.appendChild(zoneName);
  const s = result.summary;
  zoneWrap.appendChild(el('div', 'muted small', result.zone_resolution.message));
  head.appendChild(zoneWrap);
  head.appendChild(el('span', `badge ${statusClass(s.status)}`, statusLabel(s.status)));

  const counters = el('div', 'counters');
  counters.appendChild(counter('Conforme', s.conforme, 'ok'));
  counters.appendChild(counter('Não conforme', s.nao_conforme, 'danger'));
  counters.appendChild(counter('Pendente', s.pendente, 'pend'));
  counters.appendChild(counter('Atenção', s.atencao, 'warn'));
  head.appendChild(counters);
  box.appendChild(head);

  if (result.zone_resolution.candidates && result.zone_resolution.candidates.length > 1) {
    const notice = el('div', 'notice warn',
      'As respostas apontam para mais de uma zona (' +
      result.zone_resolution.candidates.join(', ') +
      '). Selecione a zona aplicável no formulário.');
    box.appendChild(notice);
  }
  if (result.missing_required && result.missing_required.length) {
    box.appendChild(el('div', 'notice warn',
      'Campos obrigatórios ainda não informados: ' + result.missing_required.join(', ') + '.'));
  }

  /* limites */
  box.appendChild(el('h3', 'section', 'Limites da zona'));
  box.appendChild(paramsTable(result.parameters));

  /* verificações */
  box.appendChild(el('h3', 'section', 'Verificação do projeto'));
  const checks = el('ul', 'checks');
  if (!result.checks.length) {
    checks.appendChild(el('li', 'check', 'Nenhum parâmetro aplicável.'));
  }
  result.checks.forEach((c) => checks.appendChild(checkItem(c)));
  box.appendChild(checks);

  /* pontos de atenção */
  if (result.requirements.length) {
    box.appendChild(el('h3', 'section', 'Pontos de atenção e exigências adicionais'));
    const reqs = el('ul', 'reqs');
    result.requirements.forEach((r) => {
      const li = el('li', `req ${r.severity === 'info' ? 'info' : ''}`);
      li.appendChild(el('div', 't', r.title));
      li.appendChild(el('div', 'm', r.message));
      if (r.basis && r.basis.ref) li.appendChild(el('div', 'b', `Base legal: ${r.basis.ref}`));
      reqs.appendChild(li);
    });
    box.appendChild(reqs);
  }

  /* fontes */
  if (result.sources.length) {
    box.appendChild(el('h3', 'section', 'Fontes legais'));
    const list = el('ul', 'sources');
    result.sources.forEach((src) => {
      const li = el('li', 'source');
      li.appendChild(el('div', 't', src.title));
      const meta = [];
      if (src.number) meta.push(`Lei nº ${src.number}/${src.year || ''}`);
      if (src.consolidated_as_of) meta.push(`consolidada até ${src.consolidated_as_of}`);
      if (src.retrieved_at) meta.push(`consultada em ${src.retrieved_at}`);
      li.appendChild(el('div', 'm', meta.join(' · ')));
      if (src.url) {
        const a = el('a', null, 'Abrir documento oficial ↗');
        a.href = src.url;
        a.target = '_blank';
        a.rel = 'noopener';
        li.appendChild(a);
      }
      if (src.notes) li.appendChild(el('div', 'm', src.notes));
      list.appendChild(li);
    });
    box.appendChild(list);
  }

  box.appendChild(el('p', 'disclaimer', result.disclaimer));
}

function paramsTable(parameters) {
  const table = el('table', 'params');
  const thead = el('thead');
  const tr = el('tr');
  ['Parâmetro', 'Valor', 'Base legal'].forEach((h) => tr.appendChild(el('th', null, h)));
  thead.appendChild(tr);
  table.appendChild(thead);
  const tbody = el('tbody');
  parameters.forEach((p) => {
    const row = el('tr');
    const nameCell = el('td');
    nameCell.appendChild(el('div', null, p.label));
    row.appendChild(nameCell);
    row.appendChild(el('td', 'val', p.value_display));
    const base = el('td', 'base');
    base.textContent = p.basis && p.basis.ref ? p.basis.ref : '—';
    row.appendChild(base);
    tbody.appendChild(row);
    if (p.notes && p.notes.length) {
      const noteRow = el('tr', 'note');
      const cell = el('td');
      cell.colSpan = 3;
      p.notes.forEach((n) => cell.appendChild(el('div', null, n)));
      noteRow.appendChild(cell);
      tbody.appendChild(noteRow);
    }
  });
  table.appendChild(tbody);
  return table;
}

function checkItem(c) {
  const li = el('li', 'check');
  li.appendChild(el('div', 'title', c.label));
  li.appendChild(el('span', `badge ${statusClass(c.status)}`, statusLabel(c.status)));
  if (c.computed_display) li.appendChild(el('div', 'msg', `Projeto: ${c.computed_display}`));
  li.appendChild(el('div', 'msg', c.message));
  if (c.allowance) li.appendChild(el('div', 'allowance', `${c.allowance.label}: ${c.allowance.display}`));
  if (c.basis && c.basis.ref) {
    const basis = el('div', 'basis');
    basis.textContent = `Base legal: ${c.basis.ref}`;
    li.appendChild(basis);
  }
  if (c.notes && c.notes.length) {
    const notes = el('div', 'notes');
    c.notes.forEach((n) => notes.appendChild(el('p', null, n)));
    li.appendChild(notes);
  }
  return li;
}

/* ---------------------------------------------------------------- utils */
function statusClass(status) {
  return {
    conforme: 'ok',
    nao_conforme: 'danger',
    pendente: 'pend',
    atencao: 'warn',
  }[status] || 'muted';
}

function statusLabel(status) {
  return {
    conforme: 'Conforme',
    nao_conforme: 'Não conforme',
    pendente: 'Dados pendentes',
    atencao: 'Atenção',
    nao_aplicavel: 'Não se aplica',
    referencia: 'Referência',
  }[status] || status;
}

function counter(label, value, cls) {
  const c = el('div', `counter ${cls}`);
  c.appendChild(el('b', null, String(value)));
  c.appendChild(document.createTextNode(label));
  return c;
}

function emptyState() {
  const div = el('div', 'empty');
  div.appendChild(el('h3', null, 'Nenhuma consulta realizada'));
  div.appendChild(el('p', null,
    'Preencha o questionário e clique em "Consultar regras" para obter os parâmetros ' +
    'de ocupação da zona, a verificação do projeto e a base legal de cada item.'));
  return div;
}

function showError(message) {
  const box = $('#results');
  box.innerHTML = '';
  box.appendChild(el('div', 'notice warn', `Erro: ${message}`));
}

function clearForm() {
  state.questions.forEach((q) => {
    const node = document.getElementById(`q-${q.key}`);
    if (!node) return;
    if (q.type === 'boolean') node.checked = false;
    else node.value = q.default !== null && q.default !== undefined ? q.default : '';
  });
  $('#zone').value = '';
  clearResults();
}

function clearResults() {
  state.lastResult = null;
  const box = $('#results');
  box.innerHTML = '';
  box.appendChild(emptyState());
}

/* ---------------------------------------------------------- saved items */
async function refreshSavedCount() {
  try {
    const data = await api('/api/projects');
    $('#saved-count').textContent = data.items.length
      ? `${data.items.length} análise(s) salva(s)`
      : '';
  } catch (_) { /* ignore */ }
}

async function openSaved() {
  const data = await api('/api/projects');
  const list = $('#saved-list');
  list.innerHTML = '';
  if (!data.items.length) {
    list.appendChild(el('p', 'muted', 'Nenhuma análise salva ainda.'));
  }
  data.items.forEach((p) => {
    const item = el('div', 'saved-item');
    const info = el('div');
    info.appendChild(el('div', null, p.name));
    info.appendChild(el('div', 'meta', new Date(p.created_at).toLocaleString('pt-BR')));
    item.appendChild(info);
    const open = el('button', 'btn', 'Abrir');
    open.addEventListener('click', async () => {
      const full = await api(`/api/projects/${p.id}`);
      state.lastResult = full.result;
      $('#modal').hidden = true;
      render();
    });
    item.appendChild(open);
    const del = el('button', 'btn ghost', 'Excluir');
    del.addEventListener('click', async () => {
      await api(`/api/projects/${p.id}`, { method: 'DELETE' });
      openSaved();
      refreshSavedCount();
    });
    item.appendChild(del);
    list.appendChild(item);
  });
  $('#modal').hidden = false;
}

boot().catch((err) => showError(err.message));
