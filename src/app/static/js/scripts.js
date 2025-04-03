document.addEventListener("DOMContentLoaded", function () {
    // 1. Инициализация переключателей пароля
    function initPasswordToggles() {
        document.querySelectorAll('.toggle-password').forEach(button => {
            button.addEventListener('click', function() {
                const targetId = this.getAttribute('data-target');
                const input = document.getElementById(targetId);
                if (input) {
                    input.type = input.type === 'password' ? 'text' : 'password';
                    const icon = this.querySelector('i');
                    if (icon) {
                        icon.classList.toggle('bi-eye');
                        icon.classList.toggle('bi-eye-slash');
                    }
                }
            });
        });
    }

    // 2. Инициализация темы
    function initTheme() {
        const themeToggle = document.getElementById("themeToggle");
        if (themeToggle) {
            themeToggle.addEventListener("click", () => {
                const isDark = document.body.classList.toggle("dark-mode");
                localStorage.setItem("theme", isDark ? "dark" : "light");
                themeToggle.textContent = isDark ? "☀️" : "🌙";
            });
        }
    }

    // 3. Secure Fetch функция
    async function secureFetch(url, options = {}) {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        const headers = {
            ...(options.headers || {}),
            ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
        };

        try {
            const response = await fetch(url, {
                ...options,
                headers,
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ message: 'Ошибка сервера' }));
                throw new Error(error.detail || error.message || `Ошибка HTTP: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Ошибка запроса:', error);
            throw error;
        }
    }

    // 4. Обработчик формы входа
    const loginForm = document.getElementById("loginForm");
    if (loginForm) {
        loginForm.addEventListener("submit", async function(event) {
            event.preventDefault();
            const submitButton = loginForm.querySelector("button[type='submit']");
            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.textContent = "Вход...";

            try {
                const formData = new FormData(loginForm);
                const loginResponse = await secureFetch("/api/v1/auth/login", {
                    method: "POST",
                    body: new URLSearchParams({
                        username: formData.get("username"),
                        password: formData.get("password")
                    }),
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded"
                    }
                });

                // Получаем данные пользователя после успешного входа
                const userData = await secureFetch("/api/v1/user/me", {
                    headers: {
                        "Accept": "application/json",
                        "Content-Type": "application/json"
                    }
                });

                // Обновляем UI
                updateUIForAuthenticatedUser(userData);

                // Закрываем модальное окно
                const modal = bootstrap.Modal.getInstance(document.getElementById('loginModal'));
                if (modal) modal.hide();
                loginForm.reset();

                // Если на странице профиля - обновляем данные
                if (window.location.pathname.includes('/profile')) {
                    await loadProfileData();
                }

            } catch (error) {
                console.error("Ошибка входа:", error);
                const errorElement = document.getElementById("loginError");
                if (errorElement) {
                    errorElement.textContent = error.message;
                    errorElement.classList.remove('d-none');
                }
            } finally {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }
        });
    }

    // 5. Обработчик формы регистрации
    const registerForm = document.getElementById("registerForm");
    if (registerForm) {
        registerForm.addEventListener("submit", async function(event) {
            event.preventDefault();
            const submitButton = registerForm.querySelector("button[type='submit']");
            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.textContent = "Регистрация...";

            const errorElement = document.getElementById("registerError");
            errorElement.textContent = "";
            errorElement.classList.add("d-none");

            // Проверка пароля
            const password = registerForm.querySelector("#regPassword").value;
            const confirmPassword = registerForm.querySelector("#regConfirmPassword").value;

            if (password !== confirmPassword) {
                errorElement.textContent = "Пароли не совпадают";
                errorElement.classList.remove("d-none");
                submitButton.disabled = false;
                submitButton.textContent = originalText;
                return;
            }

            if (password.length < 8) {
                errorElement.textContent = "Пароль должен содержать минимум 8 символов";
                errorElement.classList.remove("d-none");
                submitButton.disabled = false;
                submitButton.textContent = originalText;
                return;
            }

            try {
                const formData = new FormData(registerForm);
                const data = {
                    username: formData.get("username"),
                    email: formData.get("email"),
                    password: formData.get("password")
                };

                // Получаем CSRF токен из мета-тега
                const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

                const response = await secureFetch(registerForm.action, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRF-Token": csrfToken
                    },
                    body: JSON.stringify(data)
                });

                // Успешная регистрация - закрываем модальное окно
                const modal = bootstrap.Modal.getInstance(document.getElementById('registerModal'));
                if (modal) modal.hide();

                // Показываем сообщение об успехе
                alert("Регистрация прошла успешно! Теперь вы можете войти в систему.");

                // Очищаем форму
                registerForm.reset();

                // Автоматически открываем форму входа
                const loginModal = new bootstrap.Modal(document.getElementById('loginModal'));
                loginModal.show();

            } catch (error) {
                console.error("Ошибка регистрации:", error);
                errorElement.textContent = error.message || "Ошибка при регистрации";
                errorElement.classList.remove("d-none");

                if (error.errors) {
                    const errorMessages = Object.values(error.errors).join("\n");
                    errorElement.textContent = errorMessages;
                }
            } finally {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }
        });
    }

    // 6. Функции для работы с профилем
    async function loadProfileData() {
        try {
            const profileData = await secureFetch('/api/v1/user/profile');
            updateProfileUI(profileData);
        } catch (error) {
            console.error('Ошибка загрузки профиля:', error);
            showError('Не удалось загрузить данные профиля');
            if (error.message.includes('401')) {
                window.location.href = '/api/v1/auth/login';
            }
        }
    }

    function updateProfileUI(profileData) {
        if (profileData.gender) {
            document.getElementById('gender-field').textContent =
                profileData.gender === 'male' ? 'Мужской' : 'Женский';
        }
        if (profileData.age) {
            document.getElementById('age-field').textContent = profileData.age;
        }
        if (profileData.height) {
            document.getElementById('height-field').textContent = `${profileData.height} см`;
        }
        if (profileData.weight) {
            document.getElementById('weight-field').textContent = `${profileData.weight} кг`;
        }
    }

    // 7. Обновление UI после аутентификации
    function updateUIForAuthenticatedUser(user) {
        const authSection = document.querySelector('.navbar-collapse .ms-auto');
        if (!authSection) return;

        authSection.innerHTML = `
            <p class="mb-0 me-3">Вы вошли как <strong>${escapeHtml(user.username)}</strong></p>
            <a href="/api/v1/user/profile" class="btn btn-primary">Личный кабинет</a>
            <a href="/api/v1/user/logout" class="btn btn-outline-danger">Выйти</a>
            <button class="theme-toggle" id="themeToggle" title="Переключить тему">
                ${document.body.classList.contains('dark-mode') ? '☀️' : '🌙'}
            </button>
        `;

        initTheme();
    }

    // 8. Выход из системы
    document.querySelector('a[href*="/logout"]')?.addEventListener('click', async function(e) {
        e.preventDefault();
        try {
            await secureFetch("/api/v1/user/logout", { method: "POST" });
            window.location.href = "/";
        } catch (error) {
            console.error("Ошибка выхода:", error);
        }
    });

    // 9. Вспомогательные функции
    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function showError(message) {
        const errorElement = document.getElementById('profile-error');
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.classList.remove('d-none');
        }
    }

    // 10. Инициализация при загрузке
    const savedTheme = localStorage.getItem("theme") ||
        (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.body.classList.toggle("dark-mode", savedTheme === "dark");

    initTheme();
    initPasswordToggles();

    if (window.location.pathname.includes('/profile')) {
        loadProfileData();
    }
});
