/**
 * Backward compatibility wrapper for SelfHeal IT legacy functions.
 */
function legacyScan() {
  if (typeof runScan === 'function') runScan();
}

function legacyHeal(a) {
  if (typeof promptHealAction === 'function') {
    promptHealAction(a, 'Execute ' + a);
  }
}

function legacyAsk() {
  if (typeof sendChatMessage === 'function') {
    const qEl = document.getElementById('q');
    if (qEl && qEl.value) {
      document.getElementById('chat-input').value = qEl.value;
      qEl.value = '';
    }
    sendChatMessage();
  }
}

function legacyLoopDemo() {
  if (typeof runLoopDemo === 'function') runLoopDemo();
}

// Preserve global names for legacy bindings
window.scan = window.scan || legacyScan;
window.heal = window.heal || legacyHeal;
window.ask = window.ask || legacyAsk;
window.loopDemo = window.loopDemo || legacyLoopDemo;
