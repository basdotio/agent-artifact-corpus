# Catálogo de stacks

Usalo para armar la recomendación del Paso 2: elegí 2-3 que encajen con las respuestas del usuario y presentá cada uno con caso de uso, pros, contras, costo y mantenimiento.

> **Precios aproximados**, en USD y a modo orientativo. Cambian seguido: antes de que el usuario le pase un presupuesto al cliente, sugerile confirmarlos en el sitio de cada servicio. El dominio va aparte (un `.com.ar` se paga anual a NIC Argentina en pesos; un `.com` ronda USD 10-15/año).

## Guía rápida de elección

| Situación | Stack sugerido |
|---|---|
| Una página, entrega rápida, el cliente no edita | 1. HTML + Tailwind |
| Varias páginas, buen SEO, el cliente no edita (o edita poco) | 2. Astro |
| Varias páginas y el cliente quiere editar textos/fotos | 2. Astro + CMS · 5. WordPress · 6. No-code |
| Funcionalidades dinámicas (turnos propios, área privada, integraciones, APIs) | 3. Next.js |
| El cliente quiere tocar todo solo y no hay quien mantenga código | 6. No-code |
| Vende productos online | 7. Tienda (Tiendanube / Shopify) |
| Ya tiene hosting compartido pago con cPanel | 1. HTML o 5. WordPress |

## Hosting estático gratuito (para stacks 1 y 2)

| Plataforma | Uso comercial en plan gratis | Notas |
|---|---|---|
| **Cloudflare Pages** | Sí | Ancho de banda generoso, muy rápido, dominios propios gratis. Muy buena opción por defecto. |
| **Netlify** | Sí | Incluye **Netlify Forms** (formularios sin backend, cupo mensual limitado en el plan gratis). Deploy por drag & drop o CLI. |
| **Vercel** | **No** (Hobby es solo para uso personal/no comercial) | Para un cliente corresponde el plan Pro (~USD 20/mes por miembro). Ideal para Next.js. |
| **GitHub Pages** | Evitar para sitios comerciales | Sin formularios ni funciones de servidor. |

---

## 1. HTML + Tailwind (un archivo o pocos archivos estáticos)

- **Conviene para**: landing de una sola página, entrega en el día, cliente que no edita contenido.
- **Pros**: cero dependencias, carga rapidísimo, se hostea en cualquier lado (incluso hosting compartido), fácil de entregar.
- **Contras**: el cliente no puede editar solo; repetir partes en varias páginas es manual.
- **Tailwind**: el CDN (`<script src="https://cdn.tailwindcss.com">`) sirve para prototipar y landings chicas, pero Tailwind no lo recomienda para producción. Para entregar, mejor compilar con la **CLI standalone de Tailwind** (un binario, sin Node) y servir el CSS generado. Si se usa el CDN, dejarlo anotado en el README.
- **Hosting**: Cloudflare Pages o Netlify (gratis) · hosting compartido que ya tenga el cliente.
- **Costo**: USD 0 + dominio.
- **Formulario**: Netlify Forms (si se hostea en Netlify) · **Formspree** o **Web3Forms** (plan gratis con cupo mensual; solo hace falta un endpoint/clave) · o solo WhatsApp + `mailto:` si el cliente no quiere formulario.
- **Mantenimiento**: muy bajo. Cambios de texto = editar HTML.

## 2. Astro (sitio estático moderno), opcionalmente con CMS

- **Conviene para**: varias páginas o secciones, SEO importante, posible blog; sitio rápido sin servidor.
- **Pros**: componentes reutilizables, genera HTML estático (rapidísimo), Markdown/MDX para contenido, integra Tailwind fácil, imágenes optimizadas.
- **Contras**: requiere Node y paso de build; el cliente no edita sin un CMS.
- **CMS para que el cliente edite**: **Keystatic** o **Decap CMS** (guardan el contenido en el repo, sin costo) · **TinaCMS** (editor visual, plan gratis para pocos editores). Suma 1-2 horas de configuración.
- **Hosting**: Cloudflare Pages o Netlify (gratis).
- **Costo**: USD 0 + dominio (CMS gratis en los planes básicos).
- **Formulario**: igual que el stack 1 (Netlify Forms / Formspree / Web3Forms).
- **Mantenimiento**: bajo. Actualizar dependencias de vez en cuando.

## 3. Next.js

