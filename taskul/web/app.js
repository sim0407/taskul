(function () {
  const API = '';
  const STATUSES = ['Backlog', 'Todo', 'Doing', 'Review', 'Done'];

  const $ = (id) => document.getElementById(id);
  const viewProjects = $('view-projects');
  const viewBoard = $('view-board');
  const viewGantt = $('view-gantt');
  const viewBlockers = $('view-blockers');
  const projectList = $('project-list');
  const boardLanes = $('board-lanes');
  const ganttContainer = $('gantt-container');
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
  let lastBoardMilestones = [];
  let lastGanttTasks = [];
  let lastGanttMilestones = [];
  let lastGanttRange = { fromStr: '', toStr: '' };
  let collapsedParents = new Set(); // Track collapsed parent tasks

  function showView(view) {
    [viewProjects, viewBoard, viewGantt, viewBlockers].forEach(el => el.classList.add('hidden'));
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
        `<li><a href="#" data-project-id="${p.id}" data-project-name="${escapeAttr(p.name)}">${escapeHtml(p.name)} (${p.id})</a> <button type="button" class="btn-delete-project" data-project-id="${escapeAttr(p.id)}" data-project-name="${escapeAttr(p.name)}">削除</button></li>`
      ).join('');
      projectList.querySelectorAll('a').forEach(a => {
        a.addEventListener('click', (e) => {
          e.preventDefault();
          openBoard(a.dataset.projectId, a.dataset.projectName);
        });
      });
      projectList.querySelectorAll('.btn-delete-project').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          deleteProject(btn.dataset.projectId, btn.dataset.projectName);
        });
      });
    } catch (e) {
      projectList.innerHTML = '<li class="error">読み込み失敗: ' + escapeHtml(e.message) + '</li>';
    }
  }

  async function createSeedProject() {
    try {
      const summary = await fetchPOST('/seed', { name: 'サンプルプロジェクト' });
      showToast('サンプルプロジェクトを作成しました');
      await loadProjects();
      if (summary && summary.project) {
        openBoard(summary.project.id, summary.project.name);
      }
    } catch (e) {
      showToast(e.message, true);
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

  async function openAddSubtaskModal(parentTaskId, parentTaskTitle, parentStatus) {
    if (!currentProjectId) return;
    // Fetch parent task to get default values
    let parentTask = null;
    try {
      parentTask = await fetchJSON('/tasks/' + encodeURIComponent(parentTaskId));
    } catch (e) {
      // Ignore, use provided values
    }
    const defaultStatus = parentTask?.status || parentStatus || 'Backlog';
    const defaultMilestoneId = parentTask?.milestone_id || '';
    const defaultStartDate = parentTask?.start_date || '';
    const defaultDueDate = parentTask?.due_date || '';

    const statusOpts = STATUSES.map(s => `<option value="${s}" ${s === defaultStatus ? 'selected' : ''}>${s}</option>`).join('');
    const milestoneOpts = '<option value="">(なし / 親タスクから継承)</option>' +
      lastBoardMilestones.map(m => `<option value="${escapeAttr(m.id)}" ${m.id === defaultMilestoneId ? 'selected' : ''}>${escapeHtml(m.id + ' ' + (m.title || ''))}</option>`).join('');

    const parentLabel = escapeHtml(parentTaskId + (parentTaskTitle ? ' ' + parentTaskTitle : ''));
    showModal('子タスクを追加: ' + parentLabel, `
      <form id="form-add-subtask" class="form">
        <div class="form-group">
          <label for="subtask-title">タイトル</label>
          <input type="text" id="subtask-title" name="title" required placeholder="子タスクのタイトル">
        </div>
        <div class="form-group">
          <label for="subtask-status">ステータス</label>
          <select id="subtask-status" name="status">${statusOpts}</select>
        </div>
        <div class="form-group">
          <label for="subtask-milestone">マイルストーン</label>
          <select id="subtask-milestone" name="milestone_id">${milestoneOpts}</select>
        </div>
        <div class="form-group">
          <label for="subtask-start-date">開始日 (YYYY-MM-DD)</label>
          <input type="text" id="subtask-start-date" name="start_date" value="${escapeAttr(defaultStartDate)}" placeholder="YYYY-MM-DD（空欄で親から継承）">
        </div>
        <div class="form-group">
          <label for="subtask-due-date">期限 (YYYY-MM-DD)</label>
          <input type="text" id="subtask-due-date" name="due_date" value="${escapeAttr(defaultDueDate)}" placeholder="YYYY-MM-DD（空欄で親から継承）">
        </div>
        <div class="form-group">
          <label for="subtask-estimate-hours">見積もり (時間)</label>
          <input type="number" id="subtask-estimate-hours" name="estimate_hours" step="0.5" placeholder="数値">
        </div>
        <div id="form-add-subtask-error" class="form-error hidden"></div>
        <div class="form-actions">
          <button type="button" class="btn-cancel" data-dismiss="modal">キャンセル</button>
          <button type="submit" class="btn-submit">追加</button>
        </div>
      </form>
    `);
    const form = modalBody.querySelector('#form-add-subtask');
    const errEl = modalBody.querySelector('#form-add-subtask-error');
    form.querySelector('[data-dismiss="modal"]').addEventListener('click', closeModal);
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const title = form.querySelector('#subtask-title').value.trim();
      if (!title) { errEl.textContent = 'タイトルを入力してください'; errEl.classList.remove('hidden'); return; }
      errEl.classList.add('hidden');
      const milestoneVal = form.querySelector('#subtask-milestone').value;
      const startDateVal = form.querySelector('#subtask-start-date').value.trim();
      const dueDateVal = form.querySelector('#subtask-due-date').value.trim();
      const estimateVal = form.querySelector('#subtask-estimate-hours').value.trim();
      const body = {
        project_id: currentProjectId,
        title,
        status: form.querySelector('#subtask-status').value,
        parent_task_id: parentTaskId,
      };
      // Only send values if explicitly provided (otherwise inherit from parent)
      if (milestoneVal) body.milestone_id = milestoneVal;
      if (startDateVal) body.start_date = startDateVal;
      if (dueDateVal) body.due_date = dueDateVal;
      if (estimateVal) body.estimate_hours = parseFloat(estimateVal);
      try {
        await fetchPOST('/tasks', body);
        showToast('子タスクを追加しました');
        closeModal();
        refreshBoard();
      } catch (err) {
        errEl.textContent = err.message;
        errEl.classList.remove('hidden');
      }
    });
  }

  function applyTaskFilters(tasks, milestoneId, parentValue, depthValue) {
    return tasks.filter(t => {
      if (milestoneId && (t.milestone_id || '') !== milestoneId) return false;
      if (parentValue === '__root__') { if (t.parent_task_id) return false; }
      else if (parentValue && (t.parent_task_id || '') !== parentValue) return false;
      if (depthValue !== '' && depthValue !== undefined) {
        const depthNum = parseInt(depthValue, 10);
        if (!isNaN(depthNum) && (t.depth ?? 0) !== depthNum) return false;
      }
      return true;
    });
  }

  function fillBoardFilterSelects(board, milestones) {
    lastBoardMilestones = milestones || [];
    const msSelect = $('board-filter-milestone');
    const curMs = msSelect.value;
    msSelect.innerHTML = '<option value="">すべて</option>' +
      lastBoardMilestones.map(m => `<option value="${escapeAttr(m.id)}">${escapeHtml(m.title || m.id)}</option>`).join('');
    if (curMs) msSelect.value = curMs;

    const flat = STATUSES.flatMap(s => (board.lanes[s] || []).map(t => ({ id: t.id, title: t.title, depth: t.depth })));
    const parentSelect = $('board-filter-parent');
    const curParent = parentSelect.value;
    parentSelect.innerHTML = '<option value="">すべて</option><option value="__root__">ルートのみ</option>' +
      flat.map(t => `<option value="${escapeAttr(t.id)}">${escapeHtml(t.id + ' ' + (t.title || ''))}</option>`).join('');
    if (curParent) parentSelect.value = curParent;

    const depthSelect = $('board-filter-depth');
    const curDepth = depthSelect.value;
    const depths = [...new Set(flat.map(t => t.depth ?? 0))].sort((a, b) => a - b);
    depthSelect.innerHTML = '<option value="">すべて</option>' +
      depths.map(d => `<option value="${d}">${d}</option>`).join('');
    if (curDepth) depthSelect.value = curDepth;
  }

  function getFilteredBoard(board, milestoneId, parentValue, depthValue) {
    if (!milestoneId && !parentValue && depthValue === '') return board;
    const lanes = {};
    STATUSES.forEach(status => {
      const raw = board.lanes[status] || [];
      lanes[status] = applyTaskFilters(raw, milestoneId, parentValue, depthValue);
    });
    return { project_id: board.project_id, lanes };
  }

  function getMissingFilterQueryParams() {
    const missingMilestone = $('board-filter-missing-milestone')?.checked || false;
    const missingDue = $('board-filter-missing-due')?.checked || false;
    const missingEstimate = $('board-filter-missing-estimate')?.checked || false;
    const params = [];
    if (missingMilestone) params.push('missing_milestone=true');
    if (missingDue) params.push('missing_due_date=true');
    if (missingEstimate) params.push('missing_estimate=true');
    return params.length > 0 ? '?' + params.join('&') : '';
  }

  async function openBoard(projectId, projectName) {
    currentProjectId = projectId;
    currentProjectName = projectName || projectId;
    setBoardTitle(currentProjectName);
    boardLanes.innerHTML = '<div class="loading">ボード読み込み中…</div>';
    showView(viewBoard);
    try {
      const queryParams = getMissingFilterQueryParams();
      const [board, milestones] = await Promise.all([
        fetchJSON('/projects/' + encodeURIComponent(projectId) + '/board' + queryParams),
        fetchJSON('/projects/' + encodeURIComponent(projectId) + '/milestones').catch(() => []),
      ]);
      lastBoard = board;
      fillBoardFilterSelects(board, milestones);
      renderBoardWithFilters();
    } catch (e) {
      boardLanes.innerHTML = '<div class="error">読み込み失敗: ' + escapeHtml(e.message) + '</div>';
    }
  }

  async function refreshBoard() {
    if (!currentProjectId) return;
    try {
      const queryParams = getMissingFilterQueryParams();
      const [board, milestones] = await Promise.all([
        fetchJSON('/projects/' + encodeURIComponent(currentProjectId) + '/board' + queryParams),
        fetchJSON('/projects/' + encodeURIComponent(currentProjectId) + '/milestones').catch(() => []),
      ]);
      lastBoard = board;
      fillBoardFilterSelects(board, milestones);
      renderBoardWithFilters();
    } catch (e) {
      showToast(e.message, true);
    }
  }

  function renderBoardWithFilters() {
    if (!lastBoard) return;
    const milestoneId = ($('board-filter-milestone') && $('board-filter-milestone').value) || '';
    const parentValue = ($('board-filter-parent') && $('board-filter-parent').value) || '';
    const depthValue = ($('board-filter-depth') && $('board-filter-depth').value) || '';
    const board = getFilteredBoard(lastBoard, milestoneId, parentValue, depthValue);
    const statuses = STATUSES;
    boardLanes.innerHTML = statuses.map(status => {
      const tasks = board.lanes[status] || [];
      // Filter out children of collapsed parents in the same status
      const visibleTasks = tasks.filter(t => !isChildOfCollapsedParent(t, status));
      const cards = visibleTasks.map(t => renderCard(t, status));
      return `<div class="lane ${status}" data-status="${escapeAttr(status)}"><div class="lane-title">${escapeHtml(status)}</div><div class="lane-cards">${cards.join('')}</div></div>`;
    }).join('');
    boardLanes.querySelectorAll('.btn-move-left, .btn-move-right').forEach(btn => {
      btn.addEventListener('click', () => moveTask(btn.dataset.taskId, btn.dataset.status));
    });
    boardLanes.querySelectorAll('.btn-add-subtask').forEach(btn => {
      btn.addEventListener('click', () => openAddSubtaskModal(btn.dataset.taskId, btn.dataset.taskTitle || '', btn.dataset.taskStatus || ''));
    });
    boardLanes.querySelectorAll('.btn-card-edit').forEach(btn => {
      btn.addEventListener('click', () => openEditTaskModal(btn.dataset.taskId));
    });
    boardLanes.querySelectorAll('.btn-collapse').forEach(btn => {
      btn.addEventListener('click', () => toggleCollapse(btn.dataset.taskId));
    });

    // ドラッグ&ドロップ（ステータス変更のみ）
    boardLanes.querySelectorAll('.card').forEach(card => {
      card.addEventListener('dragstart', (e) => {
        e.dataTransfer.setData('text/plain', card.dataset.taskId);
        card.classList.add('dragging');
      });
      card.addEventListener('dragend', () => {
        card.classList.remove('dragging');
        boardLanes.querySelectorAll('.lane-cards').forEach(lc => lc.classList.remove('drag-over'));
      });
    });

    boardLanes.querySelectorAll('.lane-cards').forEach(laneCards => {
      laneCards.addEventListener('dragover', (e) => {
        e.preventDefault();
        laneCards.classList.add('drag-over');
      });
      laneCards.addEventListener('dragleave', (e) => {
        if (!laneCards.contains(e.relatedTarget)) {
          laneCards.classList.remove('drag-over');
        }
      });
      laneCards.addEventListener('drop', async (e) => {
        e.preventDefault();
        laneCards.classList.remove('drag-over');
        const taskId = e.dataTransfer.getData('text/plain');
        if (!taskId) return;
        const lane = laneCards.closest('.lane');
        const status = lane.dataset.status;
        await moveTask(taskId, status);
      });
    });
  }

  function renderBoard(board) {
    lastBoard = board;
    renderBoardWithFilters();
  }

  function taskHasChildren(taskId) {
    if (!lastBoard) return false;
    const allTasks = STATUSES.flatMap(s => (lastBoard.lanes[s] || []));
    return allTasks.some(t => t.parent_task_id === taskId);
  }

  function getTaskById(taskId) {
    if (!lastBoard) return null;
    const allTasks = STATUSES.flatMap(s => (lastBoard.lanes[s] || []));
    return allTasks.find(t => t.id === taskId) || null;
  }

  function isChildOfCollapsedParent(task, currentStatus) {
    if (!task.parent_task_id) return false;
    // Check if parent is collapsed and in the same status
    const parent = getTaskById(task.parent_task_id);
    if (!parent) return false;
    // Only collapse children in the same status as parent
    if (parent.status === currentStatus && collapsedParents.has(task.parent_task_id)) {
      return true;
    }
    return false;
  }

  function toggleCollapse(parentTaskId) {
    if (collapsedParents.has(parentTaskId)) {
      collapsedParents.delete(parentTaskId);
    } else {
      collapsedParents.add(parentTaskId);
    }
    renderBoardWithFilters();
  }

  function renderCard(t, currentStatus) {
    const idx = STATUSES.indexOf(currentStatus);
    const hasPrev = idx > 0;
    const hasNext = idx < STATUSES.length - 1;
    const prevStatus = hasPrev ? STATUSES[idx - 1] : null;
    const nextStatus = hasNext ? STATUSES[idx + 1] : null;
    const hasChildren = taskHasChildren(t.id);
    const draggable = hasChildren ? 'false' : 'true';

    // Collapse/expand button for parent tasks
    const isCollapsed = collapsedParents.has(t.id);
    const collapseBtn = hasChildren
      ? `<button type="button" class="btn-collapse" data-task-id="${escapeAttr(t.id)}" title="${isCollapsed ? '展開' : '折り畳み'}">${isCollapsed ? '+' : '-'}</button>`
      : '';
    const parentBadge = hasChildren ? '<span class="card-parent-badge" title="ステータスは子タスクから自動計算">親</span>' : '';

    // Show parent task info for child tasks in different status
    let parentInfo = '';
    if (t.parent_task_id) {
      const parent = getTaskById(t.parent_task_id);
      if (parent && parent.status !== currentStatus) {
        parentInfo = `<div class="card-parent-info" title="親: ${escapeAttr(parent.id)} ${escapeAttr(parent.title)}">← ${escapeHtml(parent.title)}</div>`;
      }
    }

    // Due date and estimate display
    let metaInfo = '';
    const dueDateStr = t.due_date ? t.due_date.slice(5).replace('-', '/') : '';
    const estimateStr = t.estimate_hours != null ? t.estimate_hours + 'h' : '';
    if (dueDateStr || estimateStr) {
      const parts = [];
      if (dueDateStr) parts.push(dueDateStr);
      if (estimateStr) parts.push(estimateStr);
      metaInfo = `<div class="card-meta">${escapeHtml(parts.join(' | '))}</div>`;
    }

    const actions = `
      <div class="card-actions">
        ${collapseBtn}
        ${hasPrev && !hasChildren ? `<button type="button" class="btn-move-left btn-arrow" data-task-id="${escapeAttr(t.id)}" data-status="${escapeAttr(prevStatus)}" title="${escapeAttr(prevStatus)}へ">←</button>` : ''}
        ${hasNext && !hasChildren ? `<button type="button" class="btn-move-right btn-arrow" data-task-id="${escapeAttr(t.id)}" data-status="${escapeAttr(nextStatus)}" title="${escapeAttr(nextStatus)}へ">→</button>` : ''}
        <button type="button" class="btn-add-subtask" data-task-id="${escapeAttr(t.id)}" data-task-title="${escapeAttr(t.title || '')}" data-task-status="${escapeAttr(currentStatus)}" title="子タスクを追加">+子タスク</button>
        <button type="button" class="btn-card-edit" data-task-id="${escapeAttr(t.id)}">編集</button>
      </div>
    `;

    // Child task indentation
    const isChild = t.parent_task_id && !parentInfo; // In same status as parent
    const childClass = isChild ? ' card-child' : '';
    const depthClass = t.depth > 0 ? ` card-depth-${Math.min(t.depth, 3)}` : '';

    return `<div class="card${hasChildren ? ' card-parent' : ''}${childClass}${depthClass}" data-task-id="${escapeAttr(t.id)}" draggable="${draggable}">${parentInfo}<div class="card-title">${escapeHtml(t.title)}</div>${metaInfo}<div class="card-footer">${parentBadge}${actions}</div></div>`;
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

  async function moveTask(taskId, status) {
    try {
      await fetchPOST('/tasks/' + encodeURIComponent(taskId) + '/move', { status });
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

      // Check if task has children (status is auto-calculated)
      const hasChildren = taskHasChildren(taskId);

      const statusOpts = STATUSES.map(s => `<option value="${s}" ${s === task.status ? 'selected' : ''}>${s}</option>`).join('');

      // マイルストーン選択肢
      const milestoneOpts = '<option value="">(なし)</option>' +
        lastBoardMilestones.map(m => `<option value="${escapeAttr(m.id)}" ${m.id === task.milestone_id ? 'selected' : ''}>${escapeHtml(m.id + ' ' + (m.title || ''))}</option>`).join('');

      // 親タスク選択肢（自身と子孫は除外）
      const allTasks = lastBoard ? STATUSES.flatMap(s => (lastBoard.lanes[s] || [])) : [];
      const descendants = new Set();
      const findDescendants = (pid) => {
        allTasks.forEach(t => {
          if (t.parent_task_id === pid && !descendants.has(t.id)) {
            descendants.add(t.id);
            findDescendants(t.id);
          }
        });
      };
      findDescendants(taskId);
      const parentOpts = '<option value="">(なし)</option>' +
        allTasks.filter(t => t.id !== taskId && !descendants.has(t.id))
          .map(t => `<option value="${escapeAttr(t.id)}" ${t.id === task.parent_task_id ? 'selected' : ''}>${escapeHtml(t.id + ' ' + (t.title || ''))}</option>`).join('');

      const statusDisabled = hasChildren ? 'disabled' : '';
      const statusHint = hasChildren ? '<span class="form-hint">（子タスクから自動計算）</span>' : '';

      showModal('タスク編集: ' + escapeHtml(taskId), `
        <form id="form-edit-task" class="form">
          <div class="form-group form-group-id">
            <span class="task-id-display">${escapeHtml(taskId)}</span>
          </div>
          <div class="form-group">
            <label for="edit-title">タイトル</label>
            <input type="text" id="edit-title" name="title" value="${escapeAttr(task.title || '')}" required>
          </div>
          <div class="form-group">
            <label for="edit-description">説明</label>
            <textarea id="edit-description" name="description" rows="2">${escapeAttr(task.description || '')}</textarea>
          </div>
          <div class="form-group">
            <label for="edit-status">ステータス ${statusHint}</label>
            <select id="edit-status" name="status" ${statusDisabled}>${statusOpts}</select>
          </div>
          <div class="form-group">
            <label for="edit-milestone">マイルストーン</label>
            <select id="edit-milestone" name="milestone_id">${milestoneOpts}</select>
          </div>
          <div class="form-group">
            <label for="edit-parent">親タスク</label>
            <select id="edit-parent" name="parent_task_id">${parentOpts}</select>
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
            ${hasChildren ? '' : '<button type="button" class="btn-mark-done" data-task-id="' + escapeAttr(taskId) + '">完了にする</button>'}
            <button type="button" class="btn-delete-task" data-task-id="${escapeAttr(taskId)}">削除</button>
            <button type="submit" class="btn-submit">保存</button>
          </div>
        </form>
      `);
      const form = modalBody.querySelector('#form-edit-task');
      const errEl = modalBody.querySelector('#form-edit-task-error');
      form.querySelector('[data-dismiss="modal"]').addEventListener('click', closeModal);
      const markDoneBtn = form.querySelector('.btn-mark-done');
      if (markDoneBtn) {
        markDoneBtn.addEventListener('click', async () => {
          try {
            await fetchPOST('/tasks/' + encodeURIComponent(taskId) + '/mark-done', {});
            showToast('タスクを完了にしました');
            closeModal();
            refreshBoard();
          } catch (e) {
            errEl.textContent = e.message;
            errEl.classList.remove('hidden');
          }
        });
      }
      form.querySelector('.btn-delete-task').addEventListener('click', async () => {
        try {
          const check = await fetchJSON('/tasks/' + encodeURIComponent(taskId) + '/delete-check');
          let msg = 'このタスクを削除しますか？';
          if (check.descendant_count > 0) {
            msg = `このタスクには ${check.descendant_count} 件の子タスクがあります。\n子タスクもすべて削除されますが、削除しますか？`;
          }
          if (!confirm(msg)) return;
          await fetchDELETE('/tasks/' + encodeURIComponent(taskId));
          showToast('タスクを削除しました');
          closeModal();
          refreshBoard();
        } catch (e) {
          errEl.textContent = e.message;
          errEl.classList.remove('hidden');
        }
      });
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errEl.classList.add('hidden');
        const milestoneVal = form.querySelector('#edit-milestone').value;
        const parentVal = form.querySelector('#edit-parent').value;
        const body = {
          title: form.querySelector('#edit-title').value.trim(),
          description: form.querySelector('#edit-description').value.trim() || null,
          status: form.querySelector('#edit-status').value,
          milestone_id: milestoneVal || null,
          parent_task_id: parentVal || null,
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

  function parseDate(s) {
    if (!s) return null;
    const d = new Date(s + 'T00:00:00');
    return isNaN(d.getTime()) ? null : d;
  }

  function defaultGanttRange() {
    const today = new Date();
    const from = new Date(today);
    from.setDate(from.getDate() - 14);
    const to = new Date(today);
    to.setDate(to.getDate() + 70);
    return { fromStr: from.toISOString().slice(0, 10), toStr: to.toISOString().slice(0, 10) };
  }

  async function showGantt() {
    if (!currentProjectId) return;
    showView(viewGantt);
    const range = defaultGanttRange();
    $('gantt-from').value = range.fromStr;
    $('gantt-to').value = range.toStr;
    await loadGanttWithRange(range.fromStr, range.toStr);
  }

  function fillGanttFilterSelects(tasks, milestones) {
    const msSelect = $('gantt-filter-milestone');
    const curMs = msSelect.value;
    msSelect.innerHTML = '<option value="">すべて</option>' +
      (milestones || []).map(m => `<option value="${escapeAttr(m.id)}">${escapeHtml(m.title || m.id)}</option>`).join('');
    if (curMs) msSelect.value = curMs;

    const parentSelect = $('gantt-filter-parent');
    const curParent = parentSelect.value;
    parentSelect.innerHTML = '<option value="">すべて</option><option value="__root__">ルートのみ</option>' +
      (tasks || []).map(t => `<option value="${escapeAttr(t.id)}">${escapeHtml(t.id + ' ' + (t.title || ''))}</option>`).join('');
    if (curParent) parentSelect.value = curParent;

    const depthSelect = $('gantt-filter-depth');
    const curDepth = depthSelect.value;
    const depths = [...new Set((tasks || []).map(t => t.depth ?? 0))].sort((a, b) => a - b);
    depthSelect.innerHTML = '<option value="">すべて</option>' +
      depths.map(d => `<option value="${d}">${d}</option>`).join('');
    if (curDepth) depthSelect.value = curDepth;
  }

  function applyGanttFiltersAndRender() {
    const milestoneId = ($('gantt-filter-milestone') && $('gantt-filter-milestone').value) || '';
    const parentValue = ($('gantt-filter-parent') && $('gantt-filter-parent').value) || '';
    const depthValue = ($('gantt-filter-depth') && $('gantt-filter-depth').value) || '';
    const filtered = applyTaskFilters(lastGanttTasks, milestoneId, parentValue, depthValue);
    renderGantt(filtered, lastGanttMilestones, lastGanttRange.fromStr, lastGanttRange.toStr);
  }

  async function loadGanttWithRange(fromStr, toStr) {
    ganttContainer.innerHTML = '<div class="loading">読み込み中…</div>';
    try {
      const [tasks, milestones] = await Promise.all([
        fetchJSON('/projects/' + encodeURIComponent(currentProjectId) + '/gantt?from_date=' + fromStr + '&to_date=' + toStr),
        fetchJSON('/projects/' + encodeURIComponent(currentProjectId) + '/milestones'),
      ]);
      lastGanttTasks = tasks;
      lastGanttMilestones = milestones || [];
      lastGanttRange = { fromStr, toStr };
      fillGanttFilterSelects(tasks, milestones);
      applyGanttFiltersAndRender();
    } catch (e) {
      ganttContainer.innerHTML = '<div class="error">読み込み失敗: ' + escapeHtml(e.message) + '</div>';
    }
  }

  function renderGanttBar(rangeStart, rangeDays, dayWidth, item, isMilestone) {
    const start = parseDate(item.start_date) || parseDate(item.due_date) || new Date();
    const end = parseDate(item.due_date) || parseDate(item.start_date) || new Date(start.getTime() + 24 * 60 * 60 * 1000);
    const startMs = start.getTime();
    const endMs = end.getTime();
    let leftPct = ((startMs - rangeStart) / (24 * 60 * 60 * 1000)) * dayWidth;
    let widthPct = ((endMs - startMs) / (24 * 60 * 60 * 1000)) * dayWidth;
    if (widthPct < 1) widthPct = 1;
    if (leftPct < 0) { widthPct += leftPct; leftPct = 0; }
    if (leftPct + widthPct > 100) widthPct = 100 - leftPct;
    let barClass = 'gantt-bar';
    if (isMilestone) {
      barClass += ' gantt-bar-milestone';
    } else if (item.status) {
      barClass += ' gantt-bar-' + item.status.toLowerCase();
    }
    return `<div class="${barClass}" style="left:${leftPct}%;width:${widthPct}%" title="${escapeAttr((item.start_date || '') + ' ～ ' + (item.due_date || ''))}"></div>`;
  }

  function renderGantt(tasks, milestones, rangeFrom, rangeTo) {
    const rangeStart = parseDate(rangeFrom).getTime();
    const rangeEnd = parseDate(rangeTo).getTime();
    const rangeDays = (rangeEnd - rangeStart) / (24 * 60 * 60 * 1000) || 1;
    const dayWidth = 100 / rangeDays;
    const todayMs = new Date(new Date().toISOString().slice(0, 10)).getTime();
    const todayPct = rangeDays > 0 ? ((todayMs - rangeStart) / (24 * 60 * 60 * 1000)) * dayWidth : null;
    const showToday = todayPct != null && todayPct >= 0 && todayPct <= 100;
    const todayLineStyle = showToday ? `left:${todayPct}%` : '';
    const todayLine = showToday ? `<div class="gantt-today-line" style="${todayLineStyle}" title="今日"></div>` : '';

    const weeks = [];
    let d = new Date(parseDate(rangeFrom).getTime());
    const endD = parseDate(rangeTo);
    while (d <= endD) {
      weeks.push('<span class="gantt-week">' + d.toISOString().slice(0, 10) + '</span>');
      d = new Date(d.getTime() + 7 * 24 * 60 * 60 * 1000);
    }
    const headerTodayLine = showToday ? `<div class="gantt-today-line" style="${todayLineStyle}" title="今日"></div>` : '';

    const rangeFromStr = rangeFrom;
    const rangeToStr = rangeTo;
    const inRange = (m) => (m.due_date >= rangeFromStr && m.start_date <= rangeToStr);
    const visibleMilestones = milestones.filter(inRange);

    if (visibleMilestones.length === 0 && tasks.length === 0) {
      ganttContainer.innerHTML = '<p class="hint">この期間にタスクがありません。タスクに開始日・期限を設定するか、マイルストーンを追加するとガントで表示されます。</p>';
      return;
    }

    let html = '<div class="gantt-header"><div class="gantt-label gantt-label-head">項目</div><div class="gantt-chart-area"><div class="gantt-weeks">' + weeks.join('') + '</div>' + headerTodayLine + '</div></div>';

    if (visibleMilestones.length > 0) {
      visibleMilestones.forEach(m => {
        const label = '<span class="gantt-milestone-label">' + escapeHtml(m.id) + '</span> ' + escapeHtml(m.title || '');
        const bar = renderGanttBar(rangeStart, rangeDays, dayWidth, m, true);
        html += `<div class="gantt-row gantt-row-milestone"><div class="gantt-label" title="${escapeAttr(m.id)}">${label}</div><div class="gantt-bar-wrap">${todayLine}${bar}</div></div>`;
      });
    }
    tasks.forEach(t => {
      const statusClass = t.status ? 'gantt-status gantt-status-' + t.status.toLowerCase() : '';
      const statusBadge = t.status ? `<span class="${statusClass}">${escapeHtml(t.status)}</span>` : '';
      const label = escapeHtml(t.id) + ' ' + escapeHtml(t.title || '') + ' ' + statusBadge;
      const bar = renderGanttBar(rangeStart, rangeDays, dayWidth, t, false);
      html += `<div class="gantt-row"><div class="gantt-label" title="${escapeAttr(t.id)}">${label}</div><div class="gantt-bar-wrap">${todayLine}${bar}</div></div>`;
    });

    ganttContainer.innerHTML = html;
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

  // Milestone management modal
  async function openMilestonesModal() {
    if (!currentProjectId) return;
    let milestones;
    try {
      milestones = await fetchJSON('/projects/' + encodeURIComponent(currentProjectId) + '/milestones');
    } catch (e) {
      showToast(e.message, true);
      return;
    }
    const rows = milestones.length === 0
      ? '<p class="hint">マイルストーンがありません。</p>'
      : milestones.map(m => `
        <div class="milestone-row" data-milestone-id="${escapeAttr(m.id)}">
          <span class="milestone-id">${escapeHtml(m.id)}</span>
          <span class="milestone-title">${escapeHtml(m.title || '')}</span>
          <span class="milestone-dates">${escapeHtml(m.start_date || '')} ～ ${escapeHtml(m.due_date || '')}</span>
          <button type="button" class="btn-edit-milestone" data-milestone-id="${escapeAttr(m.id)}">編集</button>
          <button type="button" class="btn-delete-milestone" data-milestone-id="${escapeAttr(m.id)}">削除</button>
        </div>
      `).join('');
    showModal('マイルストーン管理', `
      <div id="milestones-list">${rows}</div>
      <hr>
      <h4>新規マイルストーン</h4>
      <form id="form-new-milestone" class="form">
        <div class="form-group">
          <label for="ms-title">タイトル</label>
          <input type="text" id="ms-title" name="title" required placeholder="マイルストーン名">
        </div>
        <div class="form-group">
          <label for="ms-start-date">開始日</label>
          <input type="text" id="ms-start-date" name="start_date" required placeholder="YYYY-MM-DD">
        </div>
        <div class="form-group">
          <label for="ms-due-date">期限</label>
          <input type="text" id="ms-due-date" name="due_date" required placeholder="YYYY-MM-DD">
        </div>
        <div id="form-new-milestone-error" class="form-error hidden"></div>
        <div class="form-actions">
          <button type="button" class="btn-cancel" data-dismiss="modal">閉じる</button>
          <button type="submit" class="btn-submit">追加</button>
        </div>
      </form>
    `);
    modalBody.querySelector('[data-dismiss="modal"]').addEventListener('click', closeModal);
    modalBody.querySelectorAll('.btn-edit-milestone').forEach(btn => {
      btn.addEventListener('click', () => openEditMilestoneModal(btn.dataset.milestoneId));
    });
    modalBody.querySelectorAll('.btn-delete-milestone').forEach(btn => {
      btn.addEventListener('click', async () => {
        const milestoneId = btn.dataset.milestoneId;
        try {
          const check = await fetchJSON('/milestones/' + encodeURIComponent(milestoneId) + '/delete-check');
          let msg = 'このマイルストーンを削除しますか？';
          if (check.task_count > 0) {
            msg += '\n\n※ このマイルストーンを参照しているタスクが ' + check.task_count + ' 件あります。\nこれらのタスクのマイルストーン参照は解除されます。';
          }
          if (!confirm(msg)) return;
          await fetchDELETE('/milestones/' + encodeURIComponent(milestoneId));
          showToast('マイルストーンを削除しました');
          openMilestonesModal();
          refreshBoard();
        } catch (e) {
          showToast(e.message, true);
        }
      });
    });
    const form = modalBody.querySelector('#form-new-milestone');
    const errEl = modalBody.querySelector('#form-new-milestone-error');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errEl.classList.add('hidden');
      const title = form.querySelector('#ms-title').value.trim();
      const start_date = form.querySelector('#ms-start-date').value.trim();
      const due_date = form.querySelector('#ms-due-date').value.trim();
      if (!title || !start_date || !due_date) {
        errEl.textContent = 'すべての項目を入力してください';
        errEl.classList.remove('hidden');
        return;
      }
      try {
        await fetchPOST('/projects/' + encodeURIComponent(currentProjectId) + '/milestones', { title, start_date, due_date });
        showToast('マイルストーンを追加しました');
        openMilestonesModal();
        refreshBoard();
      } catch (err) {
        errEl.textContent = err.message;
        errEl.classList.remove('hidden');
      }
    });
  }

  async function openEditMilestoneModal(milestoneId) {
    let m;
    try {
      m = await fetchJSON('/milestones/' + encodeURIComponent(milestoneId));
    } catch (e) {
      showToast(e.message, true);
      return;
    }
    showModal('マイルストーン編集', `
      <form id="form-edit-milestone" class="form">
        <div class="form-group">
          <label for="edit-ms-title">タイトル</label>
          <input type="text" id="edit-ms-title" name="title" value="${escapeAttr(m.title || '')}" required>
        </div>
        <div class="form-group">
          <label for="edit-ms-start-date">開始日</label>
          <input type="text" id="edit-ms-start-date" name="start_date" value="${escapeAttr(m.start_date || '')}" required placeholder="YYYY-MM-DD">
        </div>
        <div class="form-group">
          <label for="edit-ms-due-date">期限</label>
          <input type="text" id="edit-ms-due-date" name="due_date" value="${escapeAttr(m.due_date || '')}" required placeholder="YYYY-MM-DD">
        </div>
        <div id="form-edit-milestone-error" class="form-error hidden"></div>
        <div class="form-actions">
          <button type="button" class="btn-cancel" data-back="milestones">← 戻る</button>
          <button type="submit" class="btn-submit">保存</button>
        </div>
      </form>
    `);
    const form = modalBody.querySelector('#form-edit-milestone');
    const errEl = modalBody.querySelector('#form-edit-milestone-error');
    form.querySelector('[data-back="milestones"]').addEventListener('click', () => openMilestonesModal());
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errEl.classList.add('hidden');
      const body = {
        title: form.querySelector('#edit-ms-title').value.trim(),
        start_date: form.querySelector('#edit-ms-start-date').value.trim(),
        due_date: form.querySelector('#edit-ms-due-date').value.trim(),
      };
      try {
        await fetchPATCH('/milestones/' + encodeURIComponent(milestoneId), body);
        showToast('マイルストーンを更新しました');
        openMilestonesModal();
        refreshBoard();
      } catch (err) {
        errEl.textContent = err.message;
        errEl.classList.remove('hidden');
      }
    });
  }

  // Event history modal
  async function openEventsModal() {
    if (!currentProjectId) return;
    let events;
    try {
      events = await fetchJSON('/events?project_id=' + encodeURIComponent(currentProjectId));
    } catch (e) {
      showToast(e.message, true);
      return;
    }
    const rows = events.length === 0
      ? '<p class="hint">イベントがありません。</p>'
      : events.map(ev => `
        <div class="event-row">
          <span class="event-time">${escapeHtml(ev.timestamp || '')}</span>
          <span class="event-actor">${escapeHtml(ev.actor || '')}</span>
          <span class="event-type">${escapeHtml(ev.event_type || '')}</span>
          <span class="event-payload">${escapeHtml(JSON.stringify(ev.payload || {}))}</span>
        </div>
      `).join('');
    showModal('イベント履歴', `
      <div id="events-list" class="events-list">${rows}</div>
      <div class="form-actions">
        <button type="button" class="btn-cancel" data-dismiss="modal">閉じる</button>
      </div>
    `);
    modalBody.querySelector('[data-dismiss="modal"]').addEventListener('click', closeModal);
  }

  // Import tasks modal
  function openImportModal() {
    if (!currentProjectId) return;
    showModal('タスクをインポート', `
      <form id="form-import" class="form">
        <p class="hint">CSV, Excel (.xlsx), または XML ファイルからタスクをインポートします。</p>
        <div class="form-group">
          <label for="import-file">ファイル</label>
          <input type="file" id="import-file" name="file" accept=".csv,.xlsx,.xml" required>
        </div>
        <div id="form-import-error" class="form-error hidden"></div>
        <div id="form-import-result" class="form-success hidden"></div>
        <div class="form-actions">
          <button type="button" class="btn-cancel" data-dismiss="modal">キャンセル</button>
          <button type="submit" class="btn-submit">インポート</button>
        </div>
      </form>
    `);
    const form = modalBody.querySelector('#form-import');
    const errEl = modalBody.querySelector('#form-import-error');
    const resultEl = modalBody.querySelector('#form-import-result');
    form.querySelector('[data-dismiss="modal"]').addEventListener('click', closeModal);
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errEl.classList.add('hidden');
      resultEl.classList.add('hidden');
      const fileInput = form.querySelector('#import-file');
      if (!fileInput.files || fileInput.files.length === 0) {
        errEl.textContent = 'ファイルを選択してください';
        errEl.classList.remove('hidden');
        return;
      }
      const file = fileInput.files[0];
      const formData = new FormData();
      formData.append('file', file);
      try {
        const r = await fetch(API + '/projects/' + encodeURIComponent(currentProjectId) + '/import', {
          method: 'POST',
          body: formData,
        });
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          throw new Error(err.detail || r.status + ' ' + r.statusText);
        }
        const result = await r.json();
        const count = result.imported_count || 0;
        resultEl.textContent = count + ' 件のタスクをインポートしました。';
        resultEl.classList.remove('hidden');
        showToast(count + ' 件のタスクをインポートしました');
        refreshBoard();
      } catch (err) {
        errEl.textContent = err.message;
        errEl.classList.remove('hidden');
      }
    });
  }

  // Delete project
  async function deleteProject(projectId, projectName) {
    try {
      const check = await fetchJSON('/projects/' + encodeURIComponent(projectId) + '/delete-check');
      let msg = 'プロジェクト「' + projectName + '」を削除しますか？';
      if (check.task_count > 0 || check.milestone_count > 0) {
        const parts = [];
        if (check.task_count > 0) parts.push(check.task_count + ' 件のタスク');
        if (check.milestone_count > 0) parts.push(check.milestone_count + ' 件のマイルストーン');
        msg += '\n\n※ このプロジェクトには ' + parts.join('と') + ' があります。\nこれらもすべて削除されますが、よろしいですか？';
      }
      if (!confirm(msg)) return;
      await fetchDELETE('/projects/' + encodeURIComponent(projectId));
      showToast('プロジェクトを削除しました');
      loadProjects();
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
  $('btn-seed-project').addEventListener('click', createSeedProject);
  $('btn-new-task').addEventListener('click', openNewTaskModal);
  $('btn-add-dependency').addEventListener('click', openAddDependencyModal);
  $('board-filter-milestone').addEventListener('change', renderBoardWithFilters);
  $('board-filter-parent').addEventListener('change', renderBoardWithFilters);
  $('board-filter-depth').addEventListener('change', renderBoardWithFilters);
  $('board-filter-missing-milestone').addEventListener('change', refreshBoard);
  $('board-filter-missing-due').addEventListener('change', refreshBoard);
  $('board-filter-missing-estimate').addEventListener('change', refreshBoard);

  $('btn-milestones').addEventListener('click', openMilestonesModal);
  $('btn-events').addEventListener('click', openEventsModal);
  $('btn-import').addEventListener('click', openImportModal);

  $('btn-gantt').addEventListener('click', showGantt);
  $('btn-back-gantt').addEventListener('click', backToBoard);
  $('btn-gantt-apply').addEventListener('click', async () => {
    if (!currentProjectId) return;
    const fromStr = $('gantt-from').value.trim();
    const toStr = $('gantt-to').value.trim();
    if (!fromStr || !toStr) {
      showToast('開始日・終了日を入力してください', true);
      return;
    }
    if (fromStr > toStr) {
      showToast('開始日は終了日より前にしてください', true);
      return;
    }
    await loadGanttWithRange(fromStr, toStr);
  });
  $('gantt-filter-milestone').addEventListener('change', applyGanttFiltersAndRender);
  $('gantt-filter-parent').addEventListener('change', applyGanttFiltersAndRender);
  $('gantt-filter-depth').addEventListener('change', applyGanttFiltersAndRender);

  $('btn-blockers').addEventListener('click', showBlockers);
  $('btn-back-blockers').addEventListener('click', backToBoard);

  loadProjects();
})();
