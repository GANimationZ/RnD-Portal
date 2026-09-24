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
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value
    const retype = document.getElementById("retype").value;
    const messageEl = document.getElementById("registermessage");
    const submitBtn = this.querySelector(".btn");

    submitBtn.disabled = true;
    submitBtn.value = "Processing...";

    try {
      const response = await fetch("/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password, retype }),
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

// ---- Login ---- //
const loginForm = document.getElementById("login");
const loginUsernameInput = document.getElementById("loginUsername");
const loginPasswordInput = document.getElementById("loginPassword");
const loginMessageEl = document.getElementById("loginmessage");
const loginFields = {
  username: loginUsernameInput,
  password: loginPasswordInput,
};

// Tampilkan pesan di bawah form. #loginmessage default-nya display:none di
// CSS, jadi HARUS di-set "block" di sini -- kalau tidak pesan tidak akan
// pernah terlihat.
function showLoginMessage(text, type = "error") {
  loginMessageEl.innerText = text;
  loginMessageEl.style.color = type === "success" ? "green" : "red";
  loginMessageEl.style.display = "block";
}

function clearLoginFeedback() {
  loginMessageEl.innerText = "";
  loginMessageEl.style.display = "none";
  Object.values(loginFields).forEach((input) => {
    input.classList.remove("is-invalid");
    input.removeAttribute("aria-invalid");
  });
}

// Tandai kolom yang bermasalah (border merah) dan fokuskan supaya user
// langsung bisa memperbaikinya.
function markLoginFieldInvalid(field) {
  const input = loginFields[field];
  if (!input) return;
  input.classList.add("is-invalid");
  input.setAttribute("aria-invalid", "true");
  input.focus();
  if (field === "password") input.select();
}

// Begitu user mulai mengetik ulang, hilangkan status error kolom itu.
Object.values(loginFields).forEach((input) => {
  input.addEventListener("input", clearLoginFeedback);
});

loginForm.addEventListener("submit", async function (e) {
  e.preventDefault();

  const username = loginUsernameInput.value.trim();
  const password = loginPasswordInput.value;
  const submitBtn = this.querySelector(".btn");

  clearLoginFeedback();

  // Validasi cepat di sisi client (atribut `required` tidak menangkap input
  // yang hanya berisi spasi). Backend tetap memvalidasi ulang.
  if (!username) {
    showLoginMessage("Username wajib diisi.");
    markLoginFieldInvalid("username");
    return;
  }
  if (!password) {
    showLoginMessage("Password wajib diisi.");
    markLoginFieldInvalid("password");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.value = "Processing...";

  try {
    const response = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    // Server error kadang membalas HTML (bukan JSON) -- jangan sampai
    // parse gagal dilaporkan sebagai "masalah koneksi".
    let result = {};
    try {
      result = await response.json();
    } catch (parseError) {
      result = {};
    }

    if (response.ok) {
      showLoginMessage(result.message || "Login berhasil.", "success");
      // Tombol sengaja dibiarkan disabled selama proses pindah halaman.
      // Tujuan ditentukan backend berdasarkan role (Admin/QA tidak boleh
      // masuk KPI Dashboard).
      window.location.href = result.redirect || "/";
      return;
    }

    const fallback =
      response.status >= 500
        ? "Terjadi kesalahan pada server. Silakan coba lagi beberapa saat lagi."
        : "Login gagal. Silakan coba lagi.";
    showLoginMessage(result.error || result.message || fallback);
    markLoginFieldInvalid(result.field);
  } catch (err) {
    console.error("Fetch error:", err);
    showLoginMessage(
      "Tidak dapat terhubung ke server. Periksa koneksi Anda lalu coba lagi.",
    );
  }

  submitBtn.disabled = false;
  submitBtn.value = "Login";
});
