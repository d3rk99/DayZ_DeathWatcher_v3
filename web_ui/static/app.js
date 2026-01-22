const toast = document.getElementById('toast');
const statusLabel = document.getElementById('server-status');

const tabs = document.querySelectorAll('.tab');
const panels = document.querySelectorAll('.tab-panel');

tabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    tabs.forEach((btn) => btn.classList.remove('active'));
    panels.forEach((panel) => panel.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(tab.dataset.tab).classList.add('active');
  });
});

const showToast = (message, isError = false) => {
  toast.textContent = message;
  toast.classList.add('show');
  toast.style.border = isError ? '1px solid #ff5959' : '1px solid #2a3536';
  setTimeout(() => toast.classList.remove('show'), 2500);
};

const formatEntries = (entries) => (entries === undefined ? '—' : entries);

const formatFileCard = (title, info) => {
  const status = info.exists ? 'Online' : 'Missing';
  const statusClass = info.exists ? 'ok' : 'warn';
  return `
    <div class="card">
      <h3>${title}</h3>
      <p>${info.path || 'Not configured'}</p>
      <div class="meta">
        <span class="badge ${statusClass}">${status}</span>
        <span class="badge">Entries: ${formatEntries(info.entries)}</span>
        <span class="badge">Updated: ${info.modified || '—'}</span>
      </div>
    </div>
  `;
};

const formatOverviewItem = (label, info) => {
  const status = info.exists ? 'Online' : 'Missing';
  const statusClass = info.exists ? 'ok' : 'warn';
  return `
    <li>
      <div>
        <strong>${label}</strong>
        <span class="muted">${info.path || 'Not configured'}</span>
      </div>
      <div class="meta">
        <span class="badge ${statusClass}">${status}</span>
        <span class="badge">Entries: ${formatEntries(info.entries)}</span>
        <span class="badge">Updated: ${info.modified || '—'}</span>
      </div>
    </li>
  `;
};

const loadOverview = async () => {
  const list = document.getElementById('overview-list');
  const botLogOutput = document.getElementById('bot-log-output');
  list.innerHTML = '';
  try {
    const response = await fetch('/api/overview');
    const data = await response.json();

    const items = [
      formatOverviewItem('User Database', data.userdata_db),
      formatOverviewItem('Whitelist', data.whitelist),
      formatOverviewItem('Blacklist', data.blacklist),
      formatOverviewItem('Death Watcher Deaths', data.death_watcher_deaths),
      formatOverviewItem('Syncer Whitelist', data.syncer.whitelist_sync),
      formatOverviewItem('Syncer Blacklist', data.syncer.blacklist_sync),
    ];

    list.innerHTML = items.join('');
    const logLines = data.bot_log?.lines?.length ? data.bot_log.lines.join('\n') : 'No bot logs yet.';
    botLogOutput.textContent = logLines;
  } catch (error) {
    showToast('Failed to load overview', true);
    botLogOutput.textContent = 'Unable to load bot logs.';
  }
};

const renderUsers = (users) => {
  const tbody = document.getElementById('users-table');
  tbody.innerHTML = '';
  if (users.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6">No users found.</td></tr>';
    return;
  }

  users.forEach((user) => {
    const row = document.createElement('tr');
    const statusClass = user.is_admin
      ? 'user-name admin'
      : user.is_alive
      ? 'user-name alive'
      : 'user-name dead';
    row.innerHTML = `
      <td><span class="${statusClass}">${user.username || 'Unknown'}</span><div class="muted">${user.user_id}</div></td>
      <td>${user.steam_id || '—'}</td>
      <td>${user.guid || '—'}</td>
      <td>
        <label class="toggle">
          <input type="checkbox" ${user.is_alive ? 'checked' : ''} data-action="alive" data-user="${user.user_id}" />
          Alive
        </label>
      </td>
      <td>
        <label class="toggle">
          <input type="checkbox" ${user.is_admin ? 'checked' : ''} data-action="admin" data-user="${user.user_id}" />
          Admin
        </label>
      </td>
      <td>
        <button class="ghost" data-action="delete" data-user="${user.user_id}">Delete</button>
      </td>
    `;
    tbody.appendChild(row);
  });
};

const loadUsers = async (query = '') => {
  const endpoint = query ? `/api/userdata/search?q=${encodeURIComponent(query)}` : '/api/userdata';
  try {
    const response = await fetch(endpoint);
    const data = await response.json();
    renderUsers(data.users || []);
  } catch (error) {
    showToast('Failed to load users', true);
  }
};

const updateUser = async (userId, payload) => {
  const response = await fetch(`/api/userdata/${userId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error('Update failed');
  }
  return response.json();
};

const deleteUser = async (userId) => {
  const response = await fetch(`/api/userdata/${userId}`, { method: 'DELETE' });
  if (!response.ok) {
    throw new Error('Delete failed');
  }
  return response.json();
};

const bindUserActions = () => {
  const table = document.getElementById('users-table');
  table.addEventListener('change', async (event) => {
    const target = event.target;
    if (target.tagName !== 'INPUT') return;
    const userId = target.dataset.user;
    const action = target.dataset.action;
    try {
      if (action === 'alive') {
        await updateUser(userId, { is_alive: target.checked ? 1 : 0 });
        showToast('Updated alive status');
      }
      if (action === 'admin') {
        await updateUser(userId, { is_admin: target.checked ? 1 : 0 });
        showToast('Updated admin status');
      }
    } catch (error) {
      showToast('Update failed', true);
    }
  });

  table.addEventListener('click', async (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    if (target.dataset.action !== 'delete') return;
    const userId = target.dataset.user;
    if (!confirm('Delete this user from the database?')) return;
    try {
      await deleteUser(userId);
      showToast('User deleted');
      loadUsers(document.getElementById('user-search').value);
    } catch (error) {
      showToast('Delete failed', true);
    }
  });
};

const renderLogs = (data) => {
  const grid = document.getElementById('logs-grid');
  const cards = [];

  if (data.death_watcher_deaths) {
    const status = data.death_watcher_deaths.exists ? 'ok' : 'warn';
    cards.push(`
      <div class="log-card">
        <h3>Death Watcher Deaths</h3>
        <p class="muted">${data.death_watcher_deaths.path}</p>
        <div class="meta">
          <span class="badge ${status}">${data.death_watcher_deaths.exists ? 'Available' : 'Missing'}</span>
          <span class="badge">Entries: ${data.death_watcher_deaths.entries ?? '—'}</span>
        </div>
      </div>
    `);
  }

  (data.log_paths || []).forEach((log) => {
    const status = log.exists ? 'ok' : 'warn';
    const lines = log.lines?.length ? log.lines.join('\n') : 'No log data yet.';
    cards.push(`
      <div class="log-card">
        <h3>Log Stream</h3>
        <p class="muted">${log.source_path || log.path}</p>
        ${log.resolved_path ? `<p class="muted">Resolved: ${log.resolved_path}</p>` : ''}
        <div class="meta">
          <span class="badge ${status}">${log.exists ? 'Streaming' : 'Missing'}</span>
        </div>
        <pre>${lines}</pre>
      </div>
    `);
  });

  if (cards.length === 0) {
    cards.push('<div class="card">No log paths configured.</div>');
  }

  grid.innerHTML = cards.join('');
};

const loadLogs = async () => {
  try {
    const response = await fetch('/api/logs');
    const data = await response.json();
    renderLogs(data);
  } catch (error) {
    showToast('Failed to load logs', true);
  }
};

const renderSync = (data) => {
  const header = document.getElementById('sync-header');
  const columns = document.getElementById('sync-columns');
  header.innerHTML = `
    ${formatFileCard('Syncer Whitelist', data.whitelist_sync)}
    ${formatFileCard('Syncer Blacklist', data.blacklist_sync)}
  `;

  const maxColumns = Math.max(data.whitelist_servers.length, data.blacklist_servers.length);
  const columnCards = [];
  for (let i = 0; i < maxColumns; i += 1) {
    const whitelistInfo = data.whitelist_servers[i];
    const blacklistInfo = data.blacklist_servers[i];
    columnCards.push(`
      <div class="sync-column">
        ${whitelistInfo ? formatFileCard(`Whitelist Server ${i + 1}`, whitelistInfo) : ''}
        ${blacklistInfo ? formatFileCard(`Blacklist Server ${i + 1}`, blacklistInfo) : ''}
      </div>
    `);
  }
  columns.innerHTML = columnCards.join('');
};

const loadSync = async () => {
  try {
    const response = await fetch('/api/sync');
    const data = await response.json();
    renderSync(data);
  } catch (error) {
    showToast('Failed to load sync status', true);
  }
};

const boot = async () => {
  statusLabel.textContent = 'Online';
  await loadOverview();
  await loadUsers();
  await loadLogs();
  await loadSync();
};

bindUserActions();

const searchInput = document.getElementById('user-search');
searchInput.addEventListener('input', (event) => {
  loadUsers(event.target.value);
});

const refreshUsers = document.getElementById('refresh-users');
refreshUsers.addEventListener('click', () => loadUsers(searchInput.value));

const refreshLogs = document.getElementById('refresh-logs');
refreshLogs.addEventListener('click', loadLogs);

const refreshSync = document.getElementById('refresh-sync');
refreshSync.addEventListener('click', loadSync);

boot();
