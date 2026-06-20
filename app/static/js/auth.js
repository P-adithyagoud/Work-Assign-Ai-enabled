function bindAuthForm(formId, endpoint) {
    const form = document.getElementById(formId);
    const message = document.getElementById("authMessage");
    if (!form) return;

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        message.textContent = "";
        const button = form.querySelector("button[type='submit']");
        button.disabled = true;

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                body: new FormData(form),
            });
            const data = await response.json();
            if (!response.ok) {
                message.textContent = (data.errors || [data.error || "Request failed."]).join(" ");
                message.className = "form-message error";
                return;
            }
            window.location.href = data.redirect || "/dashboard";
        } catch (error) {
            message.textContent = "Network error. Please try again.";
            message.className = "form-message error";
        } finally {
            button.disabled = false;
        }
    });
}

bindAuthForm("loginForm", "/login");
bindAuthForm("signupForm", "/signup");
