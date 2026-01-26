const API = "http://127.0.0.1:9999"

window.onload = loadCaptcha

async function loadCaptcha() {
  const res = await fetch(API + "/init-login")
  const data = await res.json()
  document.getElementById("captchaImg").src =
    "data:image/png;base64," + data.captcha
}

async function submitLogin() {
  const username = document.getElementById("username").value
  const password = document.getElementById("password").value
  const captcha = document.getElementById("captcha").value

  document.getElementById("output").innerText = "Fetching result..."

  const res = await fetch(API + "/submit-login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, captcha })
  })

  const data = await res.json()
  document.getElementById("output").innerText =
    JSON.stringify(data, null, 2)
}
