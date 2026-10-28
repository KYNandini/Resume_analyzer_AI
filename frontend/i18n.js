const i18n = {
  currentLanguage: localStorage.getItem('lang') || 'en',
  translations: {},

  async loadTranslations(lang) {
    try {
      const response = await fetch(`locales/${lang}.json`);
      if (!response.ok) {
        throw new Error(`Failed to load translations for ${lang}`);
      }
      this.translations = await response.json();
      this.currentLanguage = lang;
      localStorage.setItem('lang', lang);
      this.updateDOM();
    } catch (error) {
      console.error('Error loading translations:', error);
      // Fallback to English if loading fails
      if (lang !== 'en') {
        this.loadTranslations('en');
      }
    }
  },

  updateDOM() {
    // Update elements with data-i18n attribute
    document.querySelectorAll('[data-i18n]').forEach(element => {
      const key = element.getAttribute('data-i18n');
      const translation = this.translations[key];
      if (translation) {
        element.textContent = translation;
      }
    });

    // Update placeholder attributes
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
      const key = element.getAttribute('data-i18n-placeholder');
      const translation = this.translations[key];
      if (translation) {
        element.setAttribute('placeholder', translation);
      }
    });

    // Update language select dropdown to match current language
    const langSelect = document.getElementById('languageSelect');
    if (langSelect) {
      langSelect.value = this.currentLanguage;
    }
  },

  setLanguage(lang) {
    this.loadTranslations(lang);
  },

  init() {
    this.loadTranslations(this.currentLanguage);

    // Setup language dropdown listener
    const langSelect = document.getElementById('languageSelect');
    if (langSelect) {
      langSelect.addEventListener('change', (e) => {
        this.setLanguage(e.target.value);
      });
    }
  }
};

// Initialize i18n when DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
  i18n.init();
});
