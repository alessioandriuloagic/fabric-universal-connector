import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import HttpApi from 'i18next-http-backend';

i18n
    .use(HttpApi)
    .use(initReactI18next)
    .init({
        fallbackLng: 'en-US',
        supportedLngs: ['en-US', 'es', 'he', 'it'],
        debug: false,
        useSuspense: false,
        backend: {
            // Try per-language folder first, then fallback to a single file per locale in the root locales folder
            loadPath: [
                "/assets/locales/{{lng}}/translation.json",
                "/assets/locales/translation.{{lng}}.json"
            ]
        }

    });

export default i18n;