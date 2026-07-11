function setupCopyables() {
  const copyables = document.querySelectorAll(".copyable");
  for(const copyable of copyables) {
    const link = copyable.querySelector(".copy");
    const content = copyable.querySelector(".content");
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const text = content.tagName == "A" ? content.getAttribute("href") : content.innerText;
      navigator.clipboard.writeText(text);
      link.innerText="✅"
      window.setTimeout((event) => {
        link.innerText="📋"
      }, 1000);
    });
  }
}

document.addEventListener("DOMContentLoaded", (event) => {
  setupCopyables();
});
