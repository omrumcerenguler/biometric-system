import { apiLogin } from "./api.js";


window.portal = {
  init() {
    console.log("[PORTAL] init");

    const biometricBtn = document.getElementById("btn-biometric-login");
    const loginForm = document.getElementById("portalLoginForm");
    const signInBtn = document.getElementById("btnSignIn");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");
    const loginMessage = document.getElementById("loginMessage");

    if (biometricBtn) {
      biometricBtn.addEventListener("click", (e) => {
        e.preventDefault();
        window.location.href = "../biometric/identify.html";
      });
    }

    async function handleLogin() {
      console.log("[PORTAL] login handler triggered");

      const username = usernameInput ? usernameInput.value.trim() : "";
      const password = passwordInput ? passwordInput.value.trim() : "";

      console.log("[PORTAL] username:", username);

      if (!username || !password) {
        if (loginMessage) {
          loginMessage.textContent = "Please enter username and password.";
        }
        return;
      }

      try {
        const data = await apiLogin(username, password);
        console.log("[PORTAL] response data:", data);

        if (loginMessage) {
          loginMessage.textContent = "Login successful. Redirecting...";
        }

        localStorage.setItem("bankUsername", data.username);
        localStorage.setItem("bankRole", data.role);
        localStorage.setItem("bankLoggedIn", "true");
        localStorage.setItem("accessToken", data.access_token);

        setTimeout(() => {
          window.location.href = "../portal/dashboard_portal.html";
        }, 600);
      } catch (error) {
        console.error("[PORTAL LOGIN ERROR]", error);
        if (loginMessage) {
          loginMessage.textContent =
            error.message === "NETWORK_ERROR"
              ? "Could not connect to the server."
              : error.message || "Login failed.";
        }
      }
    }

    if (loginForm) {
      console.log("[PORTAL] login form found");

      loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        await handleLogin();
      });
    }

    if (signInBtn) {
      console.log("[PORTAL] sign-in button found");

      signInBtn.addEventListener("click", async () => {
        await handleLogin();
      });
    }
  },
};

document.addEventListener("DOMContentLoaded", () => {
  window.portal.init();
});