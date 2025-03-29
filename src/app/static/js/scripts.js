document.addEventListener("DOMContentLoaded", function () {
    // Функция для безопасного выполнения fetch-запросов с CSRF-токеном
    async function secureFetch(url, options = {}) {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;

        const headers = {
            ...(options.headers || {}),
            ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {})
        };

        try {
            const response = await fetch(url, {
                ...options,
                headers,
                credentials: 'include'
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || error.message || `HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Fetch error:', error);
            throw error;
        }
    }

    // Функция для обновления UI после аутентификации
    function updateUIForAuthenticatedUser(user) {
        const authSection = document.querySelector('.navbar-collapse .ms-auto');
        if (!authSection) return;

        authSection.innerHTML = `
            <p class="mb-0 me-3">Вы вошли как <strong>${escapeHtml(user.username)}</strong></p>
            <a href="/dashboard" class="btn btn-primary">Личный кабинет</a>
            <a href="/logout" class="btn btn-outline-danger">Выйти</a>
            <button class="theme-toggle" id="themeToggle" title="Переключить тему">
                ${document.body.classList.contains('dark-mode') ? '☀️' : '🌙'}
            </button>
        `;

        initThemeToggle();
    }

    // Экранирование HTML для безопасности
    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Инициализация переключателя темы
    function initThemeToggle() {
        const themeToggle = document.getElementById("themeToggle");
        if (themeToggle) {
            themeToggle.addEventListener("click", () => {
                const isDark = document.body.classList.toggle("dark-mode");
                localStorage.setItem("theme", isDark ? "dark" : "light");
                themeToggle.textContent = isDark ? "☀️" : "🌙";
            });
        }
    }

    // Функция для переключения видимости пароля
    function initPasswordToggles() {
        document.querySelectorAll('.toggle-password').forEach(button => {
            button.addEventListener('click', function () {

                const targetId = this.getAttribute('data-target');
                const input = document.getElementById(targetId);
                const icon = this.querySelector('i');

                if (input) {
                    if (input.type === 'password') {
                        input.type = 'text';
                    } else {
                        input.type = 'password';
                    }
                } else {
                    console.log("Ошибка: поле ввода не найдено!");
                }
            });
        });
    }

    // Обработчик формы входа
    const loginForm = document.getElementById("loginForm");
    if (loginForm) {
        const submitButton = loginForm.querySelector("button[type='submit']");
        const errorElement = document.getElementById("loginError");

        loginForm.addEventListener("submit", async function(event) {
            event.preventDefault();
            submitButton.disabled = true;
            const originalButtonText = submitButton.textContent;
            submitButton.textContent = "Вход...";

            try {
                // 1. Отправка данных входа с использованием secureFetch
                const formData = new FormData(loginForm);
                const { access_token } = await secureFetch("/api/v1/auth/login", {
                    method: "POST",
                    body: new URLSearchParams({
                        username: formData.get("username"),
                        password: formData.get("password")
                    }),
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded"
                    }
                });

                // 2. Получаем данные пользователя с токеном
                const userData = await secureFetch("/api/v1/user/me", {
                    headers: {
                        "Authorization": `Bearer ${access_token}`,
                        "Accept": "application/json"
                    }
                });

                // 3. Обновление интерфейса
                updateUIForAuthenticatedUser(userData);

                // 4. Закрытие модального окна
                const modal = bootstrap.Modal.getInstance(document.getElementById('loginModal'));
                if (modal) modal.hide();
                loginForm.reset();

            } catch (error) {
                console.error("Login error:", error);
                if (errorElement) {
                    errorElement.textContent = error.message;
                    errorElement.style.display = 'block';
                }
            } finally {
                submitButton.disabled = false;
                submitButton.textContent = originalButtonText;
            }
        });
    }

    // Обработчик формы регистрации
    const registerForm = document.getElementById("registerForm");
    if (registerForm) {
        registerForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            const submitButton = registerForm.querySelector("button[type='submit']");
            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.textContent = "Регистрация...";

            const formData = {
                email: document.getElementById("regEmail").value,
                username: document.getElementById("regUsername").value,
                password: document.getElementById("regPassword").value,
                confirm_password: document.getElementById("regConfirmPassword").value,
            };

            // Проверка совпадения паролей
            if (formData.password !== formData.confirm_password) {
                document.getElementById("registerError").textContent = "Пароли не совпадают!";
                submitButton.disabled = false;
                submitButton.textContent = originalText;
                return;
            }

            try {
                // Используем secureFetch для регистрации
                await secureFetch("/api/v1/auth/register", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(formData)
                });

                // Успешная регистрация
                alert("Регистрация успешна! Теперь вы можете войти.");

                // Закрываем модальное окно регистрации
                const registerModal = bootstrap.Modal.getInstance(document.getElementById('registerModal'));
                if (registerModal) registerModal.hide();

                // Открываем модальное окно входа
                const loginModal = new bootstrap.Modal(document.getElementById('loginModal'));
                loginModal.show();

            } catch (error) {
                document.getElementById("registerError").textContent = error.message;
            } finally {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }
        });
    }

    // Инициализация темы при загрузке
    const savedTheme = localStorage.getItem("theme") ||
        (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.body.classList.toggle("dark-mode", savedTheme === "dark");
    initThemeToggle();
    initPasswordToggles(); // Инициализация переключателей видимости пароля
});
