// frontend/assets/js/portal.js

window.portal = {
  init() {
    console.log("[PORTAL] init");

    const biometricBtn = document.getElementById("btn-biometric-login");

    if (biometricBtn) {
      biometricBtn.addEventListener("click", (e) => {
        e.preventDefault();
        window.location.href = "../biometric/identify.html";
      });
    }
  },
};

document.addEventListener("DOMContentLoaded", () => {
  window.portal.init();
});