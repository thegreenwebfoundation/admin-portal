document.addEventListener("DOMContentLoaded", (event) => {
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
});
