document.addEventListener("DOMContentLoaded", function() {
    // Проверка загрузки Bootstrap
    if (typeof bootstrap === 'undefined') {
        console.error('Bootstrap не загружен!');
        return;
    }

    // 1. Инициализация темы
    const initTheme = () => {
        const savedTheme = localStorage.getItem('theme') ||
            (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        document.body.classList.toggle('dark-mode', savedTheme === 'dark');

        const updateThemeButtons = (isDark) => {
            document.querySelectorAll('.theme-toggle').forEach(btn => {
                btn.innerHTML = isDark ? '☀️' : '🌙';
                btn.setAttribute('title', isDark ? 'Светлая тема' : 'Темная тема');
                btn.setAttribute('aria-label', isDark ? 'Переключить на светлую тему' : 'Переключить на темную тему');
            });
        };

        updateThemeButtons(savedTheme === 'dark');
    };

    // 2. Переключатели пароля
    const initPasswordToggles = () => {
        document.addEventListener('click', e => {
            const toggleBtn = e.target.closest('.toggle-password');
            if (toggleBtn) {
                const input = document.getElementById(toggleBtn.dataset.target);
                if (input) {
                    const isVisible = input.type === 'password';
                    input.type = isVisible ? 'text' : 'password';

                    const icon = toggleBtn.querySelector('i');
                    if (icon) {
                        icon.className = isVisible ? 'bi bi-eye' : 'bi bi-eye-slash';
                    }

                    toggleBtn.setAttribute('aria-pressed', isVisible);
                    toggleBtn.setAttribute('aria-label',
                        isVisible ? 'Скрыть пароль' : 'Показать пароль');
                }
            }
        });
    };

    // 3. Универсальный fetch
    const secureFetch = async (url, options = {}) => {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        const headers = {
            'Accept': 'application/json',
            ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
            ...options.headers || {}
        };

        // Добавляем тайм-аут 10 секунд
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);

        try {
            const response = await fetch(url, {
                ...options,
                headers,
                credentials: 'include',
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                const text = await response.text();
                console.error('Неверный формат ответа:', text);
                throw new Error('Сервер вернул не JSON');
            }

            const data = await response.json();

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
            if (error.name === 'AbortError') {
                console.error('Запрос превысил время ожидания (10 секунд)');
                throw new Error('Превышено время ожидания запроса');
            }
            console.error('Ошибка запроса:', error);
            throw error;
        }
    };

    // 4. Функции для работы с UI
    const showError = (containerId, message) => {
        const container = document.getElementById(containerId);
        if (container) {
            container.textContent = message;
            container.classList.remove('d-none');
        }
    };

    const showSuccess = (message, elementId = 'globalSuccess') => {
        console.log(`Попытка показать сообщение в элементе #${elementId}: "${message}"`);
        const successElement = document.getElementById(elementId);
        if (!successElement) {
            console.error(`Элемент #${elementId} не найден в DOM`);
            return;
        }

        const textElement = successElement.querySelector('#globalSuccessText') || successElement.querySelector('span');
        if (!textElement) {
            console.error(`Элемент для текста (span или #globalSuccessText) не найден внутри #${elementId}`);
            return;
        }

        textElement.textContent = message;
        successElement.classList.remove('d-none');
        successElement.classList.add('show');
        console.log(`Сообщение отображено в #${elementId}`);

        setTimeout(() => {
            successElement.classList.remove('show');
            successElement.classList.add('d-none');
            console.log(`Сообщение в #${elementId} скрыто`);
        }, 3000);
    };

    const clearFormErrors = (formId) => {
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
    };

    // Функция для обновления UI профиля
    const updateProfileUI = (userData) => {
        // Обновляем email в заголовке профиля
        const emailElement = document.querySelector('.profile-header p');
        if (emailElement && userData.email) {
            emailElement.textContent = userData.email;
        }

        // Обновляем поля в detail-card
        const detailItems = document.querySelectorAll('.detail-item');
        detailItems.forEach(item => {
            const label = item.querySelector('strong')?.textContent.trim();
            const valueSpan = item.querySelector('span');

            if (!valueSpan) return;

            if (label === 'Рост:') {
                valueSpan.textContent = userData.height ? `${userData.height} см` : 'Не указано';
            } else if (label === 'Вес:') {
                valueSpan.textContent = userData.weight ? `${userData.weight} кг` : 'Не указано';
            } else if (label === 'Возраст:') {
                valueSpan.textContent = userData.age ? userData.age : 'Не указано';
            } else if (label === 'Уровень физической активности:') {
                valueSpan.textContent = userData.activity_level || 'Не указано';
            }
        });
    };

    // 5. Обработчики форм
    const initLoginForm = () => {
        const form = document.getElementById('loginForm');
        if (!form) return;

        form.addEventListener('submit', async e => {
            e.preventDefault();
            const btn = form.querySelector('button[type="submit"]');
            const originalText = btn.textContent;

            btn.disabled = true;
            btn.textContent = "Вход...";
            btn.setAttribute('aria-busy', 'true');

            clearFormErrors('loginForm');
            showError('', 'loginError');

            try {
                console.log('Отправка запроса на вход...');
                const formData = new FormData(form);
                await secureFetch('/api/v1/auth/login', {
                    method: 'POST',
                    body: new URLSearchParams(formData),
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
                        showSuccess(`Добро пожаловать, ${userData.username || 'Пользователь'}!`, 'globalSuccess');
                        setTimeout(() => {
                            window.location.reload();
                        }, 2000);
                    }, {once: true});
                } else {
                    showSuccess(`Добро пожаловать, ${userData.username || 'Пользователь'}!`, 'globalSuccess');
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                }
            } catch (error) {
                console.error("Ошибка входа:", error);
                showError('loginError', error.message || "Неверное имя пользователя или пароль");
            } finally {
                btn.disabled = false;
                btn.textContent = originalText;
                btn.removeAttribute('aria-busy');
            }
        });
    };

    const initRegisterForm = () => {
        const form = document.getElementById('registerForm');
        if (!form) return;

        form.addEventListener('submit', async e => {
            e.preventDefault();
            const btn = form.querySelector('button[type="submit"]');
            const originalText = btn.textContent;

            btn.disabled = true;
            btn.textContent = "Регистрация...";

            clearFormErrors('registerForm');
            showError('', 'registerError');

            const password = form.password.value;
            const confirmPassword = form.confirm_password.value;

            if (password !== confirmPassword) {
                showError('registerError', 'Пароли не совпадают');
                btn.disabled = false;
                btn.textContent = originalText;
                return;
            }

            if (password.length < 8) {
                showError('registerError', 'Пароль должен содержать минимум 8 символов');
                btn.disabled = false;
                btn.textContent = originalText;
                return;
            }

            try {
                await secureFetch(form.action, {
                    method: 'POST',
                    body: JSON.stringify({
                        username: form.username.value,
                        email: form.email.value,
                        password: password
                    })
                });

                const modal = bootstrap.Modal.getInstance(document.getElementById('registerModal'));
                if (modal) {
                    modal.hide();
                    modal._element.addEventListener('hidden.bs.modal', () => {
                        showSuccess("Регистрация прошла успешно! Теперь вы можете войти в систему.", 'globalSuccess');
                    }, {once: true});
                } else {
                    showSuccess("Регистрация прошла успешно! Теперь вы можете войти в систему.", 'globalSuccess');
                }

                const loginModal = new bootstrap.Modal(document.getElementById('loginModal'));
                setTimeout(() => loginModal.show(), 3500);
            } catch (error) {
                console.error("Ошибка регистрации:", error);
                let errorMessage = error.message || "Ошибка при регистрации";

                if (error.errors) {
                    errorMessage = Object.values(error.errors).join("\n");
                }

                showError('registerError', errorMessage);
            } finally {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        });
    };

    // 6. Обработчики модальных окон профиля
    const initProfileModals = () => {
        // Редактирование профиля
        const editProfileModal = document.getElementById('editProfileModal');
        if (editProfileModal) {
            const editForm = document.getElementById('editProfileForm');
            const saveBtn = document.getElementById('saveProfileBtn');

            saveBtn?.addEventListener('click', async function() {
                const btn = this;
                btn.disabled = true;
                const originalText = btn.textContent;
                btn.textContent = "Сохранение...";

                clearFormErrors('editProfileForm');
                document.getElementById('profile-error')?.classList.add('d-none');
                document.getElementById('globalSuccess')?.classList.add('d-none');

                try {
                    const formData = new FormData(editForm);
                    const jsonData = {};
                    formData.forEach((value, key) => {
                        if (['age', 'height', 'weight'].includes(key)) {
                            jsonData[key] = value ? Number(value) : null;
                        } else {
                            jsonData[key] = value || null;
                        }
                    });

                    await secureFetch('/api/v1/user/profile/update', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(jsonData)
                    });

                    const updatedUserData = await secureFetch('/api/v1/user/me');

                    const modal = bootstrap.Modal.getInstance(editProfileModal);
                    if (modal) {
                        modal.hide();
                        modal._element.addEventListener('hidden.bs.modal', () => {
                            showSuccess('Профиль успешно обновлен! Обновите страницу!', 'globalSuccess');
                            editForm.reset();
                        }, { once: true });
                    } else {
                        showSuccess('Профиль успешно обновлен! Обновите страницу!', 'globalSuccess');
                        editForm.reset();
                        updateProfileUI(updatedUserData);
                    }

                } catch (error) {
                    console.error('Ошибка обновления:', error);
                    let errorMessage = 'Ошибка при обновлении профиля';
                    try {
                        const parsedError = JSON.parse(error.message);
                        if (parsedError.errors) {
                            Object.entries(parsedError.errors).forEach(([field, message]) => {
                                const input = document.getElementById(`edit${field.charAt(0).toUpperCase() + field.slice(1)}`);
                                const errorElement = document.getElementById(`edit${field.charAt(0).toUpperCase() + field.slice(1)}Error`);
                                if (input && errorElement) {
                                    input.classList.add('is-invalid');
                                    errorElement.textContent = message;
                                    errorElement.classList.remove('d-none');
                                }
                            });
                        } else {
                            errorMessage = parsedError.message || errorMessage;
                            showError('editProfileError', errorMessage);
                        }
                    } catch (e) {
                        showError('editProfileError', error.message || errorMessage);
                    }
                } finally {
                    btn.disabled = false;
                    btn.textContent = originalText;
                }
            });
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

                    const modal = bootstrap.Modal.getInstance(changePasswordModal);
                    if (modal) {
                        modal.hide();
                        modal._element.addEventListener('hidden.bs.modal', () => {
                            showSuccess('Пароль успешно изменён', 'globalSuccess');
                            changePasswordForm.reset();
                        }, { once: true });
                    } else {
                        showSuccess('Пароль успешно изменён', 'globalSuccess');
                        changePasswordForm.reset();
                    }

                } catch (error) {
                    console.error('Ошибка смены пароля:', error);
                    showError(error.message || 'Ошибка при смене пароля', 'changePasswordError');
                } finally {
                    btn.disabled = false;
                    btn.textContent = originalText;
                }
            });
        }
    };

    // 7. Поиск продуктов
    const initProductSearch = () => {
        const searchInput = document.getElementById('productQuery');
        const searchResults = document.getElementById('searchResults');
        const searchForm = document.getElementById('searchProductForm');
        const analyzeBtn = searchForm?.querySelector('button[type="submit"]');

        if (!searchInput || !searchResults || !searchForm) {
            console.error('Не найдены элементы для поиска:', { searchInput, searchResults, searchForm });
            return;
        }
        if (!analyzeBtn) {
            console.error('Кнопка "Проанализировать" не найдена');
        }

        let currentFocus = -1;
        let abortController = null;
        let lastSearchData = null; // Сохраняем данные последнего поиска

        const performSearch = async (query, fromForm = false) => {
            console.log(`Выполняется поиск: query="${query}", fromForm=${fromForm}`);
            abortController?.abort();
            abortController = new AbortController();

            try {
                const data = await secureFetch(`/api/v1/product/search?query=${encodeURIComponent(query)}`, {
                    signal: abortController.signal
                });

                lastSearchData = data; // Сохраняем данные для дальнейшего использования

                if (!fromForm) {
                    renderResults(data.suggestions || []);
                    if (data.exact_match) {
                        renderResults([data.exact_match, ...data.suggestions]);
                    }
                }

                return data;
            } catch (error) {
                if (error.name !== 'AbortError') {
                    console.error('Ошибка поиска:', error);
                    showError('searchError', 'Ошибка поиска: ' + error.message);
                }
                throw error;
            }
        };

        const renderResults = (items) => {
            console.log('Рендеринг результатов:', items);
            if (items.length === 0) {
                searchResults.innerHTML = '<div class="suggestion-item">Ничего не найдено</div>';
                searchResults.classList.add('active');
                return;
            }

            searchResults.innerHTML = items.map(item => `
                <div class="suggestion-item" data-id="${item.id}">
                    <div class="suggestion-content">
                        <i class="bi bi-box suggestion-icon"></i>
                        <div>
                            <div class="suggestion-title">${escapeHtml(item.title)}</div>
                        </div>
                    </div>
                </div>
            `).join('');

            searchResults.classList.add('active');

            searchResults.querySelectorAll('.suggestion-item').forEach(item => {
                item.addEventListener('click', () => {
                    window.location.href = `/api/v1/product/${item.dataset.id}`;
                });
            });
        };

        // Обработка ввода с debounce
        searchInput.addEventListener('input', _.debounce((e) => {
            const query = e.target.value.trim();
            if (query.length === 0) {
                searchResults.innerHTML = '';
                searchResults.classList.remove('active');
                lastSearchData = null;
                return;
            }

            if (query.length > 1) {
                performSearch(query);
            } else {
                searchResults.innerHTML = '';
                searchResults.classList.remove('active');
                lastSearchData = null;
            }
        }, 300));

        // Обработка формы и кнопки "Проанализировать"
        searchForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const query = searchInput.value.trim();
            if (!analyzeBtn) {
                console.error('Кнопка "Проанализировать" не найдена');
                return;
            }

            if (query.length < 2) {
                showError('searchError', 'Запрос должен содержать минимум 2 символа');
                return;
            }

            analyzeBtn.disabled = true;
            const originalText = analyzeBtn.textContent;
            analyzeBtn.textContent = 'Идет анализ...';

            try {
                const data = await performSearch(query, true);
                if (data.exact_match) {
                    window.location.href = `/api/v1/product/${data.exact_match.id}`;
                } else if (lastSearchData && lastSearchData.exact_match) {
                    window.location.href = `/api/v1/product/${lastSearchData.exact_match.id}`;
                } else {
                    showError('searchError', 'Точное совпадение не найдено');
                }
            } catch (error) {
                showError('searchError', 'Ошибка анализа: ' + error.message);
            } finally {
                analyzeBtn.disabled = false;
                analyzeBtn.textContent = originalText;
            }
        });

        // Обработка клавиш для навигации по подсказкам и подтверждения
        searchInput.addEventListener('keydown', (e) => {
            const items = searchResults.querySelectorAll('.suggestion-item');
            if (['ArrowDown', 'ArrowUp', 'Enter'].includes(e.key)) {
                e.preventDefault();
                if (e.key === 'ArrowDown') currentFocus = (currentFocus + 1) % items.length;
                if (e.key === 'ArrowUp') currentFocus = (currentFocus - 1 + items.length) % items.length;
                if (e.key === 'Enter') {
                    if (items[currentFocus]) {
                        items[currentFocus].click();
                    } else {
                        searchForm.dispatchEvent(new Event('submit'));
                    }
                }

                items.forEach((item, i) => item.classList.toggle('active', i === currentFocus));
            }
        });

        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
                searchResults.innerHTML = '';
                searchResults.classList.remove('active');
                currentFocus = -1;
            }
        });
    };

    // 8. Обновление UI после аутентификации
    const updateUIForAuthenticatedUser = (user) => {
        const authSection = document.querySelector('.navbar-collapse .ms-auto');
        if (!authSection) return;

        // Проверяем, есть ли уже кнопки (серверный рендеринг)
        let profileBtn = authSection.querySelector('a[href="/api/v1/user/profile/data"]');
        let logoutBtn = authSection.querySelector('#logoutBtn');
        let themeToggle = authSection.querySelector('.theme-toggle');

        if (!profileBtn || !logoutBtn || !themeToggle) {
            // Если кнопок нет, создаем их
            authSection.innerHTML = `
                <div class="d-flex align-items-center">
                    <a href="/api/v1/user/profile/data" class="btn btn-primary me-2">Профиль</a>
                    <button id="logoutBtn" class="btn btn-outline-danger me-2">Выйти</button>
                    <button class="btn btn-outline-secondary theme-toggle" id="themeToggle" title="Переключить тему">
                        ${document.body.classList.contains('dark-mode') ? '☀️' : '🌙'}
                    </button>
                </div>
            `;
        } else {
            // Если кнопки есть (серверный рендеринг), добавляем нужные классы
            profileBtn.classList.add('btn', 'btn-primary', 'me-2');
            logoutBtn.classList.add('btn', 'btn-outline-danger', 'me-2');
            themeToggle.classList.add('btn', 'btn-outline-secondary', 'theme-toggle');
            themeToggle.innerHTML = document.body.classList.contains('dark-mode') ? '☀️' : '🌙';
        }

        // Добавляем обработчик для кнопки "Выйти"
        logoutBtn = authSection.querySelector('#logoutBtn');
        logoutBtn?.addEventListener('click', async function(e) {
            e.preventDefault();
            this.disabled = true;
            this.textContent = "Выход...";
            window.location.href = "/api/v1/auth/logout";
        });

        initTheme();
    };

    // 9. Вспомогательные функции
    const escapeHtml = (unsafe) => {
        if (typeof unsafe !== 'string') return '';
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    };

    // 10. Обработчик переключения темы
    document.addEventListener('click', e => {
        if (e.target.closest('.theme-toggle')) {
            const isDark = document.body.classList.toggle('dark-mode');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');

            document.querySelectorAll('.theme-toggle').forEach(btn => {
                btn.innerHTML = isDark ? '☀️' : '🌙';
                btn.setAttribute('title', isDark ? 'Светлая тема' : 'Темная тема');
                btn.setAttribute('aria-label', isDark ? 'Переключить на светлую тему' : 'Переключить на темную тему');
            });
        }
    });

    // 11. Обработка тач-событий для tooltip
    const initTooltip = () => {
        const infoIcons = document.querySelectorAll('.custom-info-icon');

        infoIcons.forEach(icon => {
            // Обработка тач-событий для мобильных устройств
            icon.addEventListener('touchstart', function (e) {
                e.preventDefault();
                // Переключаем класс active для показа/скрытия tooltip
                this.classList.toggle('active');
                // Убираем active у других иконок
                infoIcons.forEach(otherIcon => {
                    if (otherIcon !== this) {
                        otherIcon.classList.remove('active');
                    }
                });
            });

            // Закрытие tooltip при клике/тапе вне иконки
            document.addEventListener('touchstart', function (e) {
                if (!icon.contains(e.target)) {
                    icon.classList.remove('active');
                }
            });
        });
    };

    // 12. Основная инициализация
    const initAll = () => {
        initTheme();
        initPasswordToggles();
        initLoginForm();
        initRegisterForm();
        initProfileModals();
        initProductSearch();
        initTooltip();
    };

    // Запускаем инициализацию
    initAll();
});