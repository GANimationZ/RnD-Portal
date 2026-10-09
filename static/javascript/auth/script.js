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

// ---- Register ---- //
document
  .getElementById("register")
  .addEventListener("submit", async function (e) {
    e.preventDefault();

    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const retype = document.getElementById("retype").value;
    const messageEl = document.getElementById("registermessage");
    const submitBtn = this.querySelector(".btn");

    submitBtn.disabled = true;
    submitBtn.value = "Processing...";

    try {
      const response = await fetch("/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, retype }),
      });

      const result = await response.json();
      messageEl.innerText = result.message || result.error;
      messageEl.style.display = "block";

      if (response.ok) {
        messageEl.style.color = "green";
        setTimeout(() => {
          authContainer.classList.remove("right-panel-active");
          document.getElementById("register").reset();
          messageEl.innerText = "";
          messageEl.style.display = "none";
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
      messageEl.innerText = "A connection error occurred.";
      messageEl.style.color = "red";
      messageEl.style.display = "block";
      submitBtn.disabled = false;
      submitBtn.value = "Register";
    }
  });

// ---- Login ---- //
const loginForm = document.getElementById("login");
const loginEmailInput = document.getElementById("loginEmail");
const loginPasswordInput = document.getElementById("loginPassword");
const loginMessageEl = document.getElementById("loginmessage");
const loginFields = {
  email: loginEmailInput,
  password: loginPasswordInput,
};

// Show a message under the form. #loginmessage defaults to display:none
// in CSS, so it MUST be set to "block" here or it never becomes visible.
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

// Mark the offending field (red border) and focus it so the user can fix
// it right away.
function markLoginFieldInvalid(field) {
  const input = loginFields[field];
  if (!input) return;
  input.classList.add("is-invalid");
  input.setAttribute("aria-invalid", "true");
  input.focus();
  if (field === "password") input.select();
}

// As soon as the user starts typing again, clear that field's error state.
Object.values(loginFields).forEach((input) => {
  input.addEventListener("input", clearLoginFeedback);
});

loginForm.addEventListener("submit", async function (e) {
  e.preventDefault();

  const email = loginEmailInput.value.trim();
  const password = loginPasswordInput.value;
  const submitBtn = this.querySelector(".btn");

  clearLoginFeedback();

  // Quick client-side validation (`required` doesn't catch whitespace-only
  // input). The backend re-validates anyway.
  if (!email) {
    showLoginMessage("Email is required.");
    markLoginFieldInvalid("email");
    return;
  }
  if (!password) {
    showLoginMessage("Password is required.");
    markLoginFieldInvalid("password");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.value = "Processing...";

  try {
    const response = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    // Server errors sometimes reply with HTML (not JSON) -- don't let a
    // parse failure get reported as a "connection problem".
    let result = {};
    try {
      result = await response.json();
    } catch (parseError) {
      result = {};
    }

    if (response.ok) {
      showLoginMessage(result.message || "Login successful.", "success");
      // Button is intentionally left disabled while navigating away.
      // The destination is decided by the backend based on role (Admin/QA
      // can't enter the KPI Dashboard).
      window.location.href = result.redirect || "/";
      return;
    }

    const fallback =
      response.status >= 500
        ? "A server error occurred. Please try again shortly."
        : "Login failed. Please try again.";
    showLoginMessage(result.error || result.message || fallback);
    markLoginFieldInvalid(result.field);
  } catch (err) {
    console.error("Fetch error:", err);
    showLoginMessage(
      "Unable to reach the server. Check your connection and try again.",
    );
  }

  submitBtn.disabled = false;
  submitBtn.value = "Login";
});
