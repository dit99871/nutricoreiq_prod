document.addEventListener("DOMContentLoaded", function() {
    // 1. Инициализация переключателей пароля
    function initPasswordToggles() {
        document.addEventListener('click', function(e) {
            const toggleBtn = e.target.closest('.toggle-password');
            if (toggleBtn) {
                const targetId = toggleBtn.getAttribute('data-target');
                const input = document.getElementById(targetId);
                if (input) {
                    const isVisible = input.type === 'password';
                    input.type = isVisible ? 'text' : 'password';

                    const icon = toggleBtn.querySelector('i');
                    if (icon) {
                        icon.classList.toggle('bi-eye', isVisible);
                        icon.classList.toggle('bi-eye-slash', !isVisible);
                    }

                    toggleBtn.setAttribute('aria-pressed', isVisible);
                    toggleBtn.setAttribute('aria-label',
                        isVisible ? 'Скрыть пароль' : 'Показать пароль');
                }
            }
        });
    }

    // 2. Инициализация темы
    function initTheme() {
        const savedTheme = localStorage.getItem("theme") ||
            (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
        document.body.classList.toggle("dark-mode", savedTheme === "dark");

        function updateThemeButtons(isDark) {
            document.querySelectorAll('.theme-toggle').forEach(btn => {
                btn.innerHTML = isDark ? '☀️' : '🌙';
                btn.setAttribute('title', isDark ? 'Светлая тема' : 'Темная тема');
            });
        }

        document.addEventListener('click', function(e) {
            if (e.target.closest('.theme-toggle')) {
                const isDark = document.body.classList.toggle("dark-mode");
                localStorage.setItem("theme", isDark ? "dark" : "light");
                updateThemeButtons(isDark);
            }
        });

        updateThemeButtons(savedTheme === "dark");
    }

    // 3. Secure Fetch функция
    async function secureFetch(url, options = {}) {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        const headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
            ...(options.headers || {})
        };

        try {
            const response = await fetch(url, {
                ...options,
                headers,
                credentials: 'include'
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({
                    message: `Ошибка HTTP: ${response.status}`
                }));
                throw new Error(error.detail || error.message || 'Ошибка сервера');
            }
            return await response.json();
        } catch (error) {
            console.error('Ошибка запроса:', error);
            throw error;
        }
    }

    // 4. Обработчик формы входа
    function initLoginForm() {
        const loginForm = document.getElementById("loginForm");
        if (!loginForm) return;

        loginForm.addEventListener("submit", async function(event) {
            event.preventDefault();
            const submitButton = loginForm.querySelector("button[type='submit']");
            const originalText = submitButton.textContent;

            submitButton.disabled = true;
            submitButton.textContent = "Вход...";
            submitButton.setAttribute('aria-busy', 'true');

            const errorElement = document.getElementById("loginError");
            if (errorElement) {
                errorElement.textContent = '';
                errorElement.classList.add('d-none');
            }

            try {
                const formData = new FormData(loginForm);
                const response = await secureFetch("/api/v1/auth/login", {
                    method: "POST",
                    body: new URLSearchParams({
                        username: formData.get("username"),
                        password: formData.get("password")
                    }),
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded"
                    }
                });

                const userData = await secureFetch("/api/v1/user/me");
                updateUIForAuthenticatedUser(userData);

                const modal = bootstrap.Modal.getInstance(document.getElementById('loginModal'));
                if (modal) modal.hide();
                loginForm.reset();

                if (window.location.pathname.includes('/api/v1/user/profile/data')) {
                    await loadProfileData();
                }

            } catch (error) {
                console.error("Ошибка входа:", error);
                if (errorElement) {
                    errorElement.textContent = error.message || "Неверное имя пользователя или пароль";
                    errorElement.classList.remove('d-none');
                }
            } finally {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
                submitButton.removeAttribute('aria-busy');
            }
        });
    }

    // 5. Обработчик формы регистрации
    function initRegisterForm() {
        const registerForm = document.getElementById("registerForm");
        if (!registerForm) return;

        registerForm.addEventListener("submit", async function(event) {
            event.preventDefault();
            const submitButton = registerForm.querySelector("button[type='submit']");
            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.textContent = "Регистрация...";

            const errorElement = document.getElementById("registerError");
            errorElement.textContent = "";
            errorElement.classList.add("d-none");

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

                await secureFetch(registerForm.action, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(data)
                });

                const modal = bootstrap.Modal.getInstance(document.getElementById('registerModal'));
                if (modal) modal.hide();

                alert("Регистрация прошла успешно! Теперь вы можете войти в систему.");
                registerForm.reset();

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
            const profileData = await secureFetch('/api/v1/user/profile/data');
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
        const fields = {
            'gender-field': profileData.gender ?
                (profileData.gender === 'male' ? 'Мужской' : 'Женский') : 'Не указан',
            'age-field': profileData.age ?? 'Не указан',
            'height-field': profileData.height ? `${profileData.height} см` : 'Не указан',
            'weight-field': profileData.weight ? `${profileData.weight} кг` : 'Не указан',
            'registration-date-field': formatRegistrationDate(profileData.created_at)
        };

        for (const [id, value] of Object.entries(fields)) {
            const element = document.getElementById(id);
            if (element) element.textContent = value;
        }
    }

    function formatRegistrationDate(dateString) {
        if (!dateString) return 'Не указана';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('ru-RU') + ' ' +
                   date.toLocaleTimeString('ru-RU', {hour: '2-digit', minute:'2-digit'});
        } catch (e) {
            return dateString;
        }
    }

    // 7. Обновление UI после аутентификации
    function updateUIForAuthenticatedUser(user) {
        const authSection = document.querySelector('.navbar-collapse .ms-auto');
        if (!authSection) return;

        authSection.innerHTML = `
            <div class="d-flex align-items-center">
                <p class="mb-0 me-3">Вы вошли как <strong>${escapeHtml(user.username)}</strong></p>
                <a href="/api/v1/user/profile/data" class="btn btn-primary me-2">Личный кабинет</a>
                <button id="logoutBtn" class="btn btn-outline-danger me-2">Выйти</button>
                <button class="btn btn-outline-secondary theme-toggle" id="themeToggle" title="Переключить тему">
                    ${document.body.classList.contains('dark-mode') ? '☀️' : '🌙'}
                </button>
            </div>
        `;

        document.getElementById('logoutBtn')?.addEventListener('click', async function(e) {
            e.preventDefault();
            this.disabled = true;
            this.textContent = "Выход...";

            try {
                await secureFetch("/api/v1/user/logout", { method: "POST" });
                window.location.href = "/";
            } catch (error) {
                console.error("Ошибка выхода:", error);
                this.disabled = false;
                this.textContent = "Выйти";
            }
        });

        // Инициализируем тему для новой кнопки
        initTheme();
    }

    // 8. Обработчики модальных окон профиля
    function initProfileModals() {
        // Обработчик сохранения профиля
        document.getElementById('saveProfileBtn')?.addEventListener('click', async function() {
            const btn = this;
            const originalText = btn.textContent;
            btn.disabled = true;
            btn.textContent = "Сохранение...";

            try {
                const formData = {
                    gender: document.getElementById('editGender').value || null,
                    age: document.getElementById('editAge').value ? parseInt(document.getElementById('editAge').value) : null,
                    height: document.getElementById('editHeight').value ? parseInt(document.getElementById('editHeight').value) : null,
                    weight: document.getElementById('editWeight').value ? parseInt(document.getElementById('editWeight').value) : null
                };

                const response = await secureFetch('/api/v1/user/profile/update', {
                    method: 'POST',
                    body: JSON.stringify(formData)
                });

                updateProfileUI(response);
                bootstrap.Modal.getInstance(document.getElementById('editProfileModal')).hide();
                showSuccess('Данные профиля успешно обновлены');

            } catch (error) {
                console.error('Ошибка обновления профиля:', error);
                const errorElement = document.getElementById('editProfileError');
                errorElement.textContent = error.message || 'Ошибка при обновлении профиля';
                errorElement.classList.remove('d-none');
            } finally {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        });

        // Обработчик смены пароля
        document.getElementById('savePasswordBtn')?.addEventListener('click', async function() {
            const btn = this;
            const originalText = btn.textContent;
            btn.disabled = true;
            btn.textContent = "Сохранение...";

            try {
                const newPassword = document.getElementById('newPassword').value;
                const confirmPassword = document.getElementById('confirmPassword').value;

                if (newPassword !== confirmPassword) {
                    throw new Error('Новый пароль и подтверждение не совпадают');
                }

                if (newPassword.length < 8) {
                    throw new Error('Пароль должен содержать минимум 8 символов');
                }

                await secureFetch('/api/v1/user/password/change', {
                    method: 'POST',
                    body: JSON.stringify({
                        current_password: document.getElementById('currentPassword').value,
                        new_password: newPassword
                    })
                });

                bootstrap.Modal.getInstance(document.getElementById('changePasswordModal')).hide();
                showSuccess('Пароль успешно изменён');
                document.getElementById('changePasswordForm').reset();

            } catch (error) {
                console.error('Ошибка смены пароля:', error);
                const errorElement = document.getElementById('changePasswordError');
                errorElement.textContent = error.message || 'Ошибка при смене пароля';
                errorElement.classList.remove('d-none');
            } finally {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        });
    }

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

    function showSuccess(message) {
        const successElement = document.getElementById('profile-success');
        if (successElement) {
            successElement.textContent = message;
            successElement.classList.remove('d-none');
            setTimeout(() => successElement.classList.add('d-none'), 5000);
        }
    }

    // 10. Основная инициализация
    function initAll() {
        // Проверка загрузки Bootstrap
        if (typeof bootstrap === 'undefined') {
            console.error('Bootstrap не загружен!');
            return;
        }

        initTheme();
        initPasswordToggles();
        initLoginForm();
        initRegisterForm();
        initProfileModals();

        // Если мы на странице профиля - загружаем данные
        if (window.location.pathname.includes('/api/v1/user/profile')) {
            loadProfileData();
        }
    }

    // Запускаем инициализацию
    initAll();
});