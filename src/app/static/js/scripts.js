document.addEventListener("DOMContentLoaded", function() {
    // Проверка загрузки Bootstrap
    if (typeof bootstrap === 'undefined') {
        console.error('Bootstrap не загружен!');
        return;
    }

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

    // 3. Универсальная fetch-функция
    async function secureFetch(url, options = {}) {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        const headers = {
            'Accept': 'application/json',
            ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
            ...(options.headers || {})
        };

        try {
            const response = await fetch(url, {
                ...options,
                headers,
                credentials: 'include'
            });

            const contentType = response.headers.get('content-type');
            let data;

            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            } else {
                const text = await response.text();
                throw new Error(text || 'Неверный формат ответа');
            }

            if (!response.ok) {
                const errorDetail = data.detail || data.message || 'Неизвестная ошибка';
                throw new Error(JSON.stringify({
                    status: response.status,
                    message: errorDetail,
                    errors: data.detail
                }));
            }
            return data;
        } catch (error) {
            console.error('Ошибка запроса:', error);
            throw error;
        }
    }

    // 4. Функции для работы с UI
    function showError(message, elementId) {
        const errorElement = document.getElementById(elementId);
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.classList.remove('d-none');
        }
    }

    function showSuccess(message, elementId) {
        const successElement = document.getElementById(elementId);
        if (successElement) {
            successElement.textContent = message;
            successElement.classList.remove('d-none');
            setTimeout(() => successElement.classList.add('d-none'), 3000);
        }
    }

    function clearFormErrors(formId) {
        const form = document.getElementById(formId);
        if (form) {
            form.querySelectorAll('.invalid-feedback').forEach(el => {
                el.textContent = '';
                el.classList.add('d-none');
            });
            form.querySelectorAll('.is-invalid').forEach(el => {
                el.classList.remove('is-invalid');
            });
        }
    }

    // 5. Обработчики модальных окон профиля
    function initProfileModals() {
        // Редактирование профиля
        const editProfileModal = document.getElementById('editProfileModal');
        if (editProfileModal) {
            const editForm = document.getElementById('editProfileForm');
            const saveBtn = document.getElementById('saveProfileBtn');

            function populateEditForm() {
                const getValue = (id) => {
                    const el = document.getElementById(id);
                    return el?.dataset.rawValue || '';
                };

                document.getElementById('editGender').value = getValue('gender-field');
                document.getElementById('editAge').value = getValue('age-field');
                document.getElementById('editHeight').value = getValue('height-field');
                document.getElementById('editWeight').value = getValue('weight-field');
                document.getElementById('editKfa').value = getValue('kfa-field');
            }

            saveBtn?.addEventListener('click', async function() {
                const btn = this;
                btn.disabled = true;
                const originalText = btn.textContent;
                btn.textContent = "Сохранение...";

                clearFormErrors('editProfileForm');
                document.getElementById('profile-error').classList.add('d-none');
                document.getElementById('profile-success').classList.add('d-none');

                try {
                    const formData = new FormData(editForm);
                    const csrfToken = document.querySelector('input[name="_csrf_token"]').value;

                    // Преобразование FormData в JSON с типами данных
                    const jsonData = {};
                    formData.forEach((value, key) => {
                        if (['age', 'height', 'weight'].includes(key)) {
                            jsonData[key] = value ? Number(value) : null;
                        } else {
                            jsonData[key] = value || null;
                        }
                    });

                    const response = await fetch('/api/v1/user/profile/update', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRF-Token': csrfToken
                        },
                        body: JSON.stringify(jsonData),
                        credentials: 'include'
                    });

                    const data = await response.json();

                    if (!response.ok) {
                        let errorMessage = 'Ошибка обновления профиля';
                        const errors = {};

                        if (data.detail) {
                            if (Array.isArray(data.detail)) {
                                data.detail.forEach(err => {
                                    const field = err.loc[1];
                                    errors[field] = err.msg;
                                });
                            } else {
                                errorMessage = data.detail;
                            }
                        }
                        throw new Error(JSON.stringify(errors) || errorMessage);
                    }

//                    setTimeout(() => window.location.reload(), 1000);
                    bootstrap.Modal.getInstance(editProfileModal).hide();
                    editForm.reset()
                    showSuccess('Профиль успешно обновлен', 'profile-success');

                } catch (error) {
                    console.error('Ошибка обновления:', error);

                    try {
                        const errors = JSON.parse(error.message);
                        Object.entries(errors).forEach(([field, message]) => {
                            const input = document.getElementById(`edit${field.charAt(0).toUpperCase() + field.slice(1)}`);
                            const errorElement = document.getElementById(`edit${field.charAt(0).toUpperCase() + field.slice(1)}Error`);

                            if (input && errorElement) {
                                input.classList.add('is-invalid');
                                errorElement.textContent = message;
                                errorElement.classList.remove('d-none');
                            }
                        });
                    } catch (e) {
                        showError(error.message || 'Ошибка при обновлении профиля', 'editProfileError');
                    }
                } finally {
                    btn.disabled = false;
                    btn.textContent = originalText;
                }
            });

            editProfileModal.addEventListener('show.bs.modal', populateEditForm);
        }

        // Смена пароля
        const changePasswordModal = document.getElementById('changePasswordModal');
        if (changePasswordModal) {
            const changePasswordForm = document.getElementById('changePasswordForm');
            const savePasswordBtn = document.getElementById('savePasswordBtn');

            savePasswordBtn?.addEventListener('click', async function() {
                const btn = this;
                const originalText = btn.textContent;
                btn.disabled = true;
                btn.textContent = "Сохранение...";
                clearFormErrors('changePasswordForm');

                try {
                    const newPassword = document.getElementById('newPassword').value;
                    const confirmPassword = document.getElementById('confirmPassword').value;

                    if (newPassword !== confirmPassword) {
                        throw new Error('Новый пароль и подтверждение не совпадают');
                    }

                    await secureFetch('/api/v1/auth/password/change', {
                        method: "POST",
                        body: JSON.stringify({
                            current_password: document.getElementById('currentPassword').value,
                            new_password: newPassword
                        })
                    });

                    bootstrap.Modal.getInstance(changePasswordModal).hide();
                    changePasswordForm.reset();
                    showSuccess('Пароль успешно изменён');

                } catch (error) {
                    console.error('Ошибка смены пароля:', error);
                    showError(error.message || 'Ошибка при смене пароля', 'changePasswordError');
                } finally {
                    btn.disabled = false;
                    btn.textContent = originalText;
                }
            });
        }
    }

    // 6. Обработчик формы входа
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

            // Сброс ошибок
            showError('', 'loginError');

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
                if (modal) {
                    modal.hide();
                    modal._element.addEventListener('hidden.bs.modal', () => {
                        showSuccess(`Добро пожаловать, ${userData.username}!`, 'globalSuccess');
                    }, {once: true});
                }

                loginForm.reset();

            } catch (error) {
                console.error("Ошибка входа:", error);
                showError(error.message || "Неверное имя пользователя или пароль", 'loginError');
            } finally {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
                submitButton.removeAttribute('aria-busy');
            }
        });
    }

    // 7. Обработчик формы регистрации
    function initRegisterForm() {
        const registerForm = document.getElementById("registerForm");
        if (!registerForm) return;

        registerForm.addEventListener("submit", async function(event) {
            event.preventDefault();
            const submitButton = registerForm.querySelector("button[type='submit']");
            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.textContent = "Регистрация...";

            // Сброс предыдущих ошибок
            showError('', 'registerError');

            const password = registerForm.querySelector("#regPassword").value;
            const confirmPassword = registerForm.querySelector("#regConfirmPassword").value;

            if (password !== confirmPassword) {
                showError("Пароли не совпадают", 'registerError');
                submitButton.disabled = false;
                submitButton.textContent = originalText;
                return;
            }

            if (password.length < 8) {
                showError("Пароль должен содержать минимум 8 символов", 'registerError');
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
                if (modal) {
                    modal.hide();
                    modal._element.addEventListener('hidden.bs.modal', () => {
                        showSuccess("Регистрация прошла успешно! Теперь вы можете войти в систему.", 'globalSuccess');
                    }, {once: true});
                }

                registerForm.reset();

                const loginModal = new bootstrap.Modal(document.getElementById('loginModal'));
                setTimeout(() => loginModal.show(), 3500);

            } catch (error) {
                console.error("Ошибка регистрации:", error);
                let errorMessage = error.message || "Ошибка при регистрации";

                if (error.errors) {
                    errorMessage = Object.values(error.errors).join("\n");
                }

                showError(errorMessage, 'registerError');
            } finally {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }
        });
    }

    // 8. Обновление UI после аутентификации
    function updateUIForAuthenticatedUser(user) {
        const authSection = document.querySelector('.navbar-collapse .ms-auto');
        if (!authSection) return;

        authSection.innerHTML = `
            <div class="d-flex align-items-center">
                <a href="/api/v1/user/profile/data" class="btn btn-primary me-2">Профиль</a>
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
            window.location.href = "/api/v1/auth/logout";
        });

        initTheme();
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

    // 10. Основная инициализация
    function initAll() {
        initTheme();
        initPasswordToggles();
        initLoginForm();
        initRegisterForm();
        initProfileModals();
    }

    // Запускаем инициализацию
    initAll();
});