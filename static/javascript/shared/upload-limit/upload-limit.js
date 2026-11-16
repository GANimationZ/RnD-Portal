// ====================================================================
// Shared upload limits for <input type="file" data-max-files data-max-total-mb>
// Checked right when files are picked, so the user is told immediately
// instead of after a failed upload. The server enforces the same limits.
// ====================================================================
document.addEventListener("change", (e) => {
  const input = e.target;
  if (!(input instanceof HTMLInputElement) || input.type !== "file") return;

  const maxFiles = Number(input.dataset.maxFiles) || 0;
  const maxTotalMb = Number(input.dataset.maxTotalMb) || 0;
  const files = Array.from(input.files || []);

  let problem = "";
  if (maxFiles && files.length > maxFiles) {
    problem = `You can upload at most ${maxFiles} files at once (you selected ${files.length}).`;
  } else if (maxTotalMb) {
    const totalBytes = files.reduce((sum, file) => sum + file.size, 0);
    if (totalBytes > maxTotalMb * 1024 * 1024) {
      problem = `The selected files are larger than ${maxTotalMb} MB in total.`;
    }
  }

  if (problem) {
    input.value = ""; // clear the selection so nothing oversized is sent
    if (typeof showToast === "function") showToast(problem, "error");
  }
});