- **Conviene para**: funcionalidades dinámicas — sistema de turnos propio, área de clientes, integraciones con APIs, contenido desde base de datos, multi-idioma complejo.
- **Pros**: máxima flexibilidad, ecosistema enorme, backend y frontend en un mismo proyecto.
- **Contras**: sobredimensionado para una landing simple; más mantenimiento; el hosting comercial ideal (Vercel) es pago.
- **Hosting**: Vercel Pro (~USD 20/mes) · Netlify (plan gratis permite uso comercial, con límites) · Cloudflare (con adaptador).
- **Costo**: USD 0-20/mes + servicios que use (base de datos, email).
- **Formulario**: Server Action o Route Handler que manda mail con **Resend** (plan gratis con cupo mensual) u otro proveedor; guardar la API key en variables de entorno.
- **Mantenimiento**: medio. Actualizaciones de framework y dependencias.

## 4. Vite + React (SPA estática)

- **Conviene para**: landing con mucha interacción (configuradores, calculadoras, animaciones complejas) que igual es estática.
- **Pros**: rápido de desarrollar, se hostea como estático.
- **Contras**: peor SEO que HTML/Astro si no se prerenderiza; más JS en el cliente. Para la mayoría de las landings, Astro es mejor opción.
- **Hosting / costo / formulario**: igual que el stack 1.
- **Mantenimiento**: bajo-medio.

## 5. WordPress

- **Conviene para**: el cliente quiere editar todo solo, va a tener blog, o ya trabaja con WordPress / tiene hosting con cPanel.
- **Pros**: el cliente conoce el panel, miles de plugins, blog nativo, editor de bloques.
- **Contras**: más lento si no se optimiza, necesita actualizaciones de seguridad periódicas, los plugins pueden romper cosas; construir el diseño a medida lleva más tiempo (tema de bloques propio o un builder).
- **Hosting**: hosting compartido (Hostinger, DonWeb, etc.).
- **Costo**: ~USD 3-10/mes de hosting + eventuales plugins pagos.
- **Formulario**: Contact Form 7 o WPForms (versión gratis) + plugin SMTP para que los mails no caigan en spam.
- **Mantenimiento**: medio-alto (actualizaciones, backups, seguridad). Conviene ofrecerlo como abono mensual.

## 6. No-code: Framer, Webflow, Wix, Carrd

- **Conviene para**: el cliente quiere editar visualmente sin depender de nadie; no hay quien mantenga código.
- **Pros**: edición visual, hosting incluido, formularios incluidos, rápido de armar.
- **Contras**: costo mensual, lock-in (no se exporta fácil), menos control fino; el código generado acá no se usa (se arma dentro de la plataforma). En este caso la skill entrega: dirección visual, copy completo, estructura de secciones y guía de armado, y el usuario lo arma en la plataforma.
- **Costo aproximado** (plan con dominio propio): **Carrd Pro** ~USD 19/año (ideal para una página simple) · **Framer** ~USD 10-30/mes · **Webflow** ~USD 15-30/mes · **Wix** ~USD 17-30/mes.
- **Formulario**: el nativo de la plataforma.
- **Mantenimiento**: bajo para el desarrollador; lo maneja el cliente.

## 7. Tienda online: Tiendanube / Shopify

- **Conviene para**: el cliente vende productos con carrito, stock y pagos.
- **Pros**: pagos (Mercado Pago), envíos, stock y panel listos. **Tiendanube** es muy usada en Argentina y tiene integración nativa con Mercado Pago y correos locales.
- **Contras**: costo mensual y/o comisión por venta; personalización limitada al sistema de temas.
- **Costo**: Tiendanube tiene plan inicial con comisión por venta y planes pagos en pesos · Shopify desde ~USD 29-39/mes.
- **Formulario**: el nativo.
- **Alternativa liviana**: landing estática (stack 1 o 2) con catálogo y botón "Pedir por WhatsApp" por producto, si son pocos productos y no necesita pagos online.
- **Mantenimiento**: bajo.

---

## Extras frecuentes

| Necesidad | Solución simple |
|---|---|
| Turnos / reservas | Embed de **Cal.com** o **Calendly** (planes gratis) · Google Calendar (páginas de reserva) · si es salud, plataformas de turnos del rubro |
| Multi-idioma | Astro con i18n nativo · en HTML simple, una carpeta por idioma (`/en/`) |
| Blog | Astro + Markdown/CMS · WordPress |
| Mapa | Embed de Google Maps (iframe con `loading="lazy"` y `title`) |
| Pagos sueltos | Link de pago de Mercado Pago |
| Analytics | Google Analytics 4 (`gtag.js`) · Meta Pixel · alternativas livianas: Plausible / Umami |
