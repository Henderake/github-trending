const toggleBtn = document.getElementById('sidebar-toggle');
const sidebar = document.getElementById('sidebar');
const generatedAt = document.getElementById('generated-at');
let lockHighlightUntil = 0;
let lockTimer;

if (generatedAt?.dateTime) {
  const generatedDate = new Date(generatedAt.dateTime);
  if (!Number.isNaN(generatedDate.getTime())) {
    const formatter = new Intl.DateTimeFormat(undefined, {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZoneName: 'short',
      hour12: false,
    });
    generatedAt.textContent = formatter.format(generatedDate);
    generatedAt.title = `UTC ${generatedAt.dateTime}`;
  }
}

toggleBtn?.addEventListener('click', () => {
  const open = sidebar.classList.toggle('open');
  toggleBtn.setAttribute('aria-expanded', String(open));
});

const links = Array.from(document.querySelectorAll('.sidebar a[data-target]'));
const sections = links.map((link) => document.getElementById(link.dataset.target)).filter(Boolean);
const groupToggles = Array.from(document.querySelectorAll('.group-toggle'));

const setActive = (id) => {
  links.forEach((link) => {
    const isActive = link.dataset.target === id;
    link.classList.toggle('active', isActive);
    if (!isActive) {
      return;
    }

    const groupId = link.dataset.group;
    const submenu = document.getElementById(groupId);
    const button = document.querySelector(`.group-toggle[data-group='${groupId}']`);
    submenu?.classList.remove('closed');
    button?.setAttribute('aria-expanded', 'true');

    const caret = button?.querySelector('.caret');
    if (caret) {
      caret.textContent = '▾';
    }
  });
};

groupToggles.forEach((button) => {
  const target = document.getElementById(button.dataset.group);
  const caret = button.querySelector('.caret');

  button.addEventListener('click', () => {
    const closed = target.classList.toggle('closed');
    button.setAttribute('aria-expanded', String(!closed));
    if (caret) {
      caret.textContent = closed ? '▸' : '▾';
    }
  });
});

document.querySelectorAll('.sidebar a').forEach((link) => {
  link.addEventListener('click', () => {
    const targetId = link.dataset.target;
    setActive(targetId);
    lockHighlightUntil = Date.now() + 1500;
    clearTimeout(lockTimer);
    lockTimer = setTimeout(() => {
      lockHighlightUntil = 0;
      updateActiveByScroll();
    }, 1550);
    sidebar.classList.remove('open');
    toggleBtn?.setAttribute('aria-expanded', 'false');
  });
});

const updateActiveByScroll = () => {
  if (Date.now() < lockHighlightUntil) {
    return;
  }

  const targetLine = window.innerHeight * 0.35;
  let bestId = sections[0]?.id;
  let bestScore = Infinity;

  sections.forEach((section) => {
    const rect = section.getBoundingClientRect();
    const withinView = rect.bottom > 60 && rect.top < window.innerHeight * 0.75;
    if (!withinView) {
      return;
    }

    const score = Math.abs(rect.top - targetLine);
    if (score < bestScore) {
      bestScore = score;
      bestId = section.id;
    }
  });

  if (bestId) {
    setActive(bestId);
  }
};

window.addEventListener('scroll', updateActiveByScroll, { passive: true });
window.addEventListener('resize', updateActiveByScroll);
updateActiveByScroll();
