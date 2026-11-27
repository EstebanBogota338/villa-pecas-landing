/* =========================================================
   Consentimiento de cookies + Google Analytics 4

   - Sin consentimiento no se carga ninguna etiqueta de terceros.
   - Si el ID de medición sigue siendo el placeholder, no se hace
     ninguna petición (así no rompe nada mientras se configura).
   ========================================================= */

(function () {
    'use strict';

    /* TODO: reemplaza por tu ID de medición de GA4
       (GA4 > Administrador > Flujos de datos > tu sitio web). */
    var GA_MEASUREMENT_ID = 'G-XXXXXXXXXX';
    var STORAGE_KEY = 'villapecas-consent';

    var banner = document.getElementById('cookie-banner');

    function readConsent() {
        try {
            return window.localStorage.getItem(STORAGE_KEY);
        } catch (error) {
            return null;
        }
    }

    function saveConsent(value) {
        try {
            window.localStorage.setItem(STORAGE_KEY, value);
        } catch (error) {
            /* Modo privado o almacenamiento bloqueado: la elección vale
               solo para esta página, que es suficiente. */
        }
    }

    function loadAnalytics() {
        if (GA_MEASUREMENT_ID.indexOf('XXXX') !== -1) return;
        if (window.gtag) return;

        var script = document.createElement('script');
        script.async = true;
        script.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_MEASUREMENT_ID;
        document.head.appendChild(script);

        window.dataLayer = window.dataLayer || [];
        window.gtag = function () {
            window.dataLayer.push(arguments);
        };

        window.gtag('js', new Date());
        window.gtag('config', GA_MEASUREMENT_ID);
    }

    function onKeydown(event) {
        if (event.key === 'Escape') hideBanner();
    }

    function hideBanner() {
        if (banner) banner.hidden = true;
        document.removeEventListener('keydown', onKeydown);
        syncBannerState();
    }

    /* La barra fija de reserva y el aviso de cookies comparten el borde
       inferior: mientras el aviso esta abierto, la barra se esconde. */
    function syncBannerState() {
        document.documentElement.classList.toggle('has-banner', !!(banner && !banner.hidden));
    }

    var stored = readConsent();

    if (stored === 'granted') {
        loadAnalytics();
    } else if (stored !== 'denied' && banner) {
        banner.hidden = false;
        document.addEventListener('keydown', onKeydown);
        syncBannerState();
    }

    if (banner) {
        banner.addEventListener('click', function (event) {
            var button = event.target.closest('[data-consent]');
            if (!button) return;

            var value = button.getAttribute('data-consent');
            saveConsent(value);
            hideBanner();

            if (value === 'granted') loadAnalytics();
        });
    }

    /* Conversión: clic en cualquier enlace de WhatsApp.
       data-cta dice desde qué bloque de la página vino. */
    document.addEventListener('click', function (event) {
        var link = event.target.closest('a[href*="wa.me"]');
        if (!link) return;

        if (typeof window.gtag === 'function') {
            window.gtag('event', 'click_whatsapp', {
                cta_origen: link.getAttribute('data-cta') || 'sin-etiqueta'
            });
        }
    });
})();
