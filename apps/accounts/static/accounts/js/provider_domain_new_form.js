document.addEventListener("DOMContentLoaded", (event) => {
  const form = document.getElementById("provider-domain-new-form")
  form.addEventListener("submit", (event) => {
    const domainInput = document.getElementById("id_domain");
    event.preventDefault();
    console.log(domainInput.value);

    return false;
  });
});
