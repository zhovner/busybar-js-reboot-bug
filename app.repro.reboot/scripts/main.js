// Reboots BUSY Bar (fw 1.3.1): fetch() called inside a setInterval callback
// after clearInterval() on that same interval.
const timer = setInterval(() => {
  clearInterval(timer);
  fetch("http://localhost/api/version");
}, 100);
