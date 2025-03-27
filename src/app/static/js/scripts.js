document.addEventListener("DOMContentLoaded", function () {
    const loginForm = document.getElementById("loginForm");

    loginForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const formData = new FormData(loginForm);
        const response = await fetch("/login", {
            method: "POST",
            body: new URLSearchParams(formData),
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            }
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem("access_token", data.access_token);
            localStorage.setItem("refresh_token", data.refresh_token);
            window.location.reload();
        } else {
            alert("Ошибка входа: проверьте логин и пароль.");
        }
    });

    // Переключение темы
    const themeToggle = document.getElementById("themeToggle");

    if (themeToggle) {
        const savedTheme = localStorage.getItem("theme") ||
            (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");

        document.body.classList.toggle("dark-mode", savedTheme === "dark");
        themeToggle.textContent = savedTheme === "dark" ? "☀️" : "🌙";

        themeToggle.addEventListener("click", () => {
            const isDark = document.body.classList.toggle("dark-mode");
            localStorage.setItem("theme", isDark ? "dark" : "light");
            themeToggle.textContent = isDark ? "☀️" : "🌙";
        });
    }

    const registerForm = document.getElementById("registerForm");

    registerForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const formData = {
            email: document.getElementById("regEmail").value,
            username: document.getElementById("regUsername").value,
            password: document.getElementById("regPassword").value,
            confirm_password: document.getElementById("regConfirmPassword").value,
        };

        // Проверка совпадения паролей
        if (formData.password !== formData.confirm_password) {
            document.getElementById("registerError").textContent = "Пароли не совпадают!";
            return;
    }

    try {
        const response = await fetch("/register", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRF-Token": document.querySelector("meta[name='csrf-token']").content
            },
            body: JSON.stringify(formData),
        });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Ошибка регистрации");
            }

            // Успешная регистрация
            alert("Регистрация успешна! Теперь вы можете войти.");
            location.reload(); // Перезагрузка страницы для обновления состояния пользователя
        } catch (error) {
            document.getElementById("registerError").textContent = error.message;
        }
    });
});