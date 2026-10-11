"""The 'Sign in with Google' page served at /login."""

LOGIN_PAGE = r'''<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Inventory Service - Sign in</title>
  <script src="https://accounts.google.com/gsi/client" async defer></script>
  <style>
    body { font-family: sans-serif; max-width: 640px; margin: 40px auto; padding: 0 16px; }
    textarea { width: 100%; height: 110px; }
  </style>
</head>
<body>
  <h2>Inventory Service - Sign in</h2>
  <p>Click the button, choose your Google account, and you will get an access token.</p>

  <div id="g_id_onload" data-client_id="YOUR_GOOGLE_CLIENT_ID" data-callback="onGoogleSignIn"></div>
  <div class="g_id_signin" data-type="standard" data-text="signin_with"></div>

  <div id="result" style="display:none">
    <p id="message"></p>
    <textarea id="token" readonly></textarea>
    <p>Copy the token, then open <a href="/docs">/docs</a> &rarr; <b>Authorize</b> and paste it.</p>
  </div>

  <script>
    // Google gives us an ID token; our API checks it and returns our own access token.
    async function onGoogleSignIn(response) {
      const r = await fetch("/auth/google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: response.credential }),
      });
      const data = await r.json();
      document.getElementById("result").style.display = "block";
      if (r.ok) {
        document.getElementById("message").textContent = "Signed in. Your role: " + data.role;
        document.getElementById("token").value = data.access_token;
      } else {
        document.getElementById("message").textContent = "Error: " + data.detail;
        document.getElementById("token").value = "";
      }
    }
  </script>
</body>
</html>
'''
