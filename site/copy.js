// Adds a Copy button to install commands. The page works the same without it.
document.querySelectorAll("pre[data-copy]").forEach((pre) => {
  if (!navigator.clipboard) return;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "copy";
  button.textContent = "Copy";
  button.setAttribute("aria-label", "Copy the install commands");
  button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(pre.querySelector("code").textContent.trim() + "\n");
      button.textContent = "Copied";
    } catch {
      button.textContent = "Select and copy";
    }
    setTimeout(() => { button.textContent = "Copy"; }, 2000);
  });
  pre.closest(".install").querySelector(".install-head").append(button);
});
