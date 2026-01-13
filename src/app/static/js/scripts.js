document.addEventListener("DOMContentLoaded", () => {
    if (typeof bootstrap === 'undefined') {
        console.error('Bootstrap не загружен!');
        return;
    }

    // Инициализация CSRF-токена в формах
    const initCsrfToken = () => {
        const getCsrfToken = () => {
            return document.cookie
                .split('; ')
                .find(row => row.startsWith('csrf_token='))
                ?.split('=')[1] || '';
        };

        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            const csrfInput = form.querySelector('input[name="_csrf_token"]');
            if (csrfInput) {
                csrfInput.value = getCsrfToken();
            }
        });
    };

    // Тема
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

        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
            const newTheme = e.matches ? 'dark' : 'light';
            document.body.classList.toggle('dark-mode', newTheme === 'dark');
            localStorage.setItem('theme', newTheme);
            updateThemeButtons(newTheme === 'dark');
        });
    };

    // Переключатели пароля
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

    // Универсальный fetch
    const secureFetch = async (url, options = {}) => {
        const csrfToken = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrf_token='))
            ?.split('=')[1];

        if (!csrfToken) {
            throw new Error('CSRF токен не найден. Пожалуйста, обновите страницу.');
        }

        const headers = {
            'Accept': 'application/json',
            'X-CSRF-Token': csrfToken,
            ...options.headers,
        };

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);

        try {
            const response = await fetch(url, {
                ...options,
                headers,
                credentials: 'include',
                signal: controller.signal,
            });
            clearTimeout(timeoutId);

            if (!response.ok) {
                if (response.status === 401 && response.headers.get('X-Error-Type') === 'authentication_error') {
                    const refreshResponse = await fetch('/auth/refresh', {
                        method: 'POST',
                        credentials: 'include',
                        headers: { 'X-CSRF-Token': csrfToken },
                    });
                    if (refreshResponse.ok) {
                        return secureFetch(url, options);
                    }
                    throw new Error('Ваша сессия истекла. Пожалуйста, войдите заново.');
                } else if (response.status === 403) {
                    throw new Error('Недействительный CSRF-токен. Пожалуйста, обновите страницу и попробуйте снова.');
                } else if (response.status === 500) {
                    window.location.href = '/error';
                }
                const data = await response.json();
                throw data.error || { message: 'Неизвестная ошибка' };
            }

            return await response.json();
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('Превышено время ожидания запроса');
            }
            if (error.message.includes('CSRF')) {
                showError('globalError', error.message);
                setTimeout(() => window.location.reload(), 3000);
            } else if (error.message === 'Ваша сессия истекла. Пожалуйста, войдите заново.') {
                const loginModal = new bootstrap.Modal(document.getElementById('loginModal'));
                loginModal.show();
            }
            throw error;
        }
    };

    // Функция для работы с HTMLResponse
    const checkAuthAndRedirect = async (url) => {
        const csrfToken = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrf_token='))
            ?.split('=')[1];

        if (!csrfToken) {
            throw new Error('CSRF token not found');
        }

        try {
            const response = await fetch(url, {
                credentials: 'include',
                headers: { 'X-CSRF-Token': csrfToken },
            });

            if (response.ok) {
                window.location.href = url;
            } else if (response.status === 401 && response.headers.get('X-Error-Type') === 'authentication_error') {
                const refreshResponse = await fetch('/auth/refresh', {
                    method: 'POST',
                    credentials: 'include',
                    headers: { 'X-CSRF-Token': csrfToken },
                });

                if (refreshResponse.ok) {
                    const retryResponse = await fetch(url, {
                        method: 'HEAD',
                        credentials: 'include',
                        headers: { 'X-CSRF-Token': csrfToken },
                    });

                    if (retryResponse.ok) {
                        window.location.href = url;
                    } else {
                        throw new Error('Доступ запрещен после обновления токенов');
                    }
                } else {
                    throw new Error('Не удалось обновить токены');
                }
            } else {
                throw new Error(`Ошибка сервера: ${response.status}`);
            }
        } catch (error) {
            console.error('Ошибка в checkAuthAndRedirect:', error);
            showError('globalError', error.message || 'Не удалось перейти к странице профиля');
            window.location.href = '/';
        }
    };

    // UI-утилиты
    const showError = (containerId, errorData) => {
        const container = document.getElementById(containerId);
        if (!container) return;

        if (!errorData || (typeof errorData === 'string' && errorData.trim() === '')) {
            container.textContent = '';
            container.classList.add('d-none');
            return;
        }

        if (typeof errorData === 'string') {
            container.textContent = errorData;
        } else if (errorData.code === 'validation_error' && errorData.details?.fields) {
            const errorMessages = errorData.details.fields.map(err => `${err.field}: ${err.message}`).join(', ');
            container.textContent = `Ошибки валидации: ${errorMessages}`;
        } else {
            container.textContent = errorData.message || 'Неизвестная ошибка';
        }
        container.classList.remove('d-none');
    };

    const showSuccess = (message, elementId = 'globalSuccess') => {
        const container = document.getElementById(elementId);
        if (!container) return;

        const textContainer = document.getElementById(`${elementId}Text`);
        if (textContainer) {
            textContainer.textContent = message;
        } else {
            container.textContent = message;
        }
        container.classList.remove('d-none');
        container.classList.add('d-block');

        setTimeout(() => {
            container.classList.remove('d-block');
            container.classList.add('d-none');
            if (textContainer) textContainer.textContent = '';
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
        if (!userData || typeof userData !== 'object') {
            console.warn('Некорректные данные userData:', userData);
            return;
        }

        const emailElement = document.querySelector('.profile-header p');
        if (emailElement && userData.email) {
            emailElement.textContent = escapeHtml(userData.email);
        }

        document.querySelectorAll('.detail-item').forEach(item => {
            const label = item.querySelector('strong')?.textContent.trim();
            const valueSpan = item.querySelector('span');
            if (!valueSpan) return;

            if (label === 'Пол:') {
                const genderText = userData.gender === 'male' ? 'Мужской' :
                                   userData.gender === 'female' ? 'Женский' : 'Не указан';
                valueSpan.textContent = escapeHtml(genderText);
            } else if (label === 'Возраст:') {
                const ageText = userData.age ? `${escapeHtml(String(userData.age))} лет` : 'Не указано';
                valueSpan.textContent = ageText;
            } else if (label === 'Рост:') {
                const heightText = userData.height ? `${escapeHtml(String(userData.height))} см` : 'Не указано';
                valueSpan.textContent = heightText;
            } else if (label === 'Вес:') {
                const weightText = userData.weight ? `${escapeHtml(String(userData.weight))} кг` : 'Не указано';
                valueSpan.textContent = weightText;
            } else if (label === 'Цель:') {
                valueSpan.textContent = escapeHtml(userData.goal || 'Не указана');
            } else if (label === 'Уровень физической активности:') {
                const kfaText = userData.kfa ? `${escapeHtml(String(userData.kfa))}-й уровень` : 'Не указано';
                valueSpan.textContent = kfaText;
            } else if (label === 'Регистрация:') {
                valueSpan.textContent = escapeHtml(userData.created_at || 'Не указано');
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

    // ГЛОБАЛЬНЫЕ ТОСТЫ И ОБРАБОТКА ОШИБОК
    const ensureToastContainer = () => {
        let container = document.getElementById('toastContainer');
        if (container) return container;
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'position-fixed top-0 end-0 p-3';
        container.style.zIndex = '1080'; // выше модалок
        document.body.appendChild(container);
        return container;
    };

    const showToast = (message, variant = 'danger', options = {}) => {
        const container = ensureToastContainer();
        const id = `t_${Date.now()}_${Math.random().toString(16).slice(2)}`;
        const autohide = options.autohide !== undefined ? options.autohide : true;
        const delay = options.delay || 5000;
        const header = options.header || 'Ошибка';

        const toastEl = document.createElement('div');
        toastEl.className = `toast align-items-center text-bg-${variant} border-0`;
        toastEl.id = id;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <strong class="me-2">${header}:</strong> ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        container.appendChild(toastEl);
        const toast = new bootstrap.Toast(toastEl, { autohide, delay });
        toast.show();
        toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
    };

    const extractErrorMessageFromResponse = async (response) => {
        const ct = response.headers.get('content-type') || '';
        if (ct.includes('application/json')) {
            try {
                const data = await response.clone().json();
                // Формат бэкенда: { status: 'error', error: { message, details? } }
                if (data?.error?.message) return data.error.message;
            } catch (_) { /* ignore */ }
        }
        return `Ошибка сервера: ${response.status}`;
    };

    const initGlobalErrorHandlers = () => {
        // глобальные необработанные исключения
        window.addEventListener('error', (event) => {
            // игнорим ошибки скриптов с внешних доменов без подробностей
            if (!event.message) return;
            showToast(event.message, 'danger', { header: 'Необработанная ошибка' });
        });

        window.addEventListener('unhandledrejection', (event) => {
            const reason = event.reason;
            let msg = 'Произошла непредвиденная ошибка';
            if (reason) {
                if (typeof reason === 'string') msg = reason;
                else if (reason?.message) msg = reason.message;
            }
            showToast(msg, 'danger', { header: 'Ошибка в промисе' });
        });

        // перехват fetch для сетевых/5xx ошибок вне secureFetch
        if (!window.__fetchPatched) {
            const originalFetch = window.fetch.bind(window);
            window.fetch = async (input, init = {}) => {
                try {
                    const response = await originalFetch(input, init);
                    // позволяем явным вызовам отключать глобальные тосты
                    const suppress = init && (init.suppressGlobalError === true);
                    if (!response.ok && !suppress) {
                        if (response.status >= 500) {
                            const msg = await extractErrorMessageFromResponse(response);
                            showToast(msg, 'danger', { header: 'Сервер недоступен' });
                        }
                        // 401/403/422 обычно обрабатываются локально (secureFetch/showError)
                    }
                    return response;
                } catch (err) {
                    const suppress = init && (init.suppressGlobalError === true);
                    if (!suppress) {
                        const msg = (err && err.message) ? err.message : 'Сеть недоступна или истек таймаут';
                        showToast(msg, 'danger', { header: 'Сетевая ошибка' });
                    }
                    throw err;
                }
            };
            window.__fetchPatched = true;
        }

        // экспорт в глобальную область для точечных уведомлений
        window.appShowToast = showToast;
    };

    // Перехват кликов по защищённым ссылкам и проверка/refresh перед переходом
    const initProtectedNavigation = () => {
        const isProtectedHref = (href) => {
            try {
                const url = new URL(href, window.location.origin);
                // По умолчанию считаем защищёнными все роуты под /user/
                return url.origin === window.location.origin && url.pathname.startsWith('/user/');
            } catch (_) {
                return false;
            }
        };

        document.addEventListener('click', (e) => {
            // Только левый клик без модификаторов
            if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

            const a = e.target.closest('a[href]');
            if (!a) return;

            const href = a.getAttribute('href');
            if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:')) return;

            const explicitProtected = a.hasAttribute('data-protected');
            const protectedLink = explicitProtected || isProtectedHref(href);
            if (!protectedLink) return;

            // Внутренние ссылки только
            const abs = new URL(href, window.location.origin);
            if (abs.origin !== window.location.origin) return;

            e.preventDefault();
            checkAuthAndRedirect(abs.pathname + abs.search + abs.hash);
        }, { capture: true });
    };

    // Форма логина
    const initLoginForm = () => {
        const form = document.getElementById('loginForm');
        if (!form) return;

        const csrfInput = form.querySelector('input[name="_csrf_token"]');
        if (csrfInput) {
            const csrfToken = document.cookie
                .split('; ')
                .find(row => row.startsWith('csrf_token='))
                ?.split('=')[1];
            if (csrfToken) {
                csrfInput.value = csrfToken;
            }
        }

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
                await secureFetch('/auth/login', {
                    method: 'POST',
                    body: new URLSearchParams(formData),
                    headers: { "Content-Type": "application/x-www-form-urlencoded" }
                });

                const userData = await secureFetch("/user/me");
                updateProfileUI(userData);

                const modal = bootstrap.Modal.getInstance(document.getElementById('loginModal'));
                if (modal) {
                    modal.hide();
                    showSuccess(`Добро пожаловать, ${userData.username || 'Пользователь'}!`);
                    setTimeout(() => window.location.reload(), 700);
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

    // Форма регистрации
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
                await secureFetch("/auth/register", {
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
                    showSuccess("Регистрация прошла успешно! Теперь вы можете войти.");
                    const loginModal = new bootstrap.Modal(document.getElementById('loginModal'));
                    setTimeout(() => loginModal.show(), 1500);
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

    // Модальные окна профиля
    const initProfileModals = () => {
        // Редактирование профиля
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
                        // Преобразуем числовые поля в числа
                        if (['age', 'height', 'weight', 'kfa'].includes(key) && value) {
                            jsonData[key] = Number(value);
                        } else {
                            jsonData[key] = value || null;
                        }
                    });

                    await secureFetch('/user/profile/update', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(jsonData)
                    });

                    const updatedUserData = await secureFetch('/user/me');
                    updateProfileUI(updatedUserData);
                    window.location.href = '/user/profile/data'

                    const modal = bootstrap.Modal.getInstance(editProfileModal);
                    if (modal) {
                        modal.hide();
                        showSuccess('Профиль успешно обновлен!');
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

        // Смена пароля
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

                    await secureFetch('/auth/password/change', {
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
                        showSuccess('Пароль успешно изменён!');
                        changePasswordForm.reset();
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

        // Подписка/отписка
        const subscribeModal = document.getElementById('subscribeModal');
        if (subscribeModal) {
            const subscribeForm = document.getElementById('subscribeForm');
            const confirmSubscribeBtn = document.getElementById('confirmSubscribeBtn');

            confirmSubscribeBtn?.addEventListener('click', async () => {
                confirmSubscribeBtn.disabled = true;
                const originalText = confirmSubscribeBtn.textContent;
                const isSubscribing = originalText === 'Подписаться';
                confirmSubscribeBtn.textContent = isSubscribing ? 'Подписка...' : 'Отписка...';

                clearFormErrors('subscribeForm');
                showError('subscribeError', '');

                try {
                    await secureFetch(`/user/${isSubscribing ? 'subscribe' : 'unsubscribe'}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ _csrf_token: subscribeForm.querySelector('[name="_csrf_token"]').value })
                    });

                    const modal = bootstrap.Modal.getInstance(subscribeModal);
                    if (modal) {
                        modal.hide();
                        showSuccess(isSubscribing ? 'Вы успешно подписались на рассылку!' : 'Вы успешно отписались от рассылки!');
                        setTimeout(() => window.location.reload(), 1500);
                    } else {
                        showSuccess(isSubscribing ? 'Вы успешно подписались на рассылку!' : 'Вы успешно отписались от рассылки!');
                        setTimeout(() => window.location.reload(), 1500);
                    }
                } catch (error) {
                    showError('subscribeError', error.message || `Ошибка при ${isSubscribing ? 'подписке' : 'отписке'} от рассылки`);
                } finally {
                    confirmSubscribeBtn.disabled = false;
                    confirmSubscribeBtn.textContent = originalText;
                }
            });
        }
    };

    // Поиск продуктов
    const initProductSearch = () => {
        const searchConfigs = [
            {
                formId: 'searchProductForm',
                inputId: 'productQuery',
                resultsId: 'searchResults',
                errorId: 'searchError',
            },
            {
                formId: 'productDetailSearchForm',
                inputId: 'productDetailQuery',
                resultsId: 'productDetailSearchResults',
                errorId: 'productDetailSearchError',
            },
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
                    const data = await secureFetch(`/product/search?query=${encodeURIComponent(query)}`, {
                        signal: abortController.signal,
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
                searchResults.innerHTML = items.length === 0
                    ? '<div class="suggestion-item">Ничего не найдено</div>'
                    : items.map(item => `
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
                        checkAuthAndRedirect(`/product/${item.dataset.id}`);
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
                        await secureFetch('/product/pending', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ name: query }),
                        });
                        modal.hide();
                        showSuccess(`Продукт "${query}" добавлен в очередь на рассмотрение!`);
                    } catch (error) {
                        showError(errorId, error.message || 'Ошибка при добавлении продукта');
                    }
                };
            };

            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                const query = e.target.value.trim();
                
                // Clear previous timeout and abort any pending requests
                clearTimeout(searchTimeout);
                if (abortController) {
                    abortController.abort();
                }
                
                // Clear previous results and errors
                searchResults.innerHTML = '';
                searchResults.classList.remove('active');
                if (searchError) {
                    searchError.textContent = '';
                    searchError.style.display = 'none';
                }
                
                if (query.length < 3) {
                    lastSearchData = null;
                    return;
                }
                
                // Only search after a delay when user stops typing
                searchTimeout = setTimeout(() => {
                    performSearch(query).catch(() => {
                        // Ignore aborted requests
                    });
                }, 500); // Reduced from 3000ms to 500ms for better UX
            });

            searchForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const query = searchInput.value.trim();

                // Clear previous errors
                if (searchError) {
                    searchError.textContent = '';
                    searchError.style.display = 'none';
                }

                // Validate input
                if (query.length < 3) {
                    showError(errorId, 'Запрос должен содержать минимум 3 символа');
                    return;
                }

                const button = analyzeBtn || searchForm.querySelector('button[type="submit"]');
                if (button) {
                    const originalText = button.textContent;
                    try {
                        button.disabled = true;
                        button.textContent = 'Поиск...';

                        const data = await performSearch(query, true);
                        const id = data.exact_match?.id || lastSearchData?.exact_match?.id;

                        if (id) {
                            checkAuthAndRedirect(`/product/${id}`);
                        } else {
                            openPendingProductModal(query);
                        }
                    } catch (error) {
                        // Only show error if it's not an aborted request
                        if (error.name !== 'AbortError') {
                            showError(errorId, error.message || 'Ошибка при выполнении поиска');
                        }
                    } finally {
                        if (button) {
                            button.disabled = false;
                            button.textContent = originalText;
                        }
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

    // Tooltips
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

    // Кастомные выпадающие списки
    const initCustomSelects = () => {
        const customSelects = document.querySelectorAll('.custom-select');

        customSelects.forEach(select => {
            const display = select.querySelector('.custom-select-display');
            const options = select.querySelector('.custom-select-options');
            const hiddenInput = select.nextElementSibling && select.nextElementSibling.tagName === 'INPUT' ? select.nextElementSibling : null;
            const optionItems = options ? options.querySelectorAll('li') : [];

            if (!display || !options || !hiddenInput) {
                console.warn('Неполная структура custom-select:', select);
                return;
            }

            display.addEventListener('click', function (e) {
                e.preventDefault();
                const isActive = select.classList.contains('active');
                document.querySelectorAll('.custom-select').forEach(s => {
                    s.classList.remove('active');
                });
                if (!isActive) {
                    select.classList.add('active');
                }
            });

            optionItems.forEach(option => {
                option.addEventListener('click', function (e) {
                    const value = this.getAttribute('data-value');
                    const text = this.textContent.trim();
                    display.textContent = text;
                    hiddenInput.value = value || '';
                    select.classList.remove('active');
                });
            });
        });

        document.addEventListener('click', function (e) {
            if (!e.target.closest('.custom-select')) {
                document.querySelectorAll('.custom-select').forEach(s => {
                    s.classList.remove('active');
                });
            }
        });
    };

    // Обработчики для новых кнопок
    const initNavigationButtons = () => {
        // Кнопка профиля
        const profileBtn = document.querySelector('.profile-btn');
        if (profileBtn) {
            profileBtn.addEventListener('click', () => {
                checkAuthAndRedirect('/user/profile/data');
            });
        }

        // Кнопка выхода
        const logoutBtn = document.querySelector('.logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', async () => {
                try {
                    await secureFetch('/auth/logout', {
                        method: 'POST',
                        credentials: 'include',
                    });
                    showSuccess('Вы успешно вышли из аккаунта!');
                    setTimeout(() => window.location.replace('/'), 500);
                } catch (error) {
                    showError('globalError', 'Ошибка при выходе: ' + (error.message || 'Неизвестная ошибка'));
                }
            });
        }
    };

    // Инициализация
    initCsrfToken();
    initTheme();
    initPasswordToggles();
    initGlobalErrorHandlers();
    initProtectedNavigation();
    initLoginForm();
    initRegisterForm();
    initProfileModals();
    initProductSearch();
    initTooltips();
    initCustomSelects();
    initNavigationButtons();

    // Обработка действия отписки из параметра URL
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('action') === 'unsubscribe') {
        secureFetch("/user/me")
            .then(userData => {
                // Пользователь авторизован
                if (window.location.pathname !== '/user/profile/data') {
                    // Перенаправляем на профиль с параметром
                    window.location.href = '/user/profile/data?action=unsubscribe';
                } else {
                    // Уже на профиле, открываем модальное окно
                    const subscribeModal = new bootstrap.Modal(document.getElementById('subscribeModal'));
                    subscribeModal.show();

                    // Удаляем параметр из URL
                    const url = new URL(window.location.href);
                    url.searchParams.delete('action');
                    window.history.replaceState({}, '', url.toString());
                }
            })
            .catch(error => {
                // Пользователь не авторизован, открываем модальное окно логина
                const loginModal = new bootstrap.Modal(document.getElementById('loginModal'));
                loginModal.show();

                // Обработчик закрытия модального окна логина (если закрыто без входа, удаляем параметр)
                loginModal._element.addEventListener('hidden.bs.modal', () => {
                    secureFetch("/user/me")
                        .catch(() => {
                            // Всё ещё не авторизован, удаляем параметр
                            const url = new URL(window.location.href);
                            url.searchParams.delete('action');
                            window.history.replaceState({}, '', url.toString());
                        });
                }, { once: true });
            });
    }
});
