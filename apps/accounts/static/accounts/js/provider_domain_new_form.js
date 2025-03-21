document.addEventListener("DOMContentLoaded", (event) => {
  const tablist = document.querySelector(".tabbedview");
  for (const tab of tablist.querySelectorAll(".tab")) {
    tab.addEventListener("click", (event) => {
      for (const tab2 of tablist.querySelectorAll(".tab")) {
        tab2.setAttribute("aria-expanded", "false");
        tab2.classList.add("bg-neutral-200", "hover:bg-neutral-100");
      };
      event.preventDefault();
      for(const panel of tablist.querySelectorAll(".panel")) {
        panel.classList.add("hidden");
      };
      const panel = document.getElementById(tab.getAttribute("aria-controls"));
      panel.classList.remove("hidden");
      tab.setAttribute("aria-expanded", "true")
      tab.classList.remove("bg-neutral-200", "hover:bg-neutral-100");
    });
  };

  const copyables = document.querySelectorAll(".copyable");
  for(const copyable of copyables) {
    const link = copyable.querySelector(".copy");
    const code = copyable.querySelector("code");
    link.addEventListener("click", (event) => {
      event.preventDefault();
      navigator.clipboard.writeText(code.innerText);
      link.innerText="✅"
      window.setTimeout((event) => {
        link.innerText="📋"
      }, 1000);
    });
  }
});
