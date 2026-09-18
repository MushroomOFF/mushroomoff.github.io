// ====== КОНСТАНТЫ ======
const JSON_FILE = 'new_releases.json';
const MONTHS_RU = ['Январь','Февраль','Март','Апрель','Май','Июнь',
  'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];

// ====== КОНФИГ GitHub (для работы в сети) ======
const GH = {
  owner: 'MushroomOFF',
  repo: 'AMR-plus-Qwen',
  branch: 'main',
  file: 'Website/new_releases.json'
};

// Не localhost → работаем через GitHub API вместо server.py
const USE_GITHUB_API = !['localhost', '127.0.0.1', ''].includes(location.hostname);

function getGenreGroup(cat) {
  if (cat === 'M' || cat === 'MCS') return 'metal';
  if (['HR', 'HRRU', 'CS'].includes(cat)) return 'alternative';
  return null;
}

const GROUP_ORDER = ['metal', 'alternative'];
const GROUP_LABELS = {
  metal: 'Metal',
  alternative: 'Alternative & Hard Rock'
};

// Порядок тегов: всегда первичная сортировка. Пустой тег — в конце.
const TYPE_ORDER = { 'v': 1, 'd': 2, 'o': 3, 'x': 4, '': 5 };

// ====== СОСТОЯНИЕ ======
let allReleases = [];
let adminToken = null;
let currentYear = null;
let currentMonth = null;
let activeTypes = new Set();
let groupByDate = true;
let sortMode = 'date_desc';

// ====== GitHub-хелперы ======
function ghHeaders() {
  return {
    'Authorization': `Bearer ${adminToken}`,
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28'
  };
}

function b64DecodeUtf8(b64) {
  const bin = atob(b64.replace(/\s/g, ''));
  const bytes = Uint8Array.from(bin, c => c.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

function b64EncodeUtf8(str) {
  const bytes = new TextEncoder().encode(str);
  let bin = '';
  bytes.forEach(b => bin += String.fromCharCode(b));
  return btoa(bin);
}

// Чтение файла из репозитория с поддержкой файлов больше 1 МБ (через git/blobs — обходит CORS raw.githubusercontent.com)
async function ghReadRepoFile() {
  const url = `https://api.github.com/repos/${GH.owner}/${GH.repo}/contents/${GH.file}?ref=${GH.branch}`;
  const get = await fetch(url, { headers: ghHeaders() });
  if (!get.ok) throw new Error('Не удалось прочитать файл из GitHub');
  const meta = await get.json();
  const sha = meta.sha;
  let text;
  if (meta.content && meta.encoding === 'base64') {
    text = b64DecodeUtf8(meta.content);
  } else {
    const blobUrl = `https://api.github.com/repos/${GH.owner}/${GH.repo}/git/blobs/${sha}`;
    const blob = await fetch(blobUrl, { headers: ghHeaders() });
    if (!blob.ok) throw new Error('Не удалось прочитать blob из GitHub');
    const blobData = await blob.json();
    if (blobData.encoding !== 'base64' || !blobData.content) throw new Error('GitHub не вернул содержимое');
    text = b64DecodeUtf8(blobData.content);
  }
  return { sha, data: JSON.parse(text) };
}

// ====== УТИЛИТЫ ======
function cleanData(raw) {
  return raw.map(item => {
    const out = {};
    for (const [k, v] of Object.entries(item)) {
      const key = k.trim();
      out[key] = typeof v === 'string' ? v.trim() : v;
    }
    return out;
  });
}

function parseDate(str) {
  if (!str) return null;
  const d = new Date(str);
  return isNaN(d) ? null : d;
}

function formatDateRu(date) {
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth()+1).padStart(2, '0');
  const year = date.getFullYear();
  return `${year}-${month}-${day}`;
}

function dateKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
}

function plural(n) {
  if (n % 10 === 1 && n % 100 !== 11) return '';
  if ([2,3,4].includes(n % 10) && ![12,13,14].includes(n % 100)) return 'а';
  return 'ов';
}

function getPeriodLabel() {
  if (currentYear === 'all') return 'во всей базе';
  if (currentMonth === 'all') return `за ${currentYear} год`;
  return `в ${MONTHS_RU[currentMonth].toLowerCase()} ${currentYear}`;
}

function showToast(msg, type = 'info') {
  const c = document.getElementById('toastContainer');
  if (!c) return;
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => {
    t.style.transition = 'opacity 0.3s';
    t.style.opacity = '0';
    setTimeout(() => t.remove(), 300);
  }, 3000);
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
}

// ====== АУТЕНТИФИКАЦИЯ (один токен, двойной режим) ======
function openLoginModal() {
  document.getElementById('loginModal').classList.add('active');
  document.getElementById('tokenInput').value = '';
  document.getElementById('modalError').textContent = '';
  setTimeout(() => document.getElementById('tokenInput').focus(), 100);
}

function closeLoginModal() {
  document.getElementById('loginModal').classList.remove('active');
}

async function submitToken() {
  const token = document.getElementById('tokenInput').value.trim();
  const errEl = document.getElementById('modalError');
  if (!token) { errEl.textContent = 'Введите токен'; return; }

  try {
    if (!USE_GITHUB_API) {
      // Локально: через server.py
      const r = await fetch('/api/verify', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({token})
      });
      const data = await r.json();
      if (!data.success) { errEl.textContent = data.message || 'Неверный токен'; return; }
    } else {
      // В сети: токен = fine-grained GitHub token
      adminToken = token;
      const r = await fetch('https://api.github.com/user', { headers: ghHeaders() });
      if (!r.ok) { errEl.textContent = 'Неверный токен'; adminToken = null; return; }
      const ri = await fetch(`https://api.github.com/repos/${GH.owner}/${GH.repo}`, { headers: ghHeaders() });
      if (ri.ok) {
        const j = await ri.json();
        if (!j.permissions || !j.permissions.push) {
          errEl.textContent = 'У токена нет права записи в репозиторий'; adminToken = null; return;
        }
      }
    }
    adminToken = token;
    closeLoginModal();
    updateAdminUI();
    render();
    showToast('✅ Режим редактирования активен', 'success');
  } catch (e) {
    errEl.textContent = 'Ошибка соединения';
  }
}

function logoutAdmin() {
  if (!confirm('Выйти из режима редактирования?')) return;
  adminToken = null;
  updateAdminUI();
  render();
  showToast('🔒 Режим редактирования отключён', 'info');
}

function updateAdminUI() {
  const btn = document.getElementById('adminBtn');
  const badge = document.querySelector('.admin-badge');
  if (adminToken) {
    if (btn) {
      btn.outerHTML = `<div class="admin-badge" onclick="logoutAdmin()" title="Клик — выйти">
        <span class="dot"></span><span>Редактирование</span>
      </div>`;
    }
  } else {
    if (badge) {
      badge.outerHTML = `<button class="admin-btn" id="adminBtn" onclick="openLoginModal()">🔐 Войти</button>`;
    }
  }
}

// ====== ОБНОВЛЕНИЕ MY_TYPE (двойной режим) ======
async function updateMyType(rowId, newType, btnEl) {
  if (!adminToken) { showToast('❌ Требуется вход админа', 'error'); return; }
  const release = allReleases.find(r => String(r.row_id) === String(rowId));
  if (!release) return;
  const oldType = release.my_type;
  if (oldType === newType) return;

  const allBtns = btnEl.parentElement.querySelectorAll('.type-btn');
  allBtns.forEach(b => b.classList.add('saving'));

  try {
    if (!USE_GITHUB_API) {
      const r = await fetch('/api/update_my_type', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({token: adminToken, row_id: rowId, new_type: newType})
      });
      const data = await r.json();
      if (!data.success) throw new Error(data.message);
    } else {
      const { sha, data } = await ghReadRepoFile();
      let found = false;
      for (const r of data) {
        const rid = ('row_id' in r) ? r.row_id : r['row_id '];
        if (String(rid) === String(rowId)) {
          if ('my_type' in r) r['my_type'] = newType;
          if ('my_type ' in r) r['my_type '] = newType;
          found = true;
        }
      }
      if (!found) throw new Error('row_id не найден в JSON');
      const url = `https://api.github.com/repos/${GH.owner}/${GH.repo}/contents/${GH.file}`;
      const put = await fetch(url, {
        method: 'PUT',
        headers: { ...ghHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `releases: row_id=${rowId} my_type '${oldType || ''}' -> '${newType}'`,
          content: b64EncodeUtf8(JSON.stringify(data, null, 1) + '\n'),
          sha: sha,
          branch: GH.branch
        })
      });
      if (!put.ok) {
        const e = await put.json().catch(() => ({}));
        throw new Error(e.message || 'Ошибка записи в GitHub');
      }
    }
    release.my_type = newType;
    render();
    showToast(USE_GITHUB_API ? '✅ Сохранено в GitHub' : `✅ ${release.artist}: ${oldType || '∅'} → ${newType}`, 'success');
  } catch (e) {
    showToast(`❌ ${e.message}`, 'error');
    allBtns.forEach(b => b.classList.remove('saving'));
  }
}

// ====== ФИЛЬТРАЦИЯ ПО ТИПУ ======
function toggleTypeFilter(type) {
  activeTypes.has(type) ? activeTypes.delete(type) : activeTypes.add(type);
  updateTypeFilterUI();
  applyTypeFilter();
}

function updateTypeFilterUI() {
  document.querySelectorAll('.type-filter-btn').forEach(btn => {
    btn.classList.toggle('active', activeTypes.has(btn.dataset.type));
  });
}

function applyTypeFilter() {
  document.querySelectorAll('.release-card').forEach(card => {
    const type = card.dataset.myType || 'empty';
    card.style.display = (activeTypes.size === 0 || activeTypes.has(type)) ? '' : 'none';
  });
  updateCounts();
}

function updateCounts() {
  document.querySelectorAll('.date-group').forEach(dateGroup => {
    let dateVisible = 0;
    dateGroup.querySelectorAll('.genre-section').forEach(genreSection => {
      const visibleCards = genreSection.querySelectorAll('.release-card:not([style*="display: none"])');
      const countEl = genreSection.querySelector('.genre-title .count');
      if (countEl) countEl.textContent = visibleCards.length;
      dateVisible += visibleCards.length;
      genreSection.style.display = visibleCards.length === 0 ? 'none' : '';
    });
    const dateCountEl = dateGroup.querySelector('.date-header .date-count');
    if (dateCountEl) dateCountEl.textContent = `${dateVisible} релиз${plural(dateVisible)}`;
    dateGroup.style.display = dateVisible === 0 ? 'none' : '';
  });
}

// ====== ПЛЕЕР ======
function openPlayerModal(rowId) {
  const release = allReleases.find(r => String(r.row_id) === String(rowId));
  if (!release) return;
  document.getElementById('playerArtist').textContent = release.artist || 'Unknown';
  document.getElementById('playerAlbum').textContent = release.album || '';
  const body = document.getElementById('playerBody');
  if (!release.album_link && !release.album_id) {
    body.innerHTML = `<div class="player-modal-no-link"><div class="icon">🎵</div><p>Ссылка на Apple Music отсутствует</p></div>`;
  } else {
    const embedUrl = release.album_link
      ? release.album_link.replace('music.apple.com', 'embed.music.apple.com').replace(/[?#].*$/, '') + '?app=music&itsct=music_box_player&itscg=30200&ls=1&theme=light'
      : `https://embed.music.apple.com/us/album/${release.album_id}?app=music&itsct=music_box_player&itscg=30200&ls=1&theme=light`;
    body.innerHTML = `<iframe src="${embedUrl}" allow="autoplay *; encrypted-media *; clipboard-write" sandbox="allow-forms allow-popups allow-same-origin allow-scripts allow-top-navigation-by-user-activation" style="width:100%;height:450px;border:none;border-radius:10px;background:#e4e4e4"></iframe>`;
  }
  document.getElementById('playerModal').classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closePlayerModal(event) {
  if (event && event.target !== event.currentTarget) return;
  document.getElementById('playerModal').classList.remove('active');
  document.getElementById('playerBody').innerHTML = '';
  document.body.style.overflow = '';
}

// ====== ПРОСМОТР ОБЛОЖКИ ======
function openImageModal(rowId, event) {
  if (event) event.stopPropagation();
  const release = allReleases.find(r => String(r.row_id) === String(rowId));
  if (!release || !release.cover_link) return;
  const fullUrl = release.cover_link
    .replace('296x296bb.webp', '10000x10000-999.jpg')
    .replace('296x296bf.webp', '10000x10000-999.jpg')
    .replace('296x296bf-60.jpg', '10000x10000-999.jpg');
  document.getElementById('imageModalImg').src = fullUrl;
  document.getElementById('imageModalImg').alt = release.artist || '';
  document.getElementById('imageModalArtist').textContent = release.artist || 'Unknown';
  document.getElementById('imageModalAlbum').textContent = release.album || '';
  document.getElementById('imageModal').classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeImageModal(event) {
  if (event && event.target !== event.currentTarget) return;
  document.getElementById('imageModal').classList.remove('active');
  document.getElementById('imageModalImg').src = '';
  document.body.style.overflow = '';
}

// ====== ФИЛЬТРАЦИЯ И СОРТИРОВКА ======
function getFilteredReleases() {
  return allReleases.filter(r => {
    const d = parseDate(r.update_date);
    if (!d) return false;
    if (currentYear === 'all') return true;
    if (d.getFullYear() !== currentYear) return false;
    if (currentMonth === 'all') return true;
    return d.getMonth() === currentMonth;
  });
}

function sortReleases(list) {
  const sorted = [...list];
  sorted.sort((a, b) => {
    const ta = TYPE_ORDER[a.my_type || ''] ?? 5;
    const tb = TYPE_ORDER[b.my_type || ''] ?? 5;
    if (ta !== tb) return ta - tb;
    if (sortMode === 'artist_asc') return (a.artist || '').localeCompare(b.artist || '', 'ru');
    const da = parseDate(a.update_date) || new Date(0);
    const db = parseDate(b.update_date) || new Date(0);
    return sortMode === 'date_asc' ? da - db : db - da;
  });
  return sorted;
}

// ====== РЕНДЕРИНГ ======
function buildYearMonthOptions() {
  const years = new Set();
  const yearMonths = {};
  allReleases.forEach(r => {
    const d = parseDate(r.update_date);
    if (!d) return;
    years.add(d.getFullYear());
    if (!yearMonths[d.getFullYear()]) yearMonths[d.getFullYear()] = new Set();
    yearMonths[d.getFullYear()].add(d.getMonth());
  });
  const yearsSorted = [...years].sort((a, b) => b - a);
  const yearSel = document.getElementById('yearSelect');
  const monthSel = document.getElementById('monthSelect');
  yearSel.innerHTML = yearsSorted.map(y => `<option value="${y}">${y}</option>`).join('') + `<option value="all">Вся БД</option>`;
  function updateMonths() {
    if (yearSel.value === 'all') {
      monthSel.disabled = true;
      monthSel.innerHTML = `<option>Вся БД</option>`;
      return;
    }
    monthSel.disabled = false;
    const months = yearMonths[parseInt(yearSel.value)] ? [...yearMonths[parseInt(yearSel.value)]].sort((a, b) => b - a) : [];
    monthSel.innerHTML = months.map(m => `<option value="${m}">${MONTHS_RU[m]}</option>`).join('') + `<option value="all">Весь год</option>`;
  }
  yearSel.addEventListener('change', () => {
    updateMonths();
    currentYear = yearSel.value === 'all' ? 'all' : parseInt(yearSel.value);
    currentMonth = monthSel.value === 'all' ? 'all' : parseInt(monthSel.value);
    render();
  });
  monthSel.addEventListener('change', () => {
    currentMonth = monthSel.value === 'all' ? 'all' : parseInt(monthSel.value);
    render();
  });
  if (yearsSorted.length) {
    currentYear = yearsSorted[0];
    yearSel.value = String(currentYear);
    updateMonths();
    currentMonth = parseInt(monthSel.value);
  }
}

function render() {
  const main = document.getElementById('mainContent');
  const releases = sortReleases(getFilteredReleases());
  if (!releases.length) {
    main.innerHTML = `<div class="empty-state"><div class="icon">📭</div><h3>Нет релизов</h3><p>Релизы ${getPeriodLabel()} не найдены.</p></div>`;
    return;
  }
  if (groupByDate) renderGroupedByDate(main, releases);
  else renderFlat(main, releases);
  if (activeTypes.size > 0) applyTypeFilter();
}

function renderGroupedByDate(main, releases) {
  const byDate = {};
  releases.forEach(r => {
    const d = parseDate(r.update_date);
    const key = dateKey(d);
    if (!byDate[key]) byDate[key] = {date: d, items: []};
    byDate[key].items.push(r);
  });
  const datesSorted = Object.values(byDate);
  datesSorted.sort((a, b) => sortMode === 'date_asc' ? a.date - b.date : b.date - a.date);
  let html = '';
  datesSorted.forEach(({date, items}) => {
    html += `<div class="date-group"><h2 class="date-header"><span class="date-text">${formatDateRu(date)}</span><span class="date-count">${items.length} релиз${plural(items.length)}</span></h2>`;
    html += renderGenreSections(items);
    html += `</div>`;
  });
  main.innerHTML = html;
}

function renderGenreSections(items) {
  const byGenre = {};
  items.forEach(r => {
    const g = getGenreGroup(r.genre_category);
    if (g) {
      if (!byGenre[g]) byGenre[g] = [];
      byGenre[g].push(r);
    }
  });
  let html = '';
  GROUP_ORDER.forEach(groupKey => {
    const genreItems = byGenre[groupKey];
    if (!genreItems || !genreItems.length) return;
    html += `<section class="genre-section" data-genre="${groupKey}"><h3 class="genre-title">${GROUP_LABELS[groupKey]} <span class="count">${genreItems.length}</span></h3><div class="releases-grid">`;
    genreItems.forEach(r => { html += renderCard(r); });
    html += `</div></section>`;
  });
  return html;
}

function renderFlat(main, releases) {
  main.innerHTML = `<div class="flat-summary">Найдено: ${releases.length} релиз${plural(releases.length)} ${getPeriodLabel()}</div><div class="releases-grid">${releases.map(r => renderCard(r)).join('')}</div>`;
}

function renderCard(r) {
  const name = escapeHtml(r.artist || 'Unknown');
  const album = escapeHtml(r.album || '');
  const cover = r.cover_link || '';
  const coverDisplay = cover
    .replace('296x296bb.webp', '632x632bb.webp')
    .replace('296x296bf.webp', '632x632bf.webp')
    .replace('296x296bf-60.jpg', '632x632bf-60.jpg');
  const currentType = r.my_type || '';
  const rowId = r.row_id;
  const myTypeAttr = currentType || 'empty';
  const TYPE_EMOJI = { 'v': '🔥', 'o': '👌', 'd': '🔍', 'x': '✖️' };

  const linkApple = r.album_link ? `<a class="link-btn am-active" href="${r.album_link}" target="_blank" rel="noopener" title="Apple Music" onclick="event.stopPropagation()">🎵</a>` : `<span class="link-btn disabled">🎵</span>`;
  const linkYM = r.album_link_ym ? `<a class="link-btn ym-active" href="${r.album_link_ym}" target="_blank" rel="noopener" title="Яндекс.Музыка" onclick="event.stopPropagation()">💥</a>` : `<span class="link-btn disabled">💥</span>`;
  const linkZV = r.album_link_zv ? `<a class="link-btn zv-active" href="${r.album_link_zv}" target="_blank" rel="noopener" title="Звук" onclick="event.stopPropagation()">🔊</a>` : `<span class="link-btn disabled">🔊</span>`;

  // Кнопки типов рендерятся ТОЛЬКО в режиме администратора
  let typeBtnsHtml = '';
  if (adminToken) {
    const types = ['v', 'o', 'd', 'x'];
    const typeBtns = types.map(t => {
      const active = currentType === t ? 'active' : '';
      return `<button class="type-btn ${active}" data-type="${t}" onclick="event.stopPropagation(); updateMyType(${rowId}, '${t}', this)" title="Установить тип '${t}'">${TYPE_EMOJI[t]}</button>`;
    }).join('');
    typeBtnsHtml = `<div class="type-buttons">${typeBtns}</div>`;
  }

  const imageIndicator = cover ? `<div class="image-indicator" onclick="openImageModal(${rowId}, event)" title="Открыть обложку"><svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg></div>` : '';

  return `<div class="release-card" data-row-id="${rowId}" data-my-type="${myTypeAttr}" onclick="openPlayerModal(${rowId})">
    <div class="cover-wrap">
      ${coverDisplay ? `<img src="${coverDisplay}" alt="${name}" loading="lazy" onerror="this.style.display='none'">` : ''}
      ${imageIndicator}
    </div>
    <div class="card-info">
      <div class="artist-name">${name}</div>
      <div class="album-name">${album}</div>
      <div class="links-row">${linkApple}${linkYM}${linkZV}</div>
      ${typeBtnsHtml}
    </div>
  </div>`;
}

// ====== ЗАГРУЗКА ДАННЫХ ======
async function loadData() {
  try {
    const r = await fetch(JSON_FILE + '?v=' + Date.now());
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    allReleases = cleanData(await r.json());
    document.getElementById('statusArea').style.display = 'none';
    buildYearMonthOptions();
    render();
  } catch (e) {
    console.error('Ошибка загрузки:', e);
    document.getElementById('mainContent').innerHTML = `
      <div class="empty-state">
        <div class="icon">❌</div>
        <h3>Ошибка загрузки</h3>
        <p>${e.message}</p>
        <p style="margin-top:10px">Локально: запустите <code>python server.py</code> из корня проекта.</p>
      </div>`;
  }
}

// ====== СОБЫТИЯ ======
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('tokenInput').addEventListener('keypress', e => { if (e.key === 'Enter') submitToken(); });
  document.getElementById('typeFilters').addEventListener('click', e => {
    const btn = e.target.closest('.type-filter-btn');
    if (btn) toggleTypeFilter(btn.dataset.type);
  });
  document.getElementById('groupByDateToggle').addEventListener('change', e => { groupByDate = e.target.checked; render(); });
  document.getElementById('sortSelect').addEventListener('change', e => { sortMode = e.target.value; render(); });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') { closeLoginModal(); closePlayerModal(); closeImageModal(); }
  });
  loadData();
});

// ====== СЖАТИЕ ШАПКИ ПРИ ПРОКРУТКЕ ======
(function () {
  const headerEl = document.querySelector('header');
  if (!headerEl) return;
  const onScroll = () => headerEl.classList.toggle('collapsed', window.scrollY > 60);
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
})();