async function getBiometricStatus() {
  const token = localStorage.getItem("accessToken");

  const res = await fetch("http://localhost:8000/auth/me/biometric-status", {
    method: "GET",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    throw new Error(`HTTP_${res.status}`);
  }

  return res.json();
}

document.addEventListener("DOMContentLoaded", () => {
  const username = localStorage.getItem("portalUsername") || "User";
  const role = localStorage.getItem("portalRole") || "user";
  const enrollUrl = `../biometric/enroll.html?username=${encodeURIComponent(username)}&role=${encodeURIComponent(role)}`;

  const sidebarUsername = document.getElementById("sidebarUsername");
  const sidebarRole = document.getElementById("sidebarRole");

  const welcomeText = document.getElementById("welcomeText");
  const infoUsername = document.getElementById("infoUsername");
  const infoRole = document.getElementById("infoRole");

  if (sidebarUsername) sidebarUsername.textContent = username;
  if (sidebarRole) sidebarRole.textContent = role;

  if (welcomeText) {
    welcomeText.textContent =
      `Welcome ${username}. You can manage your biometric enrollment and verification from this portal.`;
  }

  if (infoUsername) infoUsername.textContent = username;
  if (infoRole) infoRole.textContent = role;

  const faceStatus = document.getElementById("faceStatus");
  const voiceStatus = document.getElementById("voiceStatus");

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
    .catch(() => {
      if (faceStatus) faceStatus.textContent = "Unavailable";
      if (voiceStatus) voiceStatus.textContent = "Unavailable";
    });

  document.getElementById("navEnroll").onclick = () => {
    window.location.href = enrollUrl;
  };

  document.getElementById("navVerify").onclick = () => {
    window.location.href = "../biometric/identify.html";
  };

  document.getElementById("btnQuickEnroll").onclick = () => {
    window.location.href = enrollUrl;
  };

  document.getElementById("btnQuickVerify").onclick = () => {
    window.location.href = "../biometric/identify.html";
  };

  document.getElementById("navLogout").onclick = () => {
    localStorage.clear();
    window.location.href = "./office_login.html";
  };
});