/* ═══════════════════════════════════════════════════════════════
   app.js — Email Rectifier Assistant v2 Frontend
   ═══════════════════════════════════════════════════════════════ */

const App = (() => {

  /* ── State ────────────────────────────────────────────────── */
  let state = {
    screen:       'auth',
    username:     '',
    emailAddress: '',
    provider:     'gmail',
    emails:       [],
    filteredEmails: [],
    analysis:     null,
    preferences:  null,
    scanPollId:   null,
    currentFilter: 'all',
    currentTab:   'emails',
    emailCount:   100,
    radios: {
      life_mode:               'Work',
      fraud_sensitivity:       'MEDIUM',
      notification_preference: 'only_important',
      summary_preference:      'MEDIUM',
    },
  };

  /* ── Utilities ────────────────────────────────────────────── */
  const $ = id => document.getElementById(id);

  function showAlert(id, msg, type = 'error') {
    const el = $(id);
    el.className = `alert ${type}`;
    el.textContent = msg;
    el.style.display = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 4000);
  }

  async function apiFetch(url, options = {}) {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    return res.json();
  }

  function setLoading(btnId, loading, text = '') {
    const btn = $(btnId);
    if (!btn) return;
    btn.disabled = loading;
    const span = btn.querySelector('span');
    if (span) span.innerHTML = loading ? '<span class="spinner"></span>' : text || span.textContent;
  }

  function getCatEmoji(cat) {
    const map = {
      FINANCIAL:'💰', PROFESSIONAL:'💼', EDUCATIONAL:'🎓', TRAVEL:'✈️',
      HEALTHCARE:'🏥', GOVERNMENT:'🏛️', TRANSACTIONAL:'🧾', PROMOTIONAL:'📢',
      SOCIAL:'👥', SYSTEM:'⚙️', COMMUNITY:'🏘️', SERVICE:'🔧', PERSONAL:'💌',
      SPAM:'🚫',
    };
    return (map[cat] || '📨') + ' ' + (cat.charAt(0) + cat.slice(1).toLowerCase());
  }

  function getPriorityColor(p) {
    if (p >= 75) return '#f59e0b';
    if (p >= 50) return '#7c3aed';
    if (p >= 30) return '#06b6d4';
    return '#475569';
  }

  function buildPriorityRing(score) {
    const r = 13, circ = 2 * Math.PI * r;
    const dash = (score / 100) * circ;
    const color = getPriorityColor(score);
    return `<div class="priority-ring">
      <svg width="32" height="32" viewBox="0 0 32 32">
        <circle class="bg" cx="16" cy="16" r="${r}" stroke="#1a1a2e"/>
        <circle class="fg" cx="16" cy="16" r="${r}" stroke="${color}"
          stroke-dasharray="${dash} ${circ}" stroke-dashoffset="0"/>
      </svg>
      <div class="label" style="color:${color}">${score}</div>
    </div>`;
  }

  /* ── Screen management ────────────────────────────────────── */
  function showScreen(name) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    const el = $(`screen-${name}`);
    if (el) el.classList.add('active');
    state.screen = name;
  }

  /* ══ AUTH ═══════════════════════════════════════════════════ */
  function switchAuthTab(tab) {
    ['login','signup','reset'].forEach(t => {
      $(`form-${t}`).classList.toggle('hidden', t !== tab);
      const btn = $(`tab-${t}`);
      if (btn) btn.classList.toggle('active', t === tab);
    });
    $('tab-login').classList.toggle('active', tab === 'login');
    $('tab-signup').classList.toggle('active', tab === 'signup');
    $('auth-alert').style.display = 'none';
  }

  async function login() {
    const user = $('login-user').value.trim();
    const pass = $('login-pass').value;
    if (!user || !pass) return showAlert('auth-alert', 'Please fill all fields.');
    setLoading('btn-login', true, 'Login');
    const data = await apiFetch('/api/login', { method:'POST', body: JSON.stringify({ username: user, password: pass }) });
    setLoading('btn-login', false, 'Login');
    if (!data.success) return showAlert('auth-alert', data.message);
    state.username = user;
    showAlert('auth-alert', 'Login successful!', 'success');
    setTimeout(() => checkStatusAndNavigate(), 600);
  }

  async function signup() {
    const user  = $('signup-user').value.trim();
    const pass  = $('signup-pass').value;
    const pass2 = $('signup-pass2').value;
    if (!user || !pass || !pass2) return showAlert('auth-alert', 'Please fill all fields.');
    setLoading('btn-signup', true, 'Create Account');
    const data = await apiFetch('/api/signup', { method:'POST', body: JSON.stringify({ username: user, password: pass, confirm_password: pass2 }) });
    setLoading('btn-signup', false, 'Create Account');
    if (!data.success) return showAlert('auth-alert', data.message);
    state.username = user;
    showAlert('auth-alert', 'Account created!', 'success');
    setTimeout(() => showScreen('connect'), 800);
  }

  async function resetPassword() {
    const user  = $('reset-user').value.trim();
    const pass  = $('reset-pass').value;
    const pass2 = $('reset-pass2').value;
    if (!user || !pass || !pass2) return showAlert('auth-alert', 'Please fill all fields.');
    setLoading('btn-reset', true, 'Reset Password');
    const data = await apiFetch('/api/reset-password', { method:'POST', body: JSON.stringify({ username: user, new_password: pass, confirm_new_password: pass2 }) });
    setLoading('btn-reset', false, 'Reset Password');
    showAlert('auth-alert', data.message, data.success ? 'success' : 'error');
    if (data.success) setTimeout(() => switchAuthTab('login'), 1200);
  }

  async function checkStatusAndNavigate() {
    const data = await apiFetch('/api/status');
    if (!data.authenticated) { showScreen('auth'); return; }
    state.username     = data.username;
    state.emailAddress = data.email_address;

    if (data.email_connected) {
      $('btn-skip-connect').style.display = 'inline';
    }

    if (data.scan_status === 'complete') {
      // We already have scan data — reload preferences form or dashboard
      if (data.has_preferences) {
        await loadAndShowDashboard();
      } else {
        await loadScanAnalysis();
        showScreen('preferences');
      }
    } else if (data.email_connected) {
      showScreen('connect');
    } else {
      showScreen('connect');
    }
    $('dash-email-label').textContent = state.emailAddress;
  }

  /* ══ CONNECT ════════════════════════════════════════════════ */
  function selectProvider(prov) {
    state.provider = prov;
    document.querySelectorAll('.provider-btn').forEach(b => b.classList.remove('selected'));
    $(`prov-${prov}`).classList.add('selected');
    $('custom-fields').classList.toggle('hidden', prov !== 'custom');
  }

  async function connectEmail() {
    const email    = $('con-email').value.trim();
    const password = $('con-pass').value;
    if (!email || !password) return showAlert('connect-alert', 'Email and password required.');
    state.emailCount = parseInt($('con-email-count').value) || 100;
    setLoading('btn-connect', true, 'Connect & Continue');
    const payload = {
      email_address: email, email_password: password,
      provider: state.provider,
      custom_host: $('con-host') ? $('con-host').value : '',
      custom_port: $('con-port') ? parseInt($('con-port').value) : 993,
    };
    const data = await apiFetch('/api/connect-email', { method:'POST', body: JSON.stringify(payload) });
    setLoading('btn-connect', false, 'Connect & Continue');
    if (!data.success) return showAlert('connect-alert', data.message);
    state.emailAddress = email;
    $('dash-email-label').textContent = email;
    showAlert('connect-alert', 'Connected! Fetching ' + state.emailCount + ' emails...', 'success');
    setTimeout(() => startScan(), 800);
  }

  /* ══ SCANNING ═══════════════════════════════════════════════ */
  async function startScan() {
    showScreen('scanning');
    $('scan-counter').textContent = '0';
    $('scan-progress-bar').style.width = '0%';
    $('scan-cat-pills').innerHTML = '';
    $('scan-subtitle').textContent = 'Fetching ' + state.emailCount + ' emails from inbox...';

    const data = await apiFetch('/api/start-scan', {
      method: 'POST',
      body: JSON.stringify({ max_emails: state.emailCount }),
    });
    if (!data.success) {
      showAlert('connect-alert', data.message);
      showScreen('connect');
      return;
    }
    pollScanProgress();
  }

  function pollScanProgress() {
    if (state.scanPollId) clearInterval(state.scanPollId);
    state.scanPollId = setInterval(async () => {
      const data = await apiFetch('/api/scan-progress');
      if (!data.success) return;

      $('scan-counter').textContent = data.fetched;
      $('scan-progress-bar').style.width = (data.total ? data.pct : 15) + '%';

      if (data.status === 'scanning') {
        $('scan-subtitle').textContent = data.total
          ? `Fetched ${data.fetched} of ${data.total} emails…`
          : 'Fetching emails…';
      }

      if (data.status === 'complete') {
        clearInterval(state.scanPollId);
        $('scan-subtitle').textContent = 'Analysis complete!';
        $('scan-progress-bar').style.width = '100%';
        await loadScanAnalysis();
        setTimeout(() => showScreen('preferences'), 900);
      }

      if (data.status === 'error') {
        clearInterval(state.scanPollId);
        $('scan-subtitle').textContent = 'Error: ' + data.error;
      }
    }, 1000);
  }

  async function loadScanAnalysis() {
    const data = await apiFetch('/api/scan-analysis');
    if (!data.success) return;
    state.analysis = data.analysis;
    buildPreferenceForm(data.analysis);

    // Show detected categories as pills during scan screen
    const pills = $('scan-cat-pills');
    pills.innerHTML = '';
    const cats = data.analysis.category_counts || {};
    Object.entries(cats).forEach(([cat, count]) => {
      const pill = document.createElement('div');
      pill.className = 'scan-cat-pill';
      pill.textContent = `${getCatEmoji(cat)} ${count}`;
      pills.appendChild(pill);
    });
  }

  /* ══ PREFERENCES ════════════════════════════════════════════ */
  function buildPreferenceForm(analysis) {
    if (!analysis) return;
    const cats = analysis.category_counts || {};
    const senders = analysis.top_senders || [];

    // Priority grid
    const grid = $('pref-priority-grid');
    grid.innerHTML = '';
    Object.entries(cats).sort((a,b) => b[1]-a[1]).forEach(([cat, count]) => {
      const div = document.createElement('label');
      div.className = 'cat-item';
      div.innerHTML = `
        <input type="checkbox" class="prio-check" data-cat="${cat.toLowerCase()}" ${count > 5 ? 'checked' : ''}/>
        <div class="cat-item-info">
          <div class="cat-item-name">${getCatEmoji(cat)}</div>
          <div class="cat-item-count">${count} emails</div>
        </div>`;
      grid.appendChild(div);
    });

    // Action table
    const tbody = $('pref-action-table');
    tbody.innerHTML = '';
    const actions = ['ACT_NOW','NEEDS_REPLY','FYI','IGNORE','DELETE','BLOCK'];
    const defaultActions = {
      SPAM:'DELETE', FINANCIAL:'ACT_NOW', PROFESSIONAL:'ACT_NOW',
      EDUCATIONAL:'NEEDS_REPLY', TRAVEL:'FYI', HEALTHCARE:'ACT_NOW',
      GOVERNMENT:'ACT_NOW', TRANSACTIONAL:'FYI', PROMOTIONAL:'IGNORE',
      SOCIAL:'FYI', SYSTEM:'FYI', COMMUNITY:'FYI', SERVICE:'FYI', PERSONAL:'NEEDS_REPLY',
    };
    Object.keys(cats).forEach(cat => {
      const def = defaultActions[cat] || 'FYI';
      const opts = actions.map(a => `<option value="${a}" ${a===def?'selected':''}>${a.replace('_',' ')}</option>`).join('');
      tbody.innerHTML += `<tr>
        <td><div class="cat-name">${getCatEmoji(cat)}</div></td>
        <td><select class="action-sel" data-cat="${cat.toLowerCase()}">${opts}</select></td>
      </tr>`;
    });

    // Sender list
    const sl = $('pref-sender-list');
    sl.innerHTML = '';
    senders.slice(0,15).forEach(s => {
      const chip = document.createElement('div');
      chip.className = 'sender-chip';
      chip.dataset.sender = s.email;
      chip.innerHTML = `${s.email} <span class="sc-count">×${s.count}</span>`;
      chip.onclick = () => chip.classList.toggle('selected');
      sl.appendChild(chip);
    });

    // Custom labels
    const labelGrid = $('pref-labels');
    labelGrid.innerHTML = '';
    Object.keys(cats).forEach(cat => {
      const pair = document.createElement('div');
      pair.className = 'label-pair';
      pair.innerHTML = `<span class="orig">${getCatEmoji(cat)}</span><input type="text" class="label-inp" data-cat="${cat.toLowerCase()}" placeholder="e.g. Office Stuff"/>`;
      labelGrid.appendChild(pair);
    });

    // Pref steps indicator
    const steps = $('pref-steps');
    steps.innerHTML = Array(8).fill(0).map((_,i) => `<div class="pref-step ${i===0?'done':''}"></div>`).join('');
  }

  function selectRadio(el, key) {
    const parent = el.parentElement;
    parent.querySelectorAll('.radio-pill').forEach(p => p.classList.remove('selected'));
    el.classList.add('selected');
    state.radios[key] = el.dataset.val;
  }

  async function applyPreferences() {
    setLoading('btn-apply-prefs', true, 'Apply & View Inbox →');

    const prefs = gatherPreferences();
    state.preferences = prefs;

    const data = await apiFetch('/api/reprocess', { method: 'POST', body: JSON.stringify(prefs) });
    setLoading('btn-apply-prefs', false, 'Apply & View Inbox →');

    if (!data.success) {
      alert(data.message);
      return;
    }

    state.emails    = data.emails || [];
    state.analysis  = data.analysis;
    renderDashboard(data);
    showScreen('dashboard');
  }

  function gatherPreferences() {
    const priority_preferences = {};
    document.querySelectorAll('.prio-check').forEach(cb => {
      priority_preferences[cb.dataset.cat] = cb.checked;
    });

    const action_preferences = {};
    document.querySelectorAll('.action-sel').forEach(sel => {
      action_preferences[sel.dataset.cat] = sel.value;
    });

    const important_senders = [];
    document.querySelectorAll('.sender-chip.selected').forEach(chip => {
      important_senders.push(chip.dataset.sender);
    });

    const custom_labels = {};
    document.querySelectorAll('.label-inp').forEach(inp => {
      if (inp.value.trim()) custom_labels[inp.dataset.cat] = inp.value.trim();
    });

    return {
      priority_preferences,
      action_preferences,
      important_senders,
      custom_labels,
      life_mode:               state.radios.life_mode,
      fraud_sensitivity:       state.radios.fraud_sensitivity,
      notification_preference: state.radios.notification_preference,
      summary_preference:      state.radios.summary_preference,
      task_extraction:         $('tog-tasks').checked,
      focus_mode:              $('tog-focus').checked,
      ai_behavior: {
        allow_scanning:     $('tog-scanning').checked,
        allow_learning:     $('tog-learning').checked,
        allow_auto_actions: $('tog-auto').checked,
      },
    };
  }

  /* ══ DASHBOARD ══════════════════════════════════════════════ */
  function renderDashboard(data) {
    state.emails = data.emails || [];
    state.analysis = data.analysis || state.analysis;

    const analysis = state.analysis || {};
    $('stat-total').querySelector('.dash-stat-num').textContent  = analysis.total || state.emails.length;
    $('stat-urgent').querySelector('.dash-stat-num').textContent = analysis.urgent_count || 0;
    $('stat-fraud').querySelector('.dash-stat-num').textContent  = analysis.fraud_count || 0;

    buildSidebar(analysis.category_counts || {});
    applyFilter(state.currentFilter);
    renderAnalytics(analysis);
    loadTasks();
  }

  function buildSidebar(cats) {
    $('sf-all-count').textContent = state.emails.length;
    const sb = $('sidebar-cats');
    sb.innerHTML = '';
    Object.entries(cats).sort((a,b)=>b[1]-a[1]).forEach(([cat, count]) => {
      const div = document.createElement('div');
      div.className = 'sidebar-item';
      div.id = `sf-${cat.toLowerCase()}`;
      div.innerHTML = `${getCatEmoji(cat)} <span class="si-badge">${count}</span>`;
      div.onclick = () => filterCat(cat.toLowerCase());
      sb.appendChild(div);
    });
  }

  function filterCat(filter) {
    state.currentFilter = filter;
    document.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));
    const target = filter === 'all' ? $('sf-all') : filter === 'fraud' ? $('sf-fraud') : filter === 'urgent' ? $('sf-urgent') : $(`sf-${filter}`);
    if (target) target.classList.add('active');
    applyFilter(filter);
  }

  function applyFilter(filter) {
    let list = state.emails;
    if (filter === 'fraud')  list = list.filter(e => e.ai?.is_fraud);
    else if (filter === 'urgent') list = list.filter(e => e.ai?.priority_score >= 75);
    else if (filter !== 'all') list = list.filter(e => (e.ai?.category || '').toLowerCase() === filter);

    // Also respect focus mode
    if (state.preferences?.focus_mode) list = list.filter(e => !e.ai?.focus_hidden);

    state.filteredEmails = list;
    renderEmailList(list);
  }

  function searchEmails(query) {
    const q = query.toLowerCase();
    let list = state.emails;
    if (q) list = list.filter(e =>
      (e.sender||'').toLowerCase().includes(q) ||
      (e.subject||'').toLowerCase().includes(q) ||
      (e.ai?.summary||'').toLowerCase().includes(q)
    );
    state.filteredEmails = list;
    renderEmailList(list);
  }

  function sortEmails(by) {
    let list = [...state.filteredEmails];
    if (by === 'priority') list.sort((a,b) => (b.ai?.priority_score||0) - (a.ai?.priority_score||0));
    else if (by === 'sender') list.sort((a,b) => (a.sender||'').localeCompare(b.sender||''));
    renderEmailList(list);
  }

  function renderEmailList(emails) {
    const container = $('email-list');
    const empty     = $('empty-state');
    container.innerHTML = '';

    if (!emails.length) {
      empty.classList.remove('hidden');
      return;
    }
    empty.classList.add('hidden');

    emails.forEach(em => {
      const ai       = em.ai || {};
      const priority = ai.priority_score || 0;
      const isHigh   = priority >= 75;
      const cat      = ai.custom_label || ai.category || '';
      const action   = ai.suggested_action || 'FYI';
      const avatar   = (em.sender || '?')[0].toUpperCase();

      const card = document.createElement('div');
      card.className = `email-card${ai.is_fraud?' fraud':''} ${isHigh&&!ai.is_fraud?'high-priority':''}`;
      card.innerHTML = `
        <div class="email-card-top">
          <div class="email-avatar">${avatar}</div>
          <div class="email-meta">
            <div class="email-from">${escHtml(em.sender||'')}</div>
            <div class="email-subject">${escHtml(em.subject||'')}</div>
          </div>
          <div class="email-date">${em.date||''}</div>
        </div>
        <div class="email-card-mid">${escHtml((ai.summary||'').substring(0,140))}${(ai.summary||'').length>140?'…':''}</div>
        <div class="email-card-bot">
          <span class="badge-cat">${escHtml(cat)}</span>
          <span class="badge-action ${action}">${action.replace('_',' ')}</span>
          ${ai.is_fraud ? `<span class="badge-fraud">🚨 FRAUD ${Math.round((ai.fraud_probability||0)*100)}%</span>` : ''}
          ${ai.sender_importance ? '<span class="badge-important">⭐ VIP</span>' : ''}
          <div class="priority-ring-wrap">${buildPriorityRing(priority)}</div>
        </div>
        <div class="email-actions-bar">
          <button class="email-action-btn" onclick="applyAction(event,'${em.id}','ACT_NOW')">⚡ ACT</button>
          <button class="email-action-btn" onclick="applyAction(event,'${em.id}','NEEDS_REPLY')">💬 Reply</button>
          <button class="email-action-btn" onclick="applyAction(event,'${em.id}','IGNORE')">🙈 Ignore</button>
          <button class="email-action-btn del" onclick="applyAction(event,'${em.id}','DELETE')">🗑️ Delete</button>
          <button class="email-action-btn del" onclick="applyAction(event,'${em.id}','BLOCK')">🚫 Block</button>
          ${(ai.extracted_tasks||[]).length ? `<button class="email-action-btn" onclick="showTasks(event,'${em.id}')">✅ Tasks (${ai.extracted_tasks.length})</button>` : ''}
        </div>`;
      card.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON') return;
        openEmailModal(em);
      });
      container.appendChild(card);
    });
  }

  function escHtml(s) {
    return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  /* ══ EMAIL ACTIONS ══════════════════════════════════════════ */
  async function applyAction(e, emailId, action) {
    e.stopPropagation();
    const data = await apiFetch('/api/apply-action', { method:'POST', body: JSON.stringify({ email_id: emailId, action }) });
    if (!data.success) { alert(data.message); return; }
    // Optimistically update local state
    const em = state.emails.find(x => x.id === emailId);
    if (em) em.ai = { ...em.ai, suggested_action: action };
    applyFilter(state.currentFilter);
  }

  /* ══ EMAIL MODAL ════════════════════════════════════════════ */
  function openEmailModal(em) {
    const ai = em.ai || {};
    const tasks = (ai.extracted_tasks || []).map(t => `<li style="color:var(--text-2);font-size:13px;margin-bottom:4px;">${escHtml(t)}</li>`).join('');
    const deadlines = (ai.deadlines || []).map(d => `<div style="font-size:12px;color:${d.is_overdue?'var(--danger)':'var(--warning)'};margin-bottom:4px;">⏰ ${escHtml(d.task)} — ${d.deadline}</div>`).join('');
    const explanation = (ai.explanation || []).slice(-5).map(e => `<div style="font-size:12px;color:var(--text-2);margin-bottom:3px;">• ${escHtml(e)}</div>`).join('');

    $('modal-content').innerHTML = `
      <div style="margin-bottom:16px;">
        <div style="font-size:18px;font-weight:700;margin-bottom:4px;">${escHtml(em.subject||'')}</div>
        <div style="font-size:13px;color:var(--text-2);">${escHtml(em.sender||'')} &bull; ${em.date||''}</div>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;">
        <span class="badge-cat">${getCatEmoji(ai.category||'')}</span>
        <span class="badge-action ${ai.suggested_action||'FYI'}">${(ai.suggested_action||'FYI').replace('_',' ')}</span>
        ${ai.is_fraud?`<span class="badge-fraud">🚨 FRAUD ${Math.round((ai.fraud_probability||0)*100)}%</span>`:''}
        ${buildPriorityRing(ai.priority_score||0)}
      </div>
      <div style="background:var(--surface);border-radius:8px;padding:14px;margin-bottom:16px;">
        <div style="font-size:11px;color:var(--text-3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">AI Summary</div>
        <div style="font-size:14px;line-height:1.6;">${escHtml(ai.summary||'No summary available.')}</div>
      </div>
      ${tasks ? `<div style="margin-bottom:14px;"><div style="font-size:11px;color:var(--text-3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">Extracted Tasks</div><ul style="padding-left:18px;">${tasks}</ul></div>` : ''}
      ${deadlines ? `<div style="margin-bottom:14px;"><div style="font-size:11px;color:var(--text-3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">Deadlines</div>${deadlines}</div>` : ''}
      ${explanation ? `<div><div style="font-size:11px;color:var(--text-3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px;">AI Reasoning</div>${explanation}</div>` : ''}`;
    $('email-modal').classList.add('open');
  }

  function closeModal() {
    $('email-modal').classList.remove('open');
  }

  /* ══ ANALYTICS ══════════════════════════════════════════════ */
  function renderAnalytics(analysis) {
    if (!analysis) return;
    const grid = $('an-stats-grid');
    grid.innerHTML = `
      <div class="an-card"><div class="an-card-num">${analysis.total||0}</div><div class="an-card-label">Total Emails</div></div>
      <div class="an-card"><div class="an-card-num" style="color:var(--danger)">${analysis.fraud_count||0}</div><div class="an-card-label">Fraud / Spam</div></div>
      <div class="an-card"><div class="an-card-num" style="color:var(--warning)">${analysis.urgent_count||0}</div><div class="an-card-label">Urgent (≥75)</div></div>
      <div class="an-card"><div class="an-card-num" style="color:var(--accent)">${analysis.spam_pct||0}%</div><div class="an-card-label">Spam Rate</div></div>
      <div class="an-card"><div class="an-card-num" style="color:var(--warning)">${analysis.promo_pct||0}%</div><div class="an-card-label">Promotions</div></div>
      <div class="an-card"><div class="an-card-num" style="color:var(--text-2)">${analysis.ignored_pct||0}%</div><div class="an-card-label">Ignored</div></div>`;

    const cats = Object.entries(analysis.category_counts || {}).sort((a,b)=>b[1]-a[1]);
    const total = analysis.total || 1;
    const colors = ['#7c3aed','#06b6d4','#10b981','#f59e0b','#ef4444','#8b5cf6','#0ea5e9','#34d399'];

    const charts = $('an-charts');
    charts.innerHTML = '';

    // Category bars
    const catDiv = document.createElement('div');
    catDiv.innerHTML = '<div style="font-size:13px;font-weight:600;margin-bottom:14px;color:var(--text)">📊 Category Breakdown</div>';
    cats.forEach(([cat, count], i) => {
      const pct = Math.round(count / total * 100);
      const col = colors[i % colors.length];
      catDiv.innerHTML += `
        <div class="an-bar-label"><span>${getCatEmoji(cat)}</span><span style="color:var(--text)">${count}</span></div>
        <div class="an-bar-wrap"><div class="an-bar-fill" style="width:${pct}%;background:${col}"></div></div>`;
    });
    charts.appendChild(catDiv);

    // Action distribution
    const actions = Object.entries(analysis.action_counts || {}).sort((a,b)=>b[1]-a[1]);
    const actDiv = document.createElement('div');
    actDiv.innerHTML = '<div style="font-size:13px;font-weight:600;margin-bottom:14px;color:var(--text)">⚡ Action Distribution</div>';
    const actColors = {ACT_NOW:'#f59e0b', NEEDS_REPLY:'#06b6d4', FYI:'#10b981', IGNORE:'#475569', DELETE:'#ef4444', BLOCK:'#dc2626'};
    actions.forEach(([act, count]) => {
      const pct  = Math.round(count / total * 100);
      const col  = actColors[act] || '#7c3aed';
      actDiv.innerHTML += `
        <div class="an-bar-label"><span>${act.replace('_',' ')}</span><span style="color:var(--text)">${count}</span></div>
        <div class="an-bar-wrap"><div class="an-bar-fill" style="width:${pct}%;background:${col}"></div></div>`;
    });
    charts.appendChild(actDiv);
  }

  /* ══ TASKS ══════════════════════════════════════════════════ */
  async function loadTasks() {
    const data = await apiFetch('/api/tasks');
    if (!data.success) return;
    $('stat-tasks').querySelector('.dash-stat-num').textContent = data.pending_count;
    const list   = $('task-list');
    const empty  = $('task-empty');
    list.innerHTML = '';
    const tasks = data.tasks || [];
    if (!tasks.length) { empty.classList.remove('hidden'); return; }
    empty.classList.add('hidden');

    tasks.forEach(t => {
      const div = document.createElement('div');
      const done = t.status === 'completed';
      div.style.cssText = `background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin-bottom:8px;display:flex;align-items:center;gap:12px;`;
      div.innerHTML = `
        <div style="flex:1;">
          <div style="font-size:14px;font-weight:500;${done?'text-decoration:line-through;color:var(--text-2)':''}">${escHtml(t.task)}</div>
          ${t.deadline ? `<div style="font-size:12px;color:var(--warning);margin-top:3px;">⏰ ${t.deadline}</div>` : ''}
        </div>
        ${!done ? `<button class="btn-success btn" onclick="completeTask('${t.id}')">✓ Done</button>` : '<span style="color:var(--success);font-size:13px;">✓ Done</span>'}`;
      list.appendChild(div);
    });
  }

  async function completeTask(taskId) {
    const data = await apiFetch('/api/tasks/complete', { method:'POST', body: JSON.stringify({ task_id: taskId }) });
    if (data.success) loadTasks();
  }

  /* ══ OPENENV AGENT ══════════════════════════════════════════ */
  async function agentReset() {
    const data = await apiFetch('/api/openenv/reset', { method:'POST', body:'{}' });
    if (!data.success) { alert(data.message); return; }
    renderAgentState(data.state);
  }

  async function agentStep(action) {
    const data = await apiFetch('/api/openenv/step', { method:'POST', body: JSON.stringify({ action }) });
    if (!data.success) { alert(data.message); return; }
    renderAgentState(data.state);
    const statsDiv = $('agent-stats');
    const { reward, total_reward } = data.info || {};
    statsDiv.innerHTML = `
      <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:12px;">
        <div><div style="font-size:22px;font-weight:800;color:${reward>=0?'var(--success)':'var(--danger)'}">${reward>=0?'+':''}${reward}</div><div style="font-size:11px;color:var(--text-2)">Reward</div></div>
        <div><div style="font-size:22px;font-weight:800;color:var(--primary-lit)">${total_reward}</div><div style="font-size:11px;color:var(--text-2)">Total Reward</div></div>
        <div><div style="font-size:22px;font-weight:800;color:var(--accent)">${data.state.inbox?.processed||0}/${data.state.inbox?.total||0}</div><div style="font-size:11px;color:var(--text-2)">Processed</div></div>
        <div><div style="font-size:22px;font-weight:800;color:var(--text-2)">${Math.round(data.state.stats?.avg_reward||0)}</div><div style="font-size:11px;color:var(--text-2)">Avg Reward</div></div>
      </div>
      ${data.done ? '<div style="background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.2);border-radius:8px;padding:12px;color:var(--success);font-size:13px;">✅ All emails processed! Reset agent to start again.</div>' : ''}`;
  }

  function renderAgentState(s) {
    const em = s.current_email;
    const box = $('agent-email-info');
    if (!em) {
      box.innerHTML = '<div style="color:var(--text-2);font-size:13px;">All emails processed or agent not started.</div>';
      return;
    }
    box.innerHTML = `
      <div style="font-size:15px;font-weight:600;margin-bottom:4px;">${escHtml(em.subject||'')}</div>
      <div style="font-size:13px;color:var(--text-2);margin-bottom:10px;">${escHtml(em.sender||'')}</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <span class="badge-cat">${getCatEmoji(em.category||'')}</span>
        <span class="badge-action ${em.suggested_action||'FYI'}">${(em.suggested_action||'FYI').replace('_',' ')}</span>
        ${em.is_fraud?`<span class="badge-fraud">🚨 FRAUD ${Math.round((em.fraud_probability||0)*100)}%</span>`:''}
        ${buildPriorityRing(em.priority_score||0)}
      </div>
      <div style="margin-top:10px;font-size:12px;color:var(--text-2);">${escHtml(em.summary||'')}</div>
      <div style="margin-top:10px;display:flex;gap:12px;font-size:12px;color:var(--text-3);">
        <span>Remaining: <b style="color:var(--text)">${s.inbox?.remaining||0}</b></span>
        <span>Progress: <b style="color:var(--primary-lit)">${s.inbox?.progress_pct||0}%</b></span>
      </div>`;
  }

  /* ══ TABS ════════════════════════════════════════════════════ */
  function switchTab(tab) {
    state.currentTab = tab;
    document.querySelectorAll('.dash-tab').forEach((t,i) => {
      const tabs = ['emails','analytics','tasks','agent'];
      t.classList.toggle('active', tabs[i] === tab);
    });
    ['emails','analytics','tasks','agent'].forEach(t => {
      const el = $(`tab-${t}`);
      if (el) el.classList.toggle('hidden', t !== tab);
    });
    if (tab === 'tasks')    loadTasks();
    if (tab === 'analytics') renderAnalytics(state.analysis);
    if (tab === 'agent')    loadAgentView();
  }

  async function loadAgentView() {
    const data = await apiFetch('/api/openenv/state');
    if (data.success) renderAgentState(data.state);
  }

  /* ══ RESCAN / PREFS ══════════════════════════════════════════ */
  function startRescan() {
    // Show the rescan modal with email count slider
    $('rescan-email-count').value = state.emailCount || 100;
    $('rescan-count-display').textContent = state.emailCount || 100;
    $('rescan-modal').classList.add('open');
  }

  function closeRescanModal() {
    $('rescan-modal').classList.remove('open');
  }

  async function confirmRescan() {
    state.emailCount = parseInt($('rescan-email-count').value) || 100;
    closeRescanModal();
    showScreen('scanning');
    $('scan-counter').textContent = '0';
    $('scan-progress-bar').style.width = '0%';
    $('scan-cat-pills').innerHTML = '';
    $('scan-subtitle').textContent = 'Fetching ' + state.emailCount + ' emails from inbox...';
    const data = await apiFetch('/api/start-scan', { method:'POST', body: JSON.stringify({ max_emails: state.emailCount }) });
    if (!data.success) { alert(data.message); showScreen('dashboard'); return; }
    pollScanProgress();
  }

  async function showPreferences() {
    const data = await apiFetch('/api/scan-analysis');
    if (data.success && data.analysis) buildPreferenceForm(data.analysis);
    showScreen('preferences');
  }

  async function loadAndShowDashboard() {
    // Load saved preferences and reprocess
    const prefData = await apiFetch('/api/preferences');
    const prefs = prefData.preferences || {};
    state.preferences = prefs;
    const data = await apiFetch('/api/reprocess', { method:'POST', body: JSON.stringify(prefs) });
    if (data.success) {
      state.emails   = data.emails || [];
      state.analysis = data.analysis;
      renderDashboard(data);
      showScreen('dashboard');
    } else {
      // Fallback: show connect
      showScreen('connect');
    }
  }

  /* ══ LOGOUT ══════════════════════════════════════════════════ */
  async function logout() {
    await apiFetch('/api/logout', { method:'POST' });
    state.emails    = [];
    state.analysis  = null;
    state.username  = '';
    showScreen('auth');
  }

  /* ══ GLOBAL EXPOSE ══════════════════════════════════════════ */
  // Expose global for inline onclick handlers
  window.applyAction   = (e, id, action) => applyAction(e, id, action);
  window.completeTask  = id => completeTask(id);

  /* ══ INIT ════════════════════════════════════════════════════ */
  document.addEventListener('DOMContentLoaded', async () => {
    // Close modals on overlay click
    $('email-modal').addEventListener('click', e => { if (e.target === $('email-modal')) closeModal(); });
    $('rescan-modal').addEventListener('click', e => { if (e.target === $('rescan-modal')) closeRescanModal(); });
    // Check session on load
    try { await checkStatusAndNavigate(); } catch { showScreen('auth'); }
  });

  return {
    showScreen, switchAuthTab, login, signup, resetPassword,
    selectProvider, connectEmail,
    selectRadio, applyPreferences,
    filterCat, searchEmails, sortEmails,
    closeModal, closeRescanModal, confirmRescan,
    switchTab,
    agentReset, agentStep,
    startRescan, showPreferences, logout,
  };
})();
