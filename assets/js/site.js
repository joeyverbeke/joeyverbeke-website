(() => {
  const toggle = document.querySelector('.menu-toggle');
  const nav = document.querySelector('.site-nav');

  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const open = !nav.classList.contains('is-open');
      nav.classList.toggle('is-open', open);
      toggle.setAttribute('aria-expanded', String(open));
      toggle.querySelector('span').textContent = open ? 'Close' : 'Menu';
    });
  }

  const dialog = document.querySelector('.lightbox');
  if (!dialog) return;

  const image = dialog.querySelector('img');
  const caption = dialog.querySelector('figcaption');
  const close = dialog.querySelector('.lightbox-close');
  const previous = dialog.querySelector('.lightbox-prev');
  const next = dialog.querySelector('.lightbox-next');
  let items = [];
  let index = 0;
  let opener = null;

  const render = () => {
    const item = items[index];
    if (!item) return;
    image.src = item.dataset.lightboxSrc;
    image.alt = item.querySelector('img')?.alt || '';
    caption.textContent = item.dataset.lightboxCaption || '';
    caption.hidden = !caption.textContent;
    const multiple = items.length > 1;
    previous.hidden = !multiple;
    next.hidden = !multiple;
  };

  const step = (amount) => {
    if (!items.length) return;
    index = (index + amount + items.length) % items.length;
    render();
  };

  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-lightbox-src]');
    if (!button) return;
    opener = button;
    const gallery = button.closest('.gallery');
    items = Array.from(gallery.querySelectorAll('[data-lightbox-src]'));
    index = items.indexOf(button);
    render();
    dialog.showModal();
    close.focus();
  });

  close.addEventListener('click', () => dialog.close());
  previous.addEventListener('click', () => step(-1));
  next.addEventListener('click', () => step(1));
  dialog.addEventListener('click', (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener('close', () => {
    image.src = '';
    opener?.focus();
  });
  dialog.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') dialog.close();
    if (event.key === 'ArrowLeft') step(-1);
    if (event.key === 'ArrowRight') step(1);
  });
})();
