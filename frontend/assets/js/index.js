import { trackPrevPage } from "./navigation.js";
import { initEnroll } from "./enroll.js";
import { initIdentify } from "./identify.js";

trackPrevPage();

const page = document.body.dataset.page;

if (page === "enroll") {
  initEnroll();
}

if (page === "identify") {
  initIdentify();
}