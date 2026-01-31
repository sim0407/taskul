(function () {
  const API = '';
  const STATUSES = ['Backlog', 'Todo', 'Doing', 'Review', 'Done'];

  const $ = (id) => document.getElementById(id);
  const viewProjects = $('view-projects');
  const viewBoard = $('view-board');
  const viewBlockers = $('view-blockers');
  const projectList = $('project-list');
  const boardLanes = $('board-lanes');
  const boardTitle = $('board-title');
  const blockersList = $('blockers-list');
  const toastEl = $('toast');
  const modalOverlay = $('modal-overlay');
  const modalTitle = $('modal-title');
  const modalBody = $('modal-body');
  const modalClose = $('modal-close');

  let currentProjectId = null;
  let currentProjectName = null;
  let lastBoard = null;

  function showView(view) {
    [viewProjects, viewBoard, viewBlockers].forEach(el => el.classList.add('hidden'));
    view.classList.remove('hidden');
  }

  function setBoardTitle(name) {
    boardTitle.textContent = name ? `: ${name}` : '';
  }

  function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }
  function escapeAttr(s) {
    return escapeHtml(s).replace(/"/g, '&quot;');
  }

  async function fetchJSON(path) {
    const r = await fetch(API + path);
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      const msg = err.detail ? (typeof err.detail === 'string' ? err.detail : err.detail.map(d => d.msg || JSON.stringify(d)).join(' ')) : r.status + ' ' + r.statusText;
      throw new Error(msg);
    }
    return r.json();
  }

  async function fetchPOST(path, body) {
    const r = await fetch(API + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      const msg = err.detail ? (typeof err.detail === 'string' ? err.detail : err.detail.map(d => d.msg || JSON.stringify(d)).join(' ')) : r.status + ' ' + r.statusText;
      throw new Error(msg);
    }
    return r.status === 204 ? null : r.json();
  }

  async function fetchPATCH(path, body) {
    const r = await fetch(API + path, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      const msg = err.detail ? (typeof err.detail === 'string' ? err.detail : err.detail.map(d => d.msg || JSON.stringify(d)).join(' ')) : r.status + ' ' + r.statusText;
      throw new Error(msg);
    }
    return r.json();
  }

  async function fetchDELETE(path) {
    const r = await fetch(API + path, { method: 'DELETE' });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      const msg = err.detail ? (typeof err.detail === 'string' ? err.detail : err.detail.map(d => d.msg || JSON.stringify(d)).join(' ')) : r.status + ' ' + r.statusText;
      throw new Error(msg);
    }
    return r.status === 204 ? null : r.json();
  }

  function showToast(message, isError = false) {
    toastEl.textContent = message;
    toastEl.classList.remove('hidden', 'error', 'success');
    toastEl.classList.add(isError ? 'error' : 'success');
    clearTimeout(toastEl._tid);
    toastEl._tid = setTimeout(() => toastEl.classList.add('hidden'), 4000);
  }

  function showModal(title, bodyHTML) {
    modalTitle.textContent = title;
    modalBody.innerHTML = bodyHTML;
    modalOverlay.classList.remove('hidden');
  }
  function closeModal() {
    modalOverlay.classList.add('hidden');
  }
  modalClose.addEventListener('click', closeModal);
  modalOverlay.addEventListener('click', (e) => { if (e.target === modalOverlay) closeModal(); });

  async function loadProjects() {
    projectList.innerHTML = '<li class="loading">読み込み中…</li>';
    try {
      const projects = await fetchJSON('/projects');
      if (projects.length === 0) {
        projectList.innerHTML = '<li class="hint">プロジェクトがありません。「新規作成」で追加できます。</li>';
        return;
      }
      projectList.innerHTML = projects.map(p =>
        `<li><a href="#" data-project-id="${p.id}" data-project-name="${escapeAttr(p.name)}">${escapeHtml(p.name)} (${p.id})</a></li>`
      ).join('');
      projectList.querySelectorAll('a').forEach(a => {
        a.addEventListener('click', (e) => {
          e.preventDefault();
          openBoard(a.dataset.projectId, a.dataset.projectName);
        });
      });
    } catch (e) {
      projectList.innerHTML = '<li class="error">読み込み失敗: ' + escapeHtml(e.message) + '</li>';
    }
  }

  function openNewProjectModal() {
    showModal('プロジェクト新規作成', `
      <form id="form-new-project" class="form">
        <div class="form-group">
          <label for="project-name">名前</label>
          <input type="text" id="project-name" name="name" required placeholder="プロジェクト名">
        </div>
        <div id="form-new-project-error" class="form-error hidden"></div>
        <div class="form-actions">
          <button type="button" class="btn-cancel" data-dismiss="modal">キャンセル</button>
          <button type="submit" class="btn-submit">作成</button>
        </div>
      </form>
    `);
    const form = modalBody.querySelector('#form-new-project');
    const errEl = modalBody.querySelector('#form-new-project-error');
    form.querySelector('[data-dismiss="modal"]').addEventListener('click', closeModal);
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = form.querySelector('#project-name').value.trim();
      if (!name) { errEl.textContent = '名前を入力してください'; errEl.classList.remove('hidden'); return; }
      errEl.classList.add('hidden');
      try {
        await fetchPOST('/projects', { name });
        showToast('プロジェクトを作成しました');
        closeModal();
        loadProjects();
      } catch (err) {
        errEl.textContent = err.message;
        errEl.classList.remove('hidden');
      }
    });
  }

  function openAddDependencyModal() {
    if (!lastBoard) {
      showToast('ボードを読み込んでから依存を追加してください', true);
      return;
    }
    const flat = STATUSES.flatMap(s => (lastBoard.lanes[s] || []).map(t => ({ id: t.id, title: t.title })));
    if (flat.length < 2) {
      showToast('依存を追加するにはタスクが2つ以上必要です', true);
      return;
    }
    const opt = (tid, label) => `<option value="${escapeAttr(tid)}">${escapeHtml(label)}</option>`;
    const fromOpts = flat.map(t => opt(t.id, t.id + ' ' + t.title)).join('');
    const toOpts = flat.map(t => opt(t.id, t.id + ' ' + t.title)).join('');
    showModal('依存を追加', `
      <p class="hint">「ブロックするタスク」が完了するまで「ブロックされるタスク」は進められません。サイクルは禁止です。</p>
      <form id="form-add-dependency" class="form">
        <div class="form-group">
          <label for="dep-from">ブロックするタスク (from)</label>
          <select id="dep-from" name="from_task_id" required>${fromOpts}</select>
        </div>
        <div class="form-group">
          <label for="dep-to">ブロックされるタスク (to)</label>
          <select id="dep-to" name="to_task_id" required>${toOpts}</select>
        </div>
        <div id="form-add-dependency-error" class="form-error hidden"></div>
        <div class="form-actions">
          <button type="button" class="btn-cancel" data-dismiss="modal">キャンセル</button>
          <button type="submit" class="btn-submit">追加</button>
        </div>
      </form>
    `);
    const form = modalBody.querySelector('#form-add-dependency');
    const errEl = modalBody.querySelector('#form-add-dependency-error');
    form.querySelector('[data-dismiss="modal"]').addEventListener('click', closeModal);
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const fromTaskId = form.querySelector('#dep-from').value;
      const toTaskId = form.querySelector('#dep-to').value;
      if (fromTaskId === toTaskId) {
        errEl.textContent = '同じタスクを選べません';
        errEl.classList.remove('hidden');
        return;
      }
      errEl.classList.add('hidden');
      try {
        await fetchPOST('/dependencies', { from_task_id: fromTaskId, to_task_id: toTaskId });
        showToast('依存を追加しました');
        closeModal();
        refreshBoard();
      } catch (err) {
        errEl.textContent = err.message;
        errEl.classList.remove('hidden');
      }
    });
  }

  function openNewTaskModal() {
    if (!currentProjectId) return;
    const statusOpts = STATUSES.map(s => `<option value="${s}">${s}</option>`).join('');
    showModal('タスク追加', `
      <form id="form-new-task" class="form">
        <div class="form-group">
          <label for="task-title">タイトル</label>
          <input type="text" id="task-title" name="title" required placeholder="タスクのタイトル">
        </div>
        <div class="form-group">
          <label for="task-status">ステータス</label>
          <select id="task-status" name="status">${statusOpts}</select>
        </div>
        <div id="form-new-task-error" class="form-error hidden"></div>
        <div class="form-actions">
          <button type="button" class="btn-cancel" data-dismiss="modal">キャンセル</button>
          <button type="submit" class="btn-submit">追加</button>
        </div>
      </form>
    `);
    const form = modalBody.querySelector('#form-new-task');
    const errEl = modalBody.querySelector('#form-new-task-error');
    form.querySelector('[data-dismiss="modal"]').addEventListener('click', closeModal);
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const title = form.querySelector('#task-title').value.trim();
      if (!title) { errEl.textContent = 'タイトルを入力してください'; errEl.classList.remove('hidden'); return; }
      errEl.classList.add('hidden');
      try {
        await fetchPOST('/tasks', { project_id: currentProjectId, title, status: form.querySelector('#task-status').value });
        showToast('タスクを追加しました');
        closeModal();
        refreshBoard();
      } catch (err) {
        errEl.textContent = err.message;
        errEl.classList.remove('hidden');
      }
    });
  }

  async function openBoard(projectId, projectName) {
    currentProjectId = projectId;
    currentProjectName = projectName || projectId;
    setBoardTitle(currentProjectName);
    boardLanes.innerHTML = '<div class="loading">ボード読み込み中…</div>';
    showView(viewBoard);
    try {
      const board = await fetchJSON('/projects/' + encodeURIComponent(projectId) + '/board');
      renderBoard(board);
    } catch (e) {
      boardLanes.innerHTML = '<div class="error">読み込み失敗: ' + escapeHtml(e.message) + '</div>';
    }
  }

  async function refreshBoard() {
    if (!currentProjectId) return;
    try {
      const board = await fetchJSON('/projects/' + encodeURIComponent(currentProjectId) + '/board');
      renderBoard(board);
    } catch (e) {
      showToast(e.message, true);
    }
  }

  function renderBoard(board) {
    lastBoard = board;
    const statuses = STATUSES;
    boardLanes.innerHTML = statuses.map(status => {
      const tasks = board.lanes[status] || [];
      const cards = tasks.map(t => renderCard(t, status));
      return `<div class="lane ${status}" data-status="${escapeAttr(status)}"><div class="lane-title">${escapeHtml(status)}</div><div class="lane-cards">${cards.join('')}</div></div>`;
    }).join('');
    boardLanes.querySelectorAll('.btn-card-done').forEach(btn => {
      btn.addEventListener('click', () => markDone(btn.dataset.taskId));
    });
    boardLanes.querySelectorAll('.card-move-select').forEach(sel => {
      sel.addEventListener('change', (e) => {
        const taskId = e.target.dataset.taskId;
        const status = e.target.value;
        if (status) moveTask(taskId, status, 'bottom');
      });
    });
    boardLanes.querySelectorAll('.btn-card-edit').forEach(btn => {
      btn.addEventListener('click', () => openEditTaskModal(btn.dataset.taskId));
    });
  }

  function renderCard(t, currentStatus) {
    const moveOpts = STATUSES.filter(s => s !== currentStatus).map(s => `<option value="${s}">→ ${s}</option>`).join('');
    const canDone = currentStatus !== 'Done';
    const actions = `
      <div class="card-actions">
        ${canDone ? `<button type="button" class="btn-card-done btn-done" data-task-id="${escapeAttr(t.id)}">完了</button>` : ''}
        <select class="card-move-select" data-task-id="${escapeAttr(t.id)}"><option value="">移動</option>${moveOpts}</select>
        <button type="button" class="btn-card-edit" data-task-id="${escapeAttr(t.id)}">編集</button>
      </div>
    `;
    return `<div class="card" data-task-id="${escapeAttr(t.id)}"><div class="card-id">${escapeHtml(t.id)}</div><div class="card-title">${escapeHtml(t.title)}</div>${actions}</div>`;
  }

  async function markDone(taskId) {
    try {
      await fetchPOST('/tasks/' + encodeURIComponent(taskId) + '/mark-done', {});
      showToast('タスクを完了にしました');
      refreshBoard();
    } catch (e) {
      showToast(e.message, true);
    }
  }

  async function moveTask(taskId, status, position) {
    try {
      await fetchPOST('/tasks/' + encodeURIComponent(taskId) + '/move', { status, position: position || 'bottom' });
      showToast('タスクを移動しました');
      refreshBoard();
    } catch (e) {
      showToast(e.message, true);
    }
  }

  function openEditTaskModal(taskId) {
    (async () => {
      let task;
      try {
        task = await fetchJSON('/tasks/' + encodeURIComponent(taskId));
      } catch (e) {
        showToast(e.message, true);
        return;
      }
      const statusOpts = STATUSES.map(s => `<option value="${s}" ${s === task.status ? 'selected' : ''}>${s}</option>`).join('');
      showModal('タスク編集', `
        <form id="form-edit-task" class="form">
          <div class="form-group">
            <label for="edit-title">タイトル</label>
            <input type="text" id="edit-title" name="title" value="${escapeAttr(task.title || '')}" required>
          </div>
          <div class="form-group">
            <label for="edit-description">説明</label>
            <textarea id="edit-description" name="description" rows="2">${escapeAttr(task.description || '')}</textarea>
          </div>
          <div class="form-group">
            <label for="edit-status">ステータス</label>
            <select id="edit-status" name="status">${statusOpts}</select>
          </div>
          <div class="form-group">
            <label for="edit-start-date">開始日 (YYYY-MM-DD)</label>
            <input type="text" id="edit-start-date" name="start_date" value="${escapeAttr(task.start_date || '')}" placeholder="YYYY-MM-DD">
          </div>
          <div class="form-group">
            <label for="edit-due-date">期限 (YYYY-MM-DD)</label>
            <input type="text" id="edit-due-date" name="due_date" value="${escapeAttr(task.due_date || '')}" placeholder="YYYY-MM-DD">
          </div>
          <div class="form-group">
            <label for="edit-estimate-hours">見積もり (時間)</label>
            <input type="number" id="edit-estimate-hours" name="estimate_hours" step="0.5" value="${task.estimate_hours != null ? escapeAttr(String(task.estimate_hours)) : ''}" placeholder="数値">
          </div>
          <div id="form-edit-task-error" class="form-error hidden"></div>
          <div class="form-actions">
            <button type="button" class="btn-cancel" data-dismiss="modal">キャンセル</button>
            <button type="submit" class="btn-submit">保存</button>
          </div>
        </form>
      `);
      const form = modalBody.querySelector('#form-edit-task');
      const errEl = modalBody.querySelector('#form-edit-task-error');
      form.querySelector('[data-dismiss="modal"]').addEventListener('click', closeModal);
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errEl.classList.add('hidden');
        const body = {
          title: form.querySelector('#edit-title').value.trim(),
          description: form.querySelector('#edit-description').value.trim() || null,
          status: form.querySelector('#edit-status').value,
          start_date: form.querySelector('#edit-start-date').value.trim() || null,
          due_date: form.querySelector('#edit-due-date').value.trim() || null,
          estimate_hours: (() => { const v = form.querySelector('#edit-estimate-hours').value.trim(); return v ? parseFloat(v) : null; })(),
        };
        try {
          await fetchPATCH('/tasks/' + encodeURIComponent(taskId), body);
          showToast('タスクを更新しました');
          closeModal();
          refreshBoard();
        } catch (err) {
          errEl.textContent = err.message;
          errEl.classList.remove('hidden');
        }
      });
    })();
  }

  async function showBlockers() {
    if (!currentProjectId) return;
    viewBlockers.classList.remove('hidden');
    viewBoard.classList.add('hidden');
    blockersList.innerHTML = '<li class="loading">読み込み中…</li>';
    try {
      const list = await fetchJSON('/projects/' + encodeURIComponent(currentProjectId) + '/blockers');
      if (list.length === 0) {
        blockersList.innerHTML = '<li class="hint">ブロックされているタスクはありません。</li>';
        return;
      }
      blockersList.innerHTML = list.map(b => {
        const blockedBy = b.blocked_by || [];
        const removeBtns = blockedBy.map(fromId =>
          `<button type="button" class="btn-remove-dep" data-from="${escapeAttr(fromId)}" data-to="${escapeAttr(b.id)}">${escapeHtml(fromId)} → ${escapeHtml(b.id)} を解除</button>`
        ).join(' ');
        return `<li><div class="task-id">${escapeHtml(b.id)}</div><div>${escapeHtml(b.title)}</div><div class="blocked-by">blocked by: ${blockedBy.map(id => escapeHtml(id)).join(', ')}</div><div class="dependency-actions">${removeBtns}</div></li>`;
      }).join('');
      blockersList.querySelectorAll('.btn-remove-dep').forEach(btn => {
        btn.addEventListener('click', () => removeDependency(btn.dataset.from, btn.dataset.to));
      });
    } catch (e) {
      blockersList.innerHTML = '<li class="error">読み込み失敗: ' + escapeHtml(e.message) + '</li>';
    }
  }

  function backToBoard() {
    showView(viewBoard);
  }

  async function removeDependency(fromTaskId, toTaskId) {
    try {
      await fetchDELETE('/dependencies?from_task_id=' + encodeURIComponent(fromTaskId) + '&to_task_id=' + encodeURIComponent(toTaskId));
      showToast('依存を解除しました');
      showBlockers();
    } catch (e) {
      showToast(e.message, true);
    }
  }

  $('btn-projects').addEventListener('click', () => {
    setBoardTitle('');
    currentProjectId = null;
    currentProjectName = null;
    loadProjects();
    showView(viewProjects);
  });
  $('btn-back').addEventListener('click', () => {
    setBoardTitle('');
    currentProjectId = null;
    currentProjectName = null;
    loadProjects();
    showView(viewProjects);
  });
  $('btn-new-project').addEventListener('click', openNewProjectModal);
  $('btn-new-task').addEventListener('click', openNewTaskModal);
  $('btn-add-dependency').addEventListener('click', openAddDependencyModal);
  $('btn-blockers').addEventListener('click', showBlockers);
  $('btn-back-blockers').addEventListener('click', backToBoard);

  loadProjects();
})();
