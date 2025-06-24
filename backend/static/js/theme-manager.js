/**
 * Менеджер тем для plan-fact сервиса
 */
class ThemeManager {
    constructor() {
        this.STORAGE_KEY = 'gh_theme_preference';
        this.COOKIE_KEY = 'gh_theme';
        this.DARK_THEME_CLASS = 'dark-theme';
        this.themes = {
            light: 'light',
            dark: 'dark'
        };
        
        this.init();
    }

    init() {
        this.applyThemeImmediately();
        
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initializeComponents());
        } else {
            this.initializeComponents();
        }
    }

    setCookie(name, value, days) {
        const expires = new Date();
        expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));
        document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/;SameSite=Lax`;
    }

    getCookie(name) {
        const nameEQ = name + "=";
        const ca = document.cookie.split(';');
        for(let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') c = c.substring(1, c.length);
            if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
        }
        return null;
    }

    applyThemeImmediately() {
        const cookieTheme = this.getCookie(this.COOKIE_KEY);
        const savedTheme = cookieTheme || localStorage.getItem(this.STORAGE_KEY) || this.themes.light;
        
        if (savedTheme === this.themes.dark) {
            document.documentElement.classList.add(this.DARK_THEME_CLASS);
            document.body.classList.add(this.DARK_THEME_CLASS);
        }
        
        if (cookieTheme && cookieTheme !== localStorage.getItem(this.STORAGE_KEY)) {
            localStorage.setItem(this.STORAGE_KEY, cookieTheme);
        }
    }

    initializeComponents() {
        this.createThemeSwitcher();
        this.bindEvents();
        
        const currentTheme = this.getCurrentTheme();
        this.updateSwitcherUI(currentTheme);
        
        console.log('ThemeManager initialized with theme:', currentTheme);
    }

    createThemeSwitcher() {
        let switcher = document.getElementById('theme-switcher');
        
        if (!switcher) {
            switcher = document.createElement('button');
            switcher.id = 'theme-switcher';
            switcher.innerHTML = '<i class="fas fa-moon"></i><span>Тёмная тема</span>';
            switcher.title = 'Переключить тему';
            
            // Добавляем в header_login
            const headerLogin = document.querySelector('.header_login');
            if (headerLogin) {
                headerLogin.appendChild(switcher);
            }
        }

        this.themeSwitcher = switcher;
    }

    bindEvents() {
        if (this.themeSwitcher) {
            this.themeSwitcher.addEventListener('click', () => {
                this.toggleTheme();
            });
        }
    }

    getCurrentTheme() {
        const cookieTheme = this.getCookie(this.COOKIE_KEY);
        return cookieTheme || localStorage.getItem(this.STORAGE_KEY) || this.themes.light;
    }

    toggleTheme() {
        const currentTheme = this.getCurrentTheme();
        const newTheme = currentTheme === this.themes.dark ? this.themes.light : this.themes.dark;
        this.setTheme(newTheme);
    }

    setTheme(theme) {
        this.applyTheme(theme, true);
    }

    applyTheme(theme, updateStorage = true) {
        const htmlElement = document.documentElement;
        const bodyElement = document.body;

        if (theme === this.themes.light) {
            htmlElement.classList.remove(this.DARK_THEME_CLASS);
            bodyElement.classList.remove(this.DARK_THEME_CLASS);
        } else {
            htmlElement.classList.add(this.DARK_THEME_CLASS);
            bodyElement.classList.add(this.DARK_THEME_CLASS);
        }

        if (updateStorage) {
            localStorage.setItem(this.STORAGE_KEY, theme);
            this.setCookie(this.COOKIE_KEY, theme, 365);
        }

        this.updateSwitcherUI(theme);
        console.log('Theme applied:', theme);
    }

    updateSwitcherUI(theme) {
        if (!this.themeSwitcher) return;

        const iconElement = this.themeSwitcher.querySelector('i');
        const textElement = this.themeSwitcher.querySelector('span');
        
        if (theme === this.themes.dark) {
            if (iconElement) iconElement.className = 'fas fa-sun';
            if (textElement) textElement.textContent = 'Светлая тема';
            this.themeSwitcher.title = 'Переключить на светлую тему';
        } else {
            if (iconElement) iconElement.className = 'fas fa-moon';
            if (textElement) textElement.textContent = 'Тёмная тема';
            this.themeSwitcher.title = 'Переключить на тёмную тему';
        }
    }

    static init() {
        if (!window.themeManager) {
            window.themeManager = new ThemeManager();
        }
        return window.themeManager;
    }
}

// Автоматическая инициализация
ThemeManager.init();
