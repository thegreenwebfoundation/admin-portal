function setupOptionalDescriptionForms() {
  const descriptionFieldContainer = document.querySelector("div.description-field");
  const descriptionField = document.querySelector("input.description-field");
  document.querySelectorAll(".show-description-field").forEach((elem) => {
    const label = elem.closest("label");
    const input = label.querySelector("input");
    if(input.checked) {
      descriptionFieldContainer.classList.remove("hidden");
      descriptionField.classList.remove("hidden");
      descriptionField.required = true;
    } else {
      descriptionField.required = false;
    }
    input.addEventListener("change", (event) => {
      descriptionFieldContainer.classList.toggle("hidden");
      descriptionField.classList.toggle("hidden");
      descriptionField.required = !descriptionField.classList.contains("hidden");
    });
  });
}

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

function setupEmbeddedGreenchecker() {
  const greencheckers = document.querySelectorAll(".embedded-greenchecker");
  for(const greenchecker of greencheckers) {
    const field = greenchecker.querySelector(".domain-input");
    const button = greenchecker.querySelector(".submit");
    const spinner = greenchecker.querySelector(".spinner");
    const greenResult = greenchecker.querySelector(".green-result");
    const greyResult = greenchecker.querySelector(".grey-result");
    const domainDisplays = greenchecker.querySelectorAll(".domain");
    const providerDisplays = greenchecker.querySelectorAll(".provider-name");
    const checkAgainLinks = greenchecker.querySelectorAll(".check-again");
    const submitHandler = (event) => {
      button.classList.add("hidden");
      greenResult.classList.add("hidden");
      greyResult.classList.add("hidden");
      spinner.classList.remove("hidden");
      event.preventDefault();
      const domain = field.value;
      fetch(`/api/v3/greencheck/${domain}?nocache=true`).then(async (response) => {
        button.classList.remove("hidden");
        spinner.classList.add("hidden");
        const result = await response.json();
        console.log(result);
        for(display of domainDisplays) {
          display.innerText = domain;
        }
        if(result.green) {
          for(display of providerDisplays) {
            display.innerText = result.hosted_by;
          }
          greenResult.classList.remove("hidden");
        } else {
          greyResult.classList.remove("hidden");
        }
      }).catch(async (error) => {
        console.log(error);
        button.classList.remove("hidden");
        spinner.classList.add("hidden");
      });
    };
    field.addEventListener("keypress", (event)  => {
      if(event.key === "Enter") {
        submitHandler(event);
      }
    });
    button.addEventListener("click", submitHandler);
    for (const checkAgainLink of checkAgainLinks) {
      checkAgainLink.addEventListener("click", (event) => {
        event.preventDefault();
        field.value = "";
        button.classList.remove("hidden");
        spinner.classList.add("hidden");
        greenResult.classList.add("hidden");
        greyResult.classList.add("hidden");
        field.focus()
      });
    }
  }
}


document.addEventListener("DOMContentLoaded", (event) => {
  setupOptionalDescriptionForms();
  setupCopyables();
  setupEmbeddedGreenchecker();
});
