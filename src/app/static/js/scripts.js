document.addEventListener("DOMContentLoaded", () => {
    if (typeof bootstrap === 'undefined') {
        console.error('Bootstrap не загружен!');
        return;
    }

    // 1. Тема
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

        document.querySelectorAll('.theme-toggle').forEach(btn => {
            btn.addEventListener('click', () => {
                const isDark = document.body.classList.toggle('dark-mode');
                localStorage.setItem('theme', isDark ? 'dark' : 'light');
                updateThemeButtons(isDark);
            });
        });

        // Обновление темы при изменении системных настроек
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
            const newTheme = e.matches ? 'dark' : 'light';
            document.body.classList.toggle('dark-mode', newTheme === 'dark');
            localStorage.setItem('theme', newTheme);
            updateThemeButtons(newTheme === 'dark');
        });
    };

    // 2. Переключатели пароля
    const initPasswordToggles = () => {
        document.addEventListener('click', e => {
            const toggleBtn = e.target.closest('.toggle-password');
            if (!toggleBtn) return;

            const input = document.getElementById(toggleBtn.dataset.target);
            if (!input) return;

            const isVisible = input.type === 'password';
            input.type = isVisible ? 'text' : 'password';

            const icon = toggleBtn.querySelector('i');
            if (icon) {
                icon.className = isVisible ? 'bi bi-eye' : 'bi bi-eye-slash';
            }

            toggleBtn.setAttribute('aria-pressed', isVisible);
            toggleBtn.setAttribute('aria-label', isVisible ? 'Скрыть пароль' : 'Показать пароль');
        }, { capture: true });
    };

    // 3. Универсальный fetch
    const secureFetch = async (url, options = {}) => {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
        const headers = {
            'Accept': 'application/json',
            ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
            ...options.headers
        };

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

            if (!response.headers.get('content-type')?.includes('application/json')) {
                const text = await response.text();
                throw new Error(`Неверный формат ответа: ${text}`);
            }

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || data.message || 'Неизвестная ошибка');
            }
            return data;
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('Превышено время ожидания запроса');
            }
            throw error;
        }
    };

    // 4. UI-утилиты
    const showError = (containerId, message) => {
        const container = document.getElementById(containerId);
        if (container) {
            container.textContent = message;
            container.classList.remove('d-none');
        }
    };

    const showSuccess = (message, elementId = 'globalSuccess') => {
        const successElement = document.getElementById(elementId);
        if (!successElement) return;

        const textElement = successElement.querySelector('#globalSuccessText') || successElement.querySelector('span');
        if (!textElement) return;

        textElement.textContent = message;
        successElement.classList.remove('d-none');
        successElement.classList.add('show');

        setTimeout(() => {
            successElement.classList.remove('show');
            successElement.classList.add('d-none');
        }, 3000);
    };

    const clearFormErrors = (formId) => {
        const form = document.getElementById(formId);
        if (!form) return;

        form.querySelectorAll('.invalid-feedback').forEach(el => {
            el.textContent = '';
            el.classList.add('d-none');
        });
        form.querySelectorAll('.is-invalid').forEach(el => {
            el.classList.remove('is-invalid');
        });
    };

    const updateProfileUI = (userData) => {
        const emailElement = document.querySelector('.profile-header p');
        if (emailElement && userData.email) {
            emailElement.textContent = userData.email;
        }

        document.querySelectorAll('.detail-item').forEach(item => {
            const label = item.querySelector('strong')?.textContent.trim();
            const valueSpan = item.querySelector('span');
            if (!valueSpan) return;

            if (label === 'Рост:') {
                valueSpan.textContent = userData.height ? `${userData.height} см` : 'Не указано';
            } else if (label === 'Вес:') {
                valueSpan.textContent = userData.weight ? `${userData.weight} кг` : 'Не указано';
            } else if (label === 'Возраст:') {
                valueSpan.textContent = userData.age || 'Не указано';
            } else if (label === 'Уровень физической активности:') {
                valueSpan.textContent = userData.activity_level || 'Не указано';
            }
        });
    };

    const escapeHtml = (unsafe) => {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    };

    // 5. Форма логина
    const initLoginForm = () => {
        const form = document.getElementById('loginForm');
        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = form.querySelector('button[type="submit"]');
            const originalText = btn.textContent;

            btn.disabled = true;
            btn.textContent = "Вход...";

            clearFormErrors('loginForm');
            showError('loginError', '');

            try {
                const formData = new FormData(form);
                await secureFetch('/api/v1/auth/login', {
                    method: 'POST',
                    body: new URLSearchParams(formData),
                    headers: { "Content-Type": "application/x-www-form-urlencoded" }
                });

                const userData = await secureFetch("/api/v1/user/me");
                updateProfileUI(userData);

                const modal = bootstrap.Modal.getInstance(document.getElementById('loginModal'));
                if (modal) {
                    modal.hide();
                    modal._element.addEventListener('hidden.bs.modal', () => {
                        showSuccess(`Добро пожаловать, ${userData.username || 'Пользователь'}!`);
                        setTimeout(() => window.location.reload(), 700);
                    }, { once: true });
                } else {
                    showSuccess(`Добро пожаловать, ${userData.username || 'Пользователь'}!`);
                    setTimeout(() => window.location.reload(), 700);
                }
            } catch (error) {
                showError('loginError', error.message || "Неверное имя пользователя или пароль");
            } finally {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        });
    };

    // 6. Форма регистрации
    const initRegisterForm = () => {
        const form = document.getElementById('registerForm');
        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = form.querySelector('button[type="submit"]');
            const originalText = btn.textContent;

            btn.disabled = true;
            btn.textContent = "Регистрация...";

            clearFormErrors('registerForm');
            showError('registerError', '');

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
                        password
                    }),
                    headers: { 'Content-Type': 'application/json' }
                });

                const modal = bootstrap.Modal.getInstance(document.getElementById('registerModal'));
                if (modal) {
                    modal.hide();
                    modal._element.addEventListener('hidden.bs.modal', () => {
                        showSuccess("Регистрация прошла успешно! Теперь вы можете войти.");
                        const loginModal = new bootstrap.Modal(document.getElementById('loginModal'));
                        setTimeout(() => loginModal.show(), 3000);
                    }, { once: true });
                } else {
                    showSuccess("Регистрация прошла успешно! Теперь вы можете войти.");
                }
            } catch (error) {
                showError('registerError', error.message || "Ошибка при регистрации");
            } finally {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        });
    };

    // 7. Модальные окна профиля
    const initProfileModals = () => {
        const editProfileModal = document.getElementById('editProfileModal');
        if (editProfileModal) {
            const editForm = document.getElementById('editProfileForm');
            const saveBtn = document.getElementById('saveProfileBtn');

            saveBtn?.addEventListener('click', async () => {
                saveBtn.disabled = true;
                const originalText = saveBtn.textContent;
                saveBtn.textContent = "Сохранение...";

                clearFormErrors('editProfileForm');
                showError('editProfileError', '');

                try {
                    const formData = new FormData(editForm);
                    const jsonData = {};
                    formData.forEach((value, key) => {
                        jsonData[key] = ['age', 'height', 'weight'].includes(key) && value ? Number(value) : value || null;
                    });

                    await secureFetch('/api/v1/user/profile/update', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(jsonData)
                    });

                    const updatedUserData = await secureFetch('/api/v1/user/me');
                    updateProfileUI(updatedUserData);

                    const modal = bootstrap.Modal.getInstance(editProfileModal);
                    if (modal) {
                        modal.hide();
                        modal._element.addEventListener('hidden.bs.modal', () => {
                            showSuccess('Профиль успешно обновлен!');
                        }, { once: true });
                    } else {
                        showSuccess('Профиль успешно обновлен!');
                    }
                } catch (error) {
                    showError('editProfileError', error.message || 'Ошибка при обновлении профиля');
                } finally {
                    saveBtn.disabled = false;
                    saveBtn.textContent = originalText;
                }
            });
        }

        const changePasswordModal = document.getElementById('changePasswordModal');
        if (changePasswordModal) {
            const changePasswordForm = document.getElementById('changePasswordForm');
            const savePasswordBtn = document.getElementById('savePasswordBtn');

            savePasswordBtn?.addEventListener('click', async () => {
                savePasswordBtn.disabled = true;
                const originalText = savePasswordBtn.textContent;
                savePasswordBtn.textContent = "Сохранение...";

                clearFormErrors('changePasswordForm');
                showError('changePasswordError', '');

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
                        }),
                        headers: { 'Content-Type': 'application/json' }
                    });

                    const modal = bootstrap.Modal.getInstance(changePasswordModal);
                    if (modal) {
                        modal.hide();
                        modal._element.addEventListener('hidden.bs.modal', () => {
                            showSuccess('Пароль успешно изменён!');
                            changePasswordForm.reset();
                        }, { once: true });
                    } else {
                        showSuccess('Пароль успешно изменён!');
                        changePasswordForm.reset();
                    }
                } catch (error) {
                    showError('changePasswordError', error.message || 'Ошибка при смене пароля');
                } finally {
                    savePasswordBtn.disabled = false;
                    savePasswordBtn.textContent = originalText;
                }
            });
        }
    };

    // 8. Поиск продуктов
    const initProductSearch = () => {
        const searchConfigs = [
            {
                formId: 'searchProductForm',
                inputId: 'productQuery',
                resultsId: 'searchResults',
                errorId: 'searchError'
            },
            {
                formId: 'productDetailSearchForm',
                inputId: 'productDetailQuery',
                resultsId: 'productDetailSearchResults',
                errorId: 'productDetailSearchError'
            }
        ];

        searchConfigs.forEach(({ formId, inputId, resultsId, errorId }) => {
            const searchForm = document.getElementById(formId);
            const searchInput = document.getElementById(inputId);
            const searchResults = document.getElementById(resultsId);
            const searchError = document.getElementById(errorId);
            const analyzeBtn = searchForm?.querySelector('button[type="submit"]');

            if (!searchForm || !searchInput || !searchResults) return;

            let currentFocus = -1;
            let abortController = null;
            let lastSearchData = null;

            const performSearch = async (query, fromForm = false) => {
                abortController?.abort();
                abortController = new AbortController();

                try {
                    const data = await secureFetch(`/api/v1/product/search?query=${encodeURIComponent(query)}`, {
                        signal: abortController.signal
                    });

                    lastSearchData = data;

                    if (!fromForm) {
                        const items = data.exact_match ? [data.exact_match, ...data.suggestions] : data.suggestions || [];
                        renderResults(items);
                    }

                    return data;
                } catch (error) {
                    if (error.name !== 'AbortError') {
                        showError(errorId, 'Ошибка поиска: ' + error.message);
                    }
                    throw error;
                }
            };

            const renderResults = (items) => {
                searchResults.innerHTML = items.length === 0 ? '<div class="suggestion-item">Ничего не найдено</div>' : items.map(item => `
                    <div class="suggestion-item" data-id="${item.id}">
                        <div class="suggestion-content">
                            <i class="bi bi-box suggestion-icon"></i>
                            <div class="suggestion-title">${escapeHtml(item.title)}</div>
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

            const openPendingProductModal = (query) => {
                const modal = new bootstrap.Modal(document.getElementById('addPendingProductModal'));
                const pendingProductName = document.getElementById('pendingProductName');
                const pendingProductInput = document.getElementById('pendingProductInput');
                const confirmBtn = document.getElementById('confirmPendingProductBtn');

                if (!modal || !pendingProductName || !pendingProductInput || !confirmBtn) {
                    showError(errorId, 'Ошибка: модальное окно недоступно');
                    return;
                }

                pendingProductName.textContent = escapeHtml(query);
                pendingProductInput.value = query;
                modal.show();

                confirmBtn.onclick = async () => {
                    try {
                        await secureFetch('/api/v1/product/pending', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ name: query })
                        });
                        modal.hide();
                        showSuccess(`Продукт "${query}" добавлен в очередь на рассмотрение!`);
                    } catch (error) {
                        showError(errorId, error.message || 'Ошибка при добавлении продукта');
                    }
                };
            };

            searchInput.addEventListener('input', _.debounce((e) => {
                const query = e.target.value.trim();
                if (query.length < 2) {
                    searchResults.innerHTML = '';
                    searchResults.classList.remove('active');
                    lastSearchData = null;
                    return;
                }
                performSearch(query);
            }, 300));

            searchForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const query = searchInput.value.trim();

                // Проверка минимальной длины запроса
                if (query.length < 2) {
                    showError(errorId, 'Запрос должен содержать минимум 2 символа');
                    return;
                }

                // Если кнопка анализа отсутствует, просто продолжаем
                if (analyzeBtn) {
                    analyzeBtn.disabled = true;
                    const originalText = analyzeBtn.textContent;
                    analyzeBtn.textContent = 'Идет анализ...';

                    try {
                        const data = await performSearch(query, true);
                        const id = data.exact_match?.id || lastSearchData?.exact_match?.id;

                        if (id) {
                            window.location.href = `/api/v1/product/${id}`;
                        } else {
                            openPendingProductModal(query);
                        }
                    } catch (error) {
                        // Ошибка уже отображается в performSearch
                    } finally {
                        analyzeBtn.disabled = false;
                        analyzeBtn.textContent = originalText;
                    }
                } else {
                    try {
                        const data = await performSearch(query, true);
                        const id = data.exact_match?.id || lastSearchData?.exact_match?.id;

                        if (id) {
                            window.location.href = `/api/v1/product/${id}`;
                        } else {
                            openPendingProductModal(query);
                        }
                    } catch (error) {
                        // Ошибка уже отображается в performSearch
                    }
                }
            });

            searchInput.addEventListener('keydown', (e) => {
                const items = searchResults.querySelectorAll('.suggestion-item');
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    currentFocus = (currentFocus + 1) % items.length;
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    currentFocus = (currentFocus - 1 + items.length) % items.length;
                } else if (e.key === 'Enter' && items[currentFocus]) {
                    e.preventDefault();
                    items[currentFocus].click();
                }

                items.forEach((item, i) => item.classList.toggle('active', i === currentFocus));
            });

            document.addEventListener('click', (e) => {
                if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
                    searchResults.innerHTML = '';
                    searchResults.classList.remove('active');
                    currentFocus = -1;
                }
            });
        });
    };

    // 9. Tooltips
    const initTooltips = () => {
        document.querySelectorAll('.custom-info-icon').forEach(icon => {
            icon.addEventListener('click', (e) => {
                e.stopPropagation();
                const isActive = icon.classList.contains('active');
                document.querySelectorAll('.custom-info-icon').forEach(i => i.classList.remove('active'));
                if (!isActive) icon.classList.add('active');
            });
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.custom-info-icon')) {
                document.querySelectorAll('.custom-info-icon').forEach(icon => icon.classList.remove('active'));
            }
        });
    };

    // Инициализация
    initTheme();
    initPasswordToggles();
    initLoginForm();
    initRegisterForm();
    initProfileModals();
    initProductSearch();
    initTooltips();
});