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
            document.querySelectorAll('#themeToggle').forEach(btn => {
                btn.innerHTML = isDark ? '☀️' : '🌙';
            });
        }

        document.addEventListener('click', function(e) {
            if (e.target.closest('#themeToggle')) {
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

                const response = await secureFetch(registerForm.action, {
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
                window.location.href = '/login';
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
                <button id="profileBtn" class="btn btn-primary me-2">Личный кабинет</button>
                <button id="logoutBtn" class="btn btn-outline-danger me-2">Выйти</button>
                <button class="btn btn-outline-secondary" id="themeToggle" title="Переключить тему">
                    ${document.body.classList.contains('dark-mode') ? '☀️' : '🌙'}
                </button>
            </div>
        `;

        document.getElementById('profileBtn')?.addEventListener('click', function() {
            window.location.href = '/api/v1/user/profile/data';
        });

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
    }

    // 8. Вспомогательные функции
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

    // 9. Модальное окно редактирования профиля (исправленная версия)
    async function showEditProfileModal() {
        try {
            // 1. Получаем данные профиля
            const profileData = await secureFetch('/api/v1/user/profile/data');

            // 2. Создаем HTML для модального окна
            const modalId = 'editProfileModal';
            const modalHtml = `
                <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
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
                                        <select class="form-select" id="editGender">
                                            <option value="">Не указан</option>
                                            <option value="male" ${profileData.gender === 'male' ? 'selected' : ''}>Мужской</option>
                                            <option value="female" ${profileData.gender === 'female' ? 'selected' : ''}>Женский</option>
                                        </select>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Возраст</label>
                                        <input type="number" class="form-control" id="editAge"
                                               value="${profileData.age || ''}" min="1" max="120">
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Рост (см)</label>
                                        <input type="number" class="form-control" id="editHeight"
                                               value="${profileData.height || ''}" min="50" max="250">
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Вес (кг)</label>
                                        <input type="number" class="form-control" id="editWeight"
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

            // 3. Удаляем старое модальное окно, если оно есть
            const oldModal = document.getElementById(modalId);
            if (oldModal) oldModal.remove();

            // 4. Добавляем новое модальное окно в DOM
            const modalContainer = document.createElement('div');
            modalContainer.innerHTML = modalHtml;
            document.body.appendChild(modalContainer);

            // 5. Инициализируем модальное окно
            const modalElement = document.getElementById(modalId);
            const modal = new bootstrap.Modal(modalElement);

            // 6. Показываем модальное окно
            modal.show();

            // 7. Обработчик для кнопки сохранения
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

            // 8. Удаляем модальное окно при закрытии
            modalElement.addEventListener('hidden.bs.modal', () => {
                modal.dispose();
                modalElement.remove();
            });

        } catch (error) {
            console.error('Ошибка загрузки данных профиля:', error);
            showError('Не удалось загрузить данные для редактирования');
        }
    }

    // 10. Модальное окно смены пароля
    function showChangePasswordModal() {
        const modalId = 'changePasswordModal';
        const modalHtml = `
            <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
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
                                        <input type="password" class="form-control" id="currentPassword" required>
                                        <button class="btn btn-outline-secondary toggle-password" type="button" data-target="currentPassword">
                                            <i class="bi bi-eye"></i>
                                        </button>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Новый пароль</label>
                                    <div class="input-group">
                                        <input type="password" class="form-control" id="newPassword" required minlength="8">
                                        <button class="btn btn-outline-secondary toggle-password" type="button" data-target="newPassword">
                                            <i class="bi bi-eye"></i>
                                        </button>
                                    </div>
                                    <div class="form-text">Минимум 8 символов</div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Подтвердите новый пароль</label>
                                    <div class="input-group">
                                        <input type="password" class="form-control" id="confirmPassword" required minlength="8">
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

        // Удаляем старое модальное окно, если есть
        const oldModal = document.getElementById(modalId);
        if (oldModal) oldModal.remove();

        // Добавляем новое модальное окно
        const modalContainer = document.createElement('div');
        modalContainer.innerHTML = modalHtml;
        document.body.appendChild(modalContainer);

        // Инициализируем и показываем модальное окно
        const modalElement = document.getElementById(modalId);
        const modal = new bootstrap.Modal(modalElement);
        modal.show();

        // Инициализируем переключатели пароля
        initPasswordToggles();

        // Обработчик сохранения
        document.getElementById('savePasswordBtn').addEventListener('click', async function() {
            const btn = this;
            const originalText = btn.textContent;
            btn.disabled = true;
            btn.textContent = "Сохранение...";

            try {
                const form = document.getElementById('changePasswordForm');
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
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        current_password: document.getElementById('currentPassword').value,
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

        // Удаляем модальное окно после закрытия
        modalElement.addEventListener('hidden.bs.modal', () => {
            modal.dispose();
            modalElement.remove();
        });
    }

    // 11. Инициализация модальных окон профиля (исправленная версия)
    function initProfileModals() {
        // Для кнопки редактирования профиля
        const editProfileLink = document.querySelector('#edit-profile-btn');
        if (editProfileLink) {
            editProfileLink.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                showEditProfileModal();
            });
        }

        // Для кнопки смены пароля
        const changePasswordLink = document.querySelector('a[href="/api/v1/user/password/change"]');
        if (changePasswordLink) {
            changePasswordLink.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                showChangePasswordModal();
            });
        }
    }

    // 12. Основная инициализация
    function initAll() {
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