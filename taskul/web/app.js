(function () {
  const API = ''; // same origin: /projects, /projects/:id/board, etc.

  const $ = (id) => document.getElementById(id);
  const viewProjects = $('view-projects');
  const viewBoard = $('view-board');
  const viewBlockers = $('view-blockers');
  const projectList = $('project-list');
  const boardLanes = $('board-lanes');
  const boardTitle = $('board-title');
  const blockersList = $('blockers-list');

  let currentProjectId = null;

  function showView(view) {
    [viewProjects, viewBoard, viewBlockers].forEach(el => el.classList.add('hidden'));
    view.classList.remove('hidden');
  }

  function setBoardTitle(name) {
    boardTitle.textContent = name ? `: ${name}` : '';
  }

  async function fetchJSON(path) {
    const r = await fetch(API + path);
    if (!r.ok) throw new Error(r.status + ' ' + r.statusText);
    return r.json();
  }

  async function loadProjects() {
    projectList.innerHTML = '<li class="loading">読み込み中…</li>';
    try {
      const projects = await fetchJSON('/projects');
      if (projects.length === 0) {
        projectList.innerHTML = '<li class="hint">プロジェクトがありません。CLI で create-project してください。</li>';
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

  function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }
  function escapeAttr(s) {
    return escapeHtml(s).replace(/"/g, '&quot;');
  }

  async function openBoard(projectId, projectName) {
    currentProjectId = projectId;
    setBoardTitle(projectName || projectId);
    boardLanes.innerHTML = '<div class="loading">ボード読み込み中…</div>';
    showView(viewBoard);
    try {
      const board = await fetchJSON('/projects/' + encodeURIComponent(projectId) + '/board');
      renderBoard(board);
    } catch (e) {
      boardLanes.innerHTML = '<div class="error">読み込み失敗: ' + escapeHtml(e.message) + '</div>';
    }
  }

  function renderBoard(board) {
    const statuses = ['Backlog', 'Todo', 'Doing', 'Review', 'Done'];
    boardLanes.innerHTML = statuses.map(status => {
      const tasks = board.lanes[status] || [];
      const cards = tasks.map(t =>
        `<div class="card"><div class="card-id">${escapeHtml(t.id)}</div><div class="card-title">${escapeHtml(t.title)}</div></div>`
      ).join('');
      return `<div class="lane ${status}"><div class="lane-title">${escapeHtml(status)}</div><div class="lane-cards">${cards}</div></div>`;
    }).join('');
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
      blockersList.innerHTML = list.map(b =>
        `<li><div class="task-id">${escapeHtml(b.id)}</div><div>${escapeHtml(b.title)}</div><div class="blocked-by">blocked by: ${(b.blocked_by || []).map(id => escapeHtml(id)).join(', ')}</div></li>`
      ).join('');
    } catch (e) {
      blockersList.innerHTML = '<li class="error">読み込み失敗: ' + escapeHtml(e.message) + '</li>';
    }
  }

  function backToBoard() {
    showView(viewBoard);
  }

  $('btn-projects').addEventListener('click', () => {
    setBoardTitle('');
    currentProjectId = null;
    loadProjects();
    showView(viewProjects);
  });
  $('btn-back').addEventListener('click', () => {
    setBoardTitle('');
    currentProjectId = null;
    loadProjects();
    showView(viewProjects);
  });
  $('btn-blockers').addEventListener('click', showBlockers);
  $('btn-back-blockers').addEventListener('click', backToBoard);

  loadProjects();
})();
