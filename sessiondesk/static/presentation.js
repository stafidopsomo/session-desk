export function drawPresentationTabs(root, state, action) {
  if (!root) return;
  const stamp = JSON.stringify(state);
  if (root.dataset.presentation === stamp) return;
  root.dataset.presentation = stamp;
  root.replaceChildren();
  const addButton = (parent, title, handler, label) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = title;
    if (label) button.setAttribute('aria-label', label);
    button.onclick = handler;
    parent.append(button);
    return button;
  };

  for (const tab of state.tabs) {
    const current = tab.source === state.active?.source && tab.id === state.active.id;
    const group = document.createElement('div');
    group.className = 'tab' + (current ? ' active' : '');
    const send = verb => action({action: verb, source: tab.source, id: tab.id});
    addButton(group, tab.title, () => send('activate'), 'Show ' + tab.title)
      .setAttribute('aria-pressed', String(current));
    addButton(group, '×', () => send('close'), 'Close ' + tab.title);
    root.append(group);
  }
  if (state.tabs.length) {
    addButton(root, 'Close all', () => action({action: 'close_all'})).className = 'quiet';
  } else {
    const placeholder = document.createElement('small');
    placeholder.className = 'muted';
    placeholder.textContent = 'Nothing is being presented.';
    root.append(placeholder);
  }
}

export function mountWorkspacePlayer(root, {workspace, token, request}) {
  root.innerHTML = '<main class="player workspace-player"><header class="toolbar">'
    + '<div class="brand"><img src="/icon.svg" alt="">Session Desk</div>'
    + '<span class="grow"></span><span class="offline" aria-live="polite"></span></header>'
    + '<nav class="tabs" aria-label="Shared presentation tabs"></nav>'
    + '<section class="workspace-player-stage" aria-label="Player display"></section></main>';
  const strip = root.querySelector('nav');
  const stage = root.querySelector('section');
  const status = root.querySelector('.offline');
  const frames = new Map();
  let requestNumber = 0;
  let actions = Promise.resolve();

  function show(state) {
    drawPresentationTabs(strip, state, change);
    const sources = new Set(state.tabs.map(tab => tab.source));
    for (const [source, frame] of frames) {
      if (!sources.has(source)) {
        frame.remove();
        frames.delete(source);
      }
    }
    const source = state.active?.source;
    if (source && !frames.has(source)) {
      const frame = document.createElement('iframe');
      const route = new URL('/', location.href);
      route.search = new URLSearchParams({view: 'player', workspace, embed: '1',
        ...(source === 'prepared' ? {prepared: '1'} : {adventure: source})});
      route.hash = 'player=' + token;
      frame.title = 'Presented material';
      frame.src = route;
      frames.set(source, frame);
      stage.append(frame);
    }
    for (const [id, frame] of frames) {
      frame.inert = id !== source;
      frame.setAttribute('aria-hidden', String(id !== source));
    }
  }

  function change(payload) {
    actions = actions.then(async () => {
      const number = ++requestNumber;
      try {
        const state = await request('presentation/action', payload);
        if (number === requestNumber) show(state);
        status.textContent = '';
      } catch (error) {
        status.textContent = error.message;
      }
    });
  }

  async function poll() {
    await actions;
    const number = ++requestNumber;
    try {
      const state = await request('presentation');
      if (number === requestNumber) {
        show(state);
        status.textContent = '';
      }
    } catch {
      if (number === requestNumber) status.textContent = 'Reconnecting to Session Desk…';
    } finally {
      setTimeout(poll, 650);
    }
  }

  poll();
}
