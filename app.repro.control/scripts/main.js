// Control: same calls in the opposite order. Runs and exits normally.
const timer = setInterval(() => {
  fetch("http://localhost/api/version");
  clearInterval(timer);
}, 100);
