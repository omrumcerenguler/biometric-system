import { trackPrevPage } from "./navigation.js";

trackPrevPage();

const FRONTEND_ASSET_VERSION = "20260314-liveness-preview";

const page = document.body.dataset.page;

async function boot() {
  try {
    if (page === "enroll") {
      const mod = await import(`./enroll.js?v=${FRONTEND_ASSET_VERSION}`);
      mod.initEnroll();
      return;
    }

    if (page === "identify") {
      const mod = await import(`./identify.js?v=${FRONTEND_ASSET_VERSION}`);
      mod.initIdentify();
    }
  } catch (err) {
    console.error("[BOOT ERROR]", err);
  }
}

boot();