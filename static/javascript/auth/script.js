// ---- Define ---- //
const authContainer = document.getElementById("authContainer");
const toRegister = document.getElementById("toRegister");
const toLogin = document.getElementById("toLogin");

// ---- Event Listener for Panel Switching ---- //
toRegister.addEventListener("click", (e) => {
  e.preventDefault();
  authContainer.classList.add("right-panel-active");
});

toLogin.addEventListener("click", (e) => {
  e.preventDefault();
  authContainer.classList.remove("right-panel-active");
});

// ---- Main Function ---- //
document
  .getElementById("register")
  .addEventListener("submit", async function (e) {
    e.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const retype = document.getElementById("retype").value;
    const messageEl = document.getElementById("registermessage");
    const submitBtn = this.querySelector(".btn");

    submitBtn.disabled = true;
    submitBtn.value = "Processing...";

    try {
      const response = await fetch("/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, retype }),
      });

      const result = await response.json();
      messageEl.innerText = result.message || result.error;
      messageEl.style.display = "block"; // tampilkan pesan

      if (response.ok) {
        messageEl.style.color = "green";
        setTimeout(() => {
          authContainer.classList.remove("right-panel-active");
          document.getElementById("register").reset();
          messageEl.innerText = "";
          messageEl.style.display = "none"; // sembunyikan lagi
          submitBtn.disabled = false;
          submitBtn.value = "Register";
        }, 1500);
      } else {
        messageEl.style.color = "red";
        submitBtn.disabled = false;
        submitBtn.value = "Register";
      }
    } catch (err) {
      console.error("Fetch error:", err);
      messageEl.innerText = "Terjadi kesalahan koneksi.";
      messageEl.style.color = "red";
      messageEl.style.display = "block";
      submitBtn.disabled = false;
      submitBtn.value = "Register";
    }
  });

document.getElementById("login").addEventListener("submit", async function (e) {
  e.preventDefault();

  const username = document.getElementById("loginUsername").value;
  const password = document.getElementById("loginPassword").value;
  const messageEl = document.getElementById("loginmessage");
  const submitBtn = this.querySelector(".btn");

  submitBtn.disabled = true;
  submitBtn.value = "Processing...";

  try {
    const response = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    const result = await response.json();

    if (response.ok) {
      messageEl.style.color = "green";
      messageEl.innerText = result.message;
      window.location.href = "/workspace/kpi-dashboard";
    } else {
      messageEl.style.color = "red";
      messageEl.innerText = result.error;
      submitBtn.disabled = false;
      submitBtn.value = "Login";
    }
  } catch (err) {
    console.error("Fetch error:", err);
    messageEl.innerText = "Terjadi kesalahan koneksi.";
    messageEl.style.color = "red";
    submitBtn.disabled = false;
    submitBtn.value = "Login";
  }
});
