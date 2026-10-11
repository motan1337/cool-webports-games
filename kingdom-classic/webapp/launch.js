const button = document.querySelector('button');
const status = document.querySelector('[role="status"]');
const frame = document.querySelector('iframe');
const expectedWorker = new URL('asset-worker.js?v=__BUILD_ID__', location.href).href;

window.addEventListener('message', event => {
  if (event.origin !== location.origin || event.source !== frame.contentWindow || event.data !== 'kingdom-exit') return;
  frame.hidden = true;
  frame.src = 'about:blank';
  document.querySelector('main').hidden = false;
  status.textContent = 'Game saved.';
  button.disabled = false;
  button.focus();
});

function waitFor(check, subscribe, message) {
  return new Promise((resolve, reject) => {
    let timeout;
    const finish = () => {
      if (!check()) return;
      clearTimeout(timeout);
      subscribe(finish, false);
      resolve();
    };
    subscribe(finish, true);
    timeout = setTimeout(() => {
      subscribe(finish, false);
      reject(new Error(message));
    }, 30000);
    finish();
  });
}

button.addEventListener('click', async () => {
  button.disabled = true;
  status.textContent = 'Preparing game files...';
  try {
    if (!('serviceWorker' in navigator)) throw new Error('This browser cannot load the segmented game files.');
    const registration = await navigator.serviceWorker.register(expectedWorker, { scope: './', updateViaCache: 'none' });
    const worker = registration.installing || registration.waiting || registration.active;
    if (!worker) throw new Error('The asset loader could not start.');
    await waitFor(() => worker.state === 'activated', (callback, add) => {
      worker[add ? 'addEventListener' : 'removeEventListener']('statechange', callback);
    }, 'The asset loader did not activate. Reload and try again.');
    await waitFor(() => navigator.serviceWorker.controller && navigator.serviceWorker.controller.scriptURL === expectedWorker,
      (callback, add) => navigator.serviceWorker[add ? 'addEventListener' : 'removeEventListener']('controllerchange', callback),
      'The page did not receive the new asset loader. Reload and try again.');
    frame.src = './game/index.html';
    frame.hidden = false;
    document.querySelector('main').hidden = true;
    frame.focus();
  } catch (error) {
    status.textContent = error.message;
    button.disabled = false;
  }
});
