// basit page history: prevPath / lastPath
export function trackPrevPage() {
  try {
    const last = sessionStorage.getItem("lastPath");
    sessionStorage.setItem("prevPath", last || "");
    sessionStorage.setItem("lastPath", window.location.pathname);
  } catch {}
}

export function goBack(fallback = "/portal/login_portal.html") {
  const prevPath = sessionStorage.getItem("prevPath");

  // Eğer prevPath varsa oraya dön
  if (prevPath) {
    window.location.href = prevPath;
    return;
  }

  // yoksa browser back dene
  if (window.history.length > 1) {
    window.history.back();
    return;
  }

  // en son fallback
  window.location.href = fallback;
}