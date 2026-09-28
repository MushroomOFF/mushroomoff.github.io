// ====== КОНСТАНТЫ ======
const JSON_FILE = 'soon_releases.json';
const MONTHS_RU = ['Январь','Февраль','Март','Апрель','Май','Июнь',
'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];

const TODAY = new Date();
TODAY.setHours(0, 0, 0, 0);

// ====== СОСТОЯНИЕ ======
let allReleases = [];
let currentYear = 'upcoming';
let currentMonth = 'all';
let groupByDate = true;
let myArtistsOnly = false;
let sortMode = 'date_asc';

// ====== УТИЛИТЫ ======
function parseDate(str) {
  if (!str) return null;
  const d = new Date(str);
  return isNaN(d) ? null : d;
}

function formatDateRu(date) {
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
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
  if (currentYear === 'upcoming') return 'предстоящие';
  if (currentMonth === 'all') return `за ${currentYear} год`;
  return `в ${MONTHS_RU[currentMonth].toLowerCase()} ${currentYear}`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
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

// ====== ФИЛЬТРАЦИЯ ======
function getFilteredReleases() {
  let list = allReleases.filter(r => {
    const d = parseDate(r.release_date);
    if (!d) return false;

    if (currentYear === 'upcoming') {
      return d >= TODAY;
    }

    if (d.getFullYear() !== currentYear) return false;

    if (currentMonth === 'all') return true;
    return d.getMonth() === currentMonth;
  });

  if (myArtistsOnly) {
    list = list.filter(r => r.my_artist === 1 || r.my_artist === '1');
  }

  return list;
}

// ====== СОРТИРОВКА ======
function sortReleases(list) {
  const sorted = [...list];
  sorted.sort((a, b) => {
    if (sortMode === 'artist_asc') {
      return (a.artist_name || '').localeCompare(b.artist_name || '', 'ru');
    }
    if (sortMode === 'artist_desc') {
      return (b.artist_name || '').localeCompare(a.artist_name || '', 'ru');
    }
    const da = parseDate(a.release_date) || new Date(0);
    const db = parseDate(b.release_date) || new Date(0);
    if (sortMode === 'date_asc') return da - db;
    return db - da;
  });
  return sorted;
}

// ====== РЕНДЕРИНГ ======
function buildYearMonthOptions() {
  const years = new Set();
  const yearMonths = {};

  allReleases.forEach(r => {
    const d = parseDate(r.release_date);
    if (!d) return;
    years.add(d.getFullYear());
    if (!yearMonths[d.getFullYear()]) yearMonths[d.getFullYear()] = new Set();
    yearMonths[d.getFullYear()].add(d.getMonth());
  });

  const yearsSorted = [...years].sort((a, b) => b - a);
  const yearSel = document.getElementById('yearSelect');
  const monthSel = document.getElementById('monthSelect');

  yearSel.innerHTML =
    `<option value="upcoming">Предстоящие</option>` +
    yearsSorted.map(y => `<option value="${y}">${y}</option>`).join('');

  function updateMonths() {
    if (yearSel.value === 'upcoming') {
      monthSel.disabled = true;
      monthSel.innerHTML = `<option>Все даты</option>`;
      return;
    }
    monthSel.disabled = false;
    const months = yearMonths[parseInt(yearSel.value)]
      ? [...yearMonths[parseInt(yearSel.value)]].sort((a, b) => a - b)
      : [];
    monthSel.innerHTML =
      `<option value="all">Весь год</option>` +
      months.map(m => `<option value="${m}">${MONTHS_RU[m]}</option>`).join('');
  }

  yearSel.addEventListener('change', () => {
    currentYear = yearSel.value === 'upcoming' ? 'upcoming' : parseInt(yearSel.value);
    updateMonths();
    currentMonth = 'all';
    render();
  });

  monthSel.addEventListener('change', () => {
    currentMonth = monthSel.value === 'all' ? 'all' : parseInt(monthSel.value);
    render();
  });

  currentYear = 'upcoming';
  yearSel.value = 'upcoming';
  updateMonths();
  currentMonth = 'all';
}

function render() {
  const main = document.getElementById('mainContent');
  const releases = sortReleases(getFilteredReleases());

  if (!releases.length) {
    main.innerHTML = `<div class="empty-state"><div class="icon">📭</div><h3>Нет релизов</h3><p>Релизы (${getPeriodLabel()}) не найдены.</p></div>`;
    return;
  }

  if (groupByDate) {
    renderGroupedByDate(main, releases);
  } else {
    renderFlat(main, releases);
  }
}

function renderGroupedByDate(main, releases) {
  const byDate = {};
  releases.forEach(r => {
    const d = parseDate(r.release_date);
    if (!d) return;
    const key = dateKey(d);
    if (!byDate[key]) byDate[key] = { date: d, items: [] };
    byDate[key].items.push(r);
  });

  const datesSorted = Object.values(byDate);
  datesSorted.sort((a, b) => {
    if (sortMode === 'date_desc') return b.date - a.date;
    return a.date - b.date;
  });

  let html = '';
  datesSorted.forEach(({ date, items }) => {
    html += `<div class="date-group">`;
    html += `<h2 class="date-header"><span class="date-text">${formatDateRu(date)}</span><span class="date-count">${items.length} релиз${plural(items.length)}</span></h2>`;
    html += `<div class="releases-grid">`;
    items.forEach(r => { html += renderCard(r); });
    html += `</div></div>`;
  });

  main.innerHTML = html;
}

function renderFlat(main, releases) {
  let html = `<div class="flat-summary">Найдено: ${releases.length} релиз${plural(releases.length)} (${getPeriodLabel()})</div>`;
  html += `<div class="releases-grid">`;
  releases.forEach(r => { html += renderCard(r); });
  html += `</div>`;
  main.innerHTML = html;
}

function renderCard(r) {
  const name = escapeHtml(r.artist_name || 'Unknown');
  const album = escapeHtml(r.album_name || '');
  const cover = r.cover_link || '';
  const coverDisplay = cover.replace('296x296bf-60.jpg', '632x632bf-60.jpg');
  const isMyArtist = r.my_artist === 1 || r.my_artist === '1';
  const rowId = r.row_id;

  const releaseDateText = r.release_date_text || '';

  const linkApple = r.album_link
    ? `<a class="link-btn am-active" href="${r.album_link}" target="_blank" rel="noopener" title="Apple Music" onclick="event.stopPropagation()">🎵 Apple Music</a>`
    : `<span class="link-btn disabled">🎵</span>`;

  const myArtistClass = isMyArtist ? ' my-artist' : '';

  const imageIndicator = cover
    ? `<div class="image-indicator" onclick="openImageModal(${rowId}, event)" title="Открыть обложку"><svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg></div>`
    : '';

  return `<div class="release-card${myArtistClass}" data-row-id="${rowId}" onclick="openPlayerModal(${rowId})">
  <div class="cover-wrap">
    ${coverDisplay ? `<img src="${coverDisplay}" alt="${name}" loading="lazy" onerror="this.style.display='none'">` : ''}
    ${imageIndicator}
  </div>
  <div class="card-info">
    <div class="artist-name">${name}</div>
    <div class="album-name">${album}</div>
    ${releaseDateText ? `<div class="release-date-text">📅 ${escapeHtml(releaseDateText)}</div>` : ''}
    <div class="links-row">${linkApple}</div>
  </div>
</div>`;
}

// ====== ПЛЕЕР ======
function openPlayerModal(rowId) {
  const release = allReleases.find(r => String(r.row_id) === String(rowId));
  if (!release) return;

  document.getElementById('playerArtist').textContent = release.artist_name || 'Unknown';
  document.getElementById('playerAlbum').textContent = release.album_name || '';

  const body = document.getElementById('playerBody');
  if (!release.album_link) {
    body.innerHTML = `<div class="player-modal-no-link"><div class="icon">🎵</div><p>Ссылка на Apple Music отсутствует</p></div>`;
  } else {
    const embedUrl = release.album_link
      .replace('music.apple.com', 'embed.music.apple.com')
      .replace(/[?#].*$/, '')
      + '?app=music&itsct=music_box_player&itscg=30200&ls=1&theme=light';
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

  const fullUrl = release.cover_link.replace('296x296bf-60.jpg', '10000x10000-999.jpg');
  document.getElementById('imageModalImg').src = fullUrl;
  document.getElementById('imageModalImg').alt = release.artist_name || '';
  document.getElementById('imageModalArtist').textContent = release.artist_name || 'Unknown';
  document.getElementById('imageModalAlbum').textContent = release.album_name || '';
  document.getElementById('imageModal').classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeImageModal(event) {
  if (event && event.target !== event.currentTarget) return;
  document.getElementById('imageModal').classList.remove('active');
  document.getElementById('imageModalImg').src = '';
  document.body.style.overflow = '';
}

// ====== ЗАГРУЗКА ДАННЫХ ======
async function loadData() {
  try {
    const r = await fetch(JSON_FILE + '?v=' + Date.now());
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    allReleases = await r.json();
    document.getElementById('statusArea').style.display = 'none';
    buildYearMonthOptions();
    render();
  } catch (e) {
    console.error('Ошибка загрузки:', e);
    document.getElementById('mainContent').innerHTML =
      `<div class="empty-state"><div class="icon">❌</div><h3>Ошибка загрузки</h3><p>${e.message}</p></div>`;
  }
}

// ====== СОБЫТИЯ ======
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('groupByDateToggle').addEventListener('change', e => {
    groupByDate = e.target.checked;
    render();
  });

  document.getElementById('myArtistsToggle').addEventListener('change', e => {
    myArtistsOnly = e.target.checked;
    render();
  });

  document.getElementById('sortSelect').addEventListener('change', e => {
    sortMode = e.target.value;
    render();
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      closePlayerModal();
      closeImageModal();
    }
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

// ====== СТРОКА-УКАЗАТЕЛЬ ПРИ ПРОКРУТКЕ ======
(function () {
  const bar = document.getElementById('scrollBreadcrumb');
  if (!bar) return;
  let ticking = false;
  let lastKey = '';

  function findCurrentDateGroup() {
    const headerEl = document.querySelector('header');
    const line = (headerEl ? headerEl.offsetHeight : 56) + 12;
    let current = null;
    document.querySelectorAll('.date-group').forEach(dg => {
      if (dg.getBoundingClientRect().top <= line) current = dg;
    });
    return current;
  }

  function update() {
    ticking = false;
    const headerEl = document.querySelector('header');
    const dg = findCurrentDateGroup();

    if (!dg || !headerEl || !headerEl.classList.contains('collapsed')) {
      bar.classList.remove('visible');
      lastKey = '';
      return;
    }

    const dateEl = dg.querySelector('.date-text');
    const dateText = dateEl ? dateEl.textContent.trim() : '';

    if (dateText !== lastKey) {
      bar.innerHTML = `<span class="crumb-date">${escapeHtml(dateText)}</span>`;
      lastKey = dateText;
    }
    bar.classList.add('visible');
  }

  function onScroll() {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(update);
    }
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  onScroll();
})();