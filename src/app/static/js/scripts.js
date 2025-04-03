document.addEventListener("DOMContentLoaded", function () {
    // 1. Инициализация переключателей пароля (сохранено без изменений)
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

    // 2. Инициализация темы (сохранено без изменений)
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

    // 3. Secure Fetch функция (сохранено без изменений)
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

    // 4. Обработчик формы входа (сохранено без изменений)
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

                const userData = await secureFetch("/api/v1/user/me");
                updateUIForAuthenticatedUser(userData);

                const modal = bootstrap.Modal.getInstance(document.getElementById('loginModal'));
                if (modal) modal.hide();
                loginForm.reset();

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

    // 5. Обработчик формы регистрации (сохранено без изменений)
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

                const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

                const response = await secureFetch(registerForm.action, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRF-Token": csrfToken
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

    // 6. Функции для работы с профилем (обновлено)
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
        if (profileData.gender) {
            document.getElementById('gender-field').textContent =
                profileData.gender === 'male' ? 'Мужской' : 'Женский';
        }
        if (profileData.age !== undefined && profileData.age !== null) {
            document.getElementById('age-field').textContent = profileData.age;
        } else {
            document.getElementById('age-field').textContent = 'Не указан';
        }
        if (profileData.height !== undefined && profileData.height !== null) {
            document.getElementById('height-field').textContent = `${profileData.height} см`;
        } else {
            document.getElementById('height-field').textContent = 'Не указан';
        }
        if (profileData.weight !== undefined && profileData.weight !== null) {
            document.getElementById('weight-field').textContent = `${profileData.weight} кг`;
        } else {
            document.getElementById('weight-field').textContent = 'Не указан';
        }
        if (profileData.created_at) {
            try {
                const date = new Date(profileData.created_at);
                document.getElementById('registration-date-field').textContent =
                    date.toLocaleDateString('ru-RU') + ' ' + date.toLocaleTimeString('ru-RU', {hour: '2-digit', minute:'2-digit'});
            } catch (e) {
                document.getElementById('registration-date-field').textContent = profileData.created_at;
            }
        }
    }

    // 7. Обновление UI после аутентификации (обновлено с обработчиками модалок)
    function updateUIForAuthenticatedUser(user) {
        const authSection = document.querySelector('.navbar-collapse .ms-auto');
        if (!authSection) return;

        authSection.innerHTML = `
            <p class="mb-0 me-3">Вы вошли как <strong>${escapeHtml(user.username)}</strong></p>
            <button id="profileBtn" class="btn btn-primary">Личный кабинет</button>
            <a href="/api/v1/user/logout" class="btn btn-outline-danger">Выйти</a>
            <button class="theme-toggle" id="themeToggle" title="Переключить тему">
                ${document.body.classList.contains('dark-mode') ? '☀️' : '🌙'}
            </button>
        `;

        // Инициализация обработчиков для новых кнопок
        document.getElementById('profileBtn')?.addEventListener('click', function() {
            if (window.location.pathname.includes('/api/v1/user/profile/data')) {
                loadProfileData();
            } else {
                window.location.href = '/api/v1/user/profile/data';
            }
        });

        initTheme();
    }

    // 8. Выход из системы (сохранено без изменений)
    document.querySelector('a[href*="/logout"]')?.addEventListener('click', async function(e) {
        e.preventDefault();
        try {
            await secureFetch("/api/v1/user/logout", { method: "POST" });
            window.location.href = "/";
        } catch (error) {
            console.error("Ошибка выхода:", error);
        }
    });

    // 9. Вспомогательные функции (сохранено + добавлено)
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

    // 10. Инициализация при загрузке (обновлено)
    const savedTheme = localStorage.getItem("theme") ||
        (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.body.classList.toggle("dark-mode", savedTheme === "dark");

    initTheme();
    initPasswordToggles();

    // Инициализация модальных окон для редактирования профиля
    function initProfileModals() {
        // Обработчик для кнопки "Редактировать профиль"
        document.querySelector('a[href="/api/v1/user/profile/update"]')?.addEventListener('click', function(e) {
            e.preventDefault();
            showEditProfileModal();
        });

        // Обработчик для кнопки "Сменить пароль"
        document.querySelector('a[href="/api/v1/user/password/change"]')?.addEventListener('click', function(e) {
            e.preventDefault();
            showChangePasswordModal();
        });
    }

    // Модальное окно редактирования профиля
    async function showEditProfileModal() {
        try {
            const profileData = await secureFetch('/api/v1/user/profile/data');

            const modalHtml = `
                <div class="modal fade" id="editProfileModal" tabindex="-1" aria-hidden="true">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Редактировать профиль</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <form id="editProfileForm">
                                    <div class="mb-3">
                                        <label class="form-label">Пол</label>
                                        <select class="form-select" name="gender" id="editGender">
                                            <option value="">Не указан</option>
                                            <option value="male" ${profileData.gender === 'male' ? 'selected' : ''}>Мужской</option>
                                            <option value="female" ${profileData.gender === 'female' ? 'selected' : ''}>Женский</option>
                                        </select>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Возраст</label>
                                        <input type="number" class="form-control" name="age" id="editAge"
                                               value="${profileData.age || ''}" min="1" max="120">
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Рост (см)</label>
                                        <input type="number" class="form-control" name="height" id="editHeight"
                                               value="${profileData.height || ''}" min="50" max="250">
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Вес (кг)</label>
                                        <input type="number" class="form-control" name="weight" id="editWeight"
                                               value="${profileData.weight || ''}" min="20" max="300">
                                    </div>
                                    <div id="editProfileError" class="alert alert-danger d-none"></div>
                                </form>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                                <button type="button" class="btn btn-primary" id="saveProfileBtn">Сохранить</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            let modalElement = document.getElementById('editProfileModal');
            if (!modalElement) {
                modalElement = document.createElement('div');
                document.body.appendChild(modalElement);
            }
            modalElement.innerHTML = modalHtml;

            const modal = new bootstrap.Modal(modalElement);
            modal.show();

            document.getElementById('saveProfileBtn').addEventListener('click', async function() {
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
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(formData)
                    });

                    updateProfileUI(response);
                    modal.hide();
                    showSuccess('Данные профиля успешно обновлены');

                } catch (error) {
                    console.error('Ошибка обновления профиля:', error);
                    const errorElement = document.getElementById('editProfileError');
                    errorElement.textContent = error.message;
                    errorElement.classList.remove('d-none');
                } finally {
                    btn.disabled = false;
                    btn.textContent = originalText;
                }
            });

        } catch (error) {
            console.error('Ошибка загрузки данных профиля:', error);
            showError('Не удалось загрузить данные для редактирования');
        }
    }

    // Модальное окно смены пароля
    function showChangePasswordModal() {
        const modalHtml = `
            <div class="modal fade" id="changePasswordModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Смена пароля</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <form id="changePasswordForm">
                                <div class="mb-3">
                                    <label class="form-label">Текущий пароль</label>
                                    <div class="input-group">
                                        <input type="password" class="form-control" name="current_password" id="currentPassword" required>
                                        <button class="btn btn-outline-secondary toggle-password" type="button" data-target="currentPassword">
                                            <i class="bi bi-eye"></i>
                                        </button>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Новый пароль</label>
                                    <div class="input-group">
                                        <input type="password" class="form-control" name="new_password" id="newPassword" required minlength="8">
                                        <button class="btn btn-outline-secondary toggle-password" type="button" data-target="newPassword">
                                            <i class="bi bi-eye"></i>
                                        </button>
                                    </div>
                                    <div class="form-text">Минимум 8 символов</div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Подтвердите новый пароль</label>
                                    <div class="input-group">
                                        <input type="password" class="form-control" name="confirm_password" id="confirmPassword" required minlength="8">
                                        <button class="btn btn-outline-secondary toggle-password" type="button" data-target="confirmPassword">
                                            <i class="bi bi-eye"></i>
                                        </button>
                                    </div>
                                </div>
                                <div id="changePasswordError" class="alert alert-danger d-none"></div>
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                            <button type="button" class="btn btn-primary" id="savePasswordBtn">Сохранить</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        let modalElement = document.getElementById('changePasswordModal');
        if (!modalElement) {
            modalElement = document.createElement('div');
            document.body.appendChild(modalElement);
        }
        modalElement.innerHTML = modalHtml;

        const modal = new bootstrap.Modal(modalElement);
        modal.show();
        initPasswordToggles();

        document.getElementById('savePasswordBtn').addEventListener('click', async function() {
            const btn = this;
            const originalText = btn.textContent;
            btn.disabled = true;
            btn.textContent = "Сохранение...";

            try {
                const form = document.getElementById('changePasswordForm');
                const newPassword = form.new_password.value;
                const confirmPassword = form.confirm_password.value;

                if (newPassword !== confirmPassword) {
                    throw new Error('Новый пароль и подтверждение не совпадают');
                }

                if (newPassword.length < 8) {
                    throw new Error('Пароль должен содержать минимум 8 символов');
                }

                await secureFetch('/api/v1/user/password/change', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        current_password: form.current_password.value,
                        new_password: newPassword
                    })
                });

                modal.hide();
                showSuccess('Пароль успешно изменен');
                form.reset();

            } catch (error) {
                console.error('Ошибка смены пароля:', error);
                const errorElement = document.getElementById('changePasswordError');
                errorElement.textContent = error.message;
                errorElement.classList.remove('d-none');
            } finally {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        });
    }

    // Инициализация модальных окон
    initProfileModals();

    // Загрузка данных профиля если на странице профиля
    if (window.location.pathname.includes('/api/v1/user/profile/data')) {
        loadProfileData();
    }
});