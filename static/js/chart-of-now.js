(function() {
  const IDLE_TIMEOUT = 30 * 60 * 1000; // 30 minutes
  let idleTimer;

  function resetIdleTimer() {
    clearTimeout(idleTimer);
    idleTimer = setTimeout(refreshChart, IDLE_TIMEOUT);
  }

  function refreshChart() {
    if (typeof htmx !== 'undefined') {
      htmx.ajax('GET', '/chart-of-now/', {target: '#chart-of-now-widget', swap: 'innerHTML'});
    }
  }

  // Reset timer on user activity
  ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'].forEach(function(event) {
    document.addEventListener(event, resetIdleTimer, { passive: true });
  });

  // Start timer on page load
  resetIdleTimer();
})();
