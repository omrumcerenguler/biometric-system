async function getBiometricStatus() {
  const token = localStorage.getItem("accessToken");

  if (!token) {
    throw new Error("AUTH_REQUIRED");
  }

  const res = await fetch("http://localhost:8000/auth/me/biometric-status", {
    method: "GET",
    headers: {
      Accept: "application/json",
      "X-Client": "portal",
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    throw new Error(`HTTP_${res.status}`);
  }

  return res.json();
}

document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("accessToken");
  const isLoggedIn = localStorage.getItem("portalLoggedIn") === "true";

  if (!token || !isLoggedIn) {
    localStorage.clear();
    window.location.href = "./office_login.html";
    return;
  }

  const username = localStorage.getItem("portalUsername") || "User";
  const role = localStorage.getItem("portalRole") || "user";

  const enrollUrl = `../biometric/enroll.html?username=${encodeURIComponent(
    username
  )}&role=${encodeURIComponent(role)}`;

  const sidebarUsername = document.getElementById("sidebarUsername");
  const sidebarRole = document.getElementById("sidebarRole");

  const welcomeText = document.getElementById("welcomeText");
  const infoUsername = document.getElementById("infoUsername");
  const infoRole = document.getElementById("infoRole");

  const faceStatus = document.getElementById("faceStatus");
  const voiceStatus = document.getElementById("voiceStatus");
  const portalStatus = document.getElementById("portalStatus");

  if (sidebarUsername) sidebarUsername.textContent = username;
  if (sidebarRole) sidebarRole.textContent = role;

  if (welcomeText) {
    welcomeText.textContent = `Welcome ${username}. You can manage your biometric enrollment and verification from this portal.`;
  }

  if (infoUsername) infoUsername.textContent = username;
  if (infoRole) infoRole.textContent = role;

  if (portalStatus) {
    portalStatus.textContent = "Active";
  }

  getBiometricStatus()
    .then((data) => {
      if (faceStatus) {
        faceStatus.textContent = data.face_enrolled
          ? "Enrolled"
          : "Not Enrolled";
      }

      if (voiceStatus) {
        voiceStatus.textContent = data.voice_enrolled
          ? "Enrolled"
          : "Not Enrolled";
      }
    })
    .catch((error) => {
      console.error("[PORTAL BIOMETRIC STATUS ERROR]", error);

      if (
        error.message === "AUTH_REQUIRED" ||
        error.message === "HTTP_401" ||
        error.message === "HTTP_403"
      ) {
        localStorage.clear();
        window.location.href = "./office_login.html";
        return;
      }

      if (faceStatus) faceStatus.textContent = "Unavailable";
      if (voiceStatus) voiceStatus.textContent = "Unavailable";
    });

  const navEnroll = document.getElementById("navEnroll");
  const navVerify = document.getElementById("navVerify");
  const btnQuickEnroll = document.getElementById("btnQuickEnroll");
  const btnQuickVerify = document.getElementById("btnQuickVerify");
  const navLogout = document.getElementById("navLogout");

  if (navEnroll) {
    navEnroll.onclick = () => {
      window.location.href = enrollUrl;
    };
  }

  if (navVerify) {
    navVerify.onclick = () => {
      window.location.href = "../biometric/identify.html";
    };
  }

  if (btnQuickEnroll) {
    btnQuickEnroll.onclick = () => {
      window.location.href = enrollUrl;
    };
  }

  if (btnQuickVerify) {
    btnQuickVerify.onclick = () => {
      window.location.href = "../biometric/identify.html";
    };
  }

  if (navLogout) {
    navLogout.onclick = () => {
      localStorage.clear();
      window.location.href = "./office_login.html";
    };
  }
});