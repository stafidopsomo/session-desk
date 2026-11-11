/* A local visual preference. Does not call the campaign API or change play. */
(() => {
  const key = 'campaign-appearance';
  const valid = value => value === 'slate' || value === 'classic';
  const params = new URLSearchParams(location.search);
  let saved = 'classic';
  try { const value = localStorage.getItem(key); if (valid(value)) saved = value; } catch {}
  const preview = params.get('skin');
  document.documentElement.dataset.skin = valid(preview) ? preview : saved;

  function mount() {
    const popover = document.querySelector('.display-popover');
    if (!popover) return;
    const label = document.createElement('label');
    label.className = 'appearance-control';
    label.htmlFor = 'appearanceSkin';
    label.append('Appearance');
    const select = document.createElement('select');
    select.id = 'appearanceSkin';
    select.add(new Option('Classic · forest', 'classic'));
    select.add(new Option('Slate · clear contrast', 'slate'));
    select.value = document.documentElement.dataset.skin;
    label.append(select);
    popover.prepend(label);
    select.addEventListener('change', () => {
      if (!valid(select.value)) return;
      document.documentElement.dataset.skin = select.value;
      try { localStorage.setItem(key, select.value); } catch {}
      // An explicit choice must win over the preview URL on the next reload.
      const url = new URL(location.href);
      url.searchParams.delete('skin');
      history.replaceState(history.state, '', url);
    });
    addEventListener('storage', event => {
      if (event.key !== key || !valid(event.newValue)) return;
      if (valid(new URLSearchParams(location.search).get('skin'))) return;
      document.documentElement.dataset.skin = event.newValue;
      select.value = event.newValue;
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, {once:true});
  else mount();
})();
