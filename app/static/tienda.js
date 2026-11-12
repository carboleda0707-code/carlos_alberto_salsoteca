// ==============================================================================
// LÓGICA FRONTEND TIENDA WEB & CARRITO - SALSOTECA CARLOS ALBERTO
// ==============================================================================

const API_URL = ""; // Relativo para consumir directamente FastAPI

let listaBannersDinamicos = [];
let sliderIndex = 0;
let sliderTimeout = null;

const TIEMPO_TRANSICION_FADE = 600;

// Estado Global del Carrito de Compras en LocalStorage
let carrito = JSON.parse(localStorage.getItem('salsoteca_carrito')) || [];

async function cargarBannersDinamicos() {
    const imgElem = document.getElementById("slider-img");
    const capElem = document.getElementById("slider-caption");
    if (!imgElem || !capElem) return;

    imgElem.style.transition = `opacity ${TIEMPO_TRANSICION_FADE}ms ease-in-out`;

    try {
        const res = await fetch(`${API_URL}/api/slider/`);
        if (res.ok) {
            const data = await res.json();
            if (data && data.length > 0) {
                listaBannersDinamicos = data;
                ciclarBannersDinamicos(imgElem, capElem);
                return;
            }
        }
    } catch (error) {
        console.error("Error al conectar con la API de banners:", error);
    }

    imgElem.src = "";
    imgElem.style.opacity = 0;
    capElem.innerText = "Salsoteca Carlos Alberto — Sube tus banners desde el panel administrativo";
}

function ciclarBannersDinamicos(imgElem, capElem) {
    if (listaBannersDinamicos.length === 0) return;

    const bannerActual = listaBannersDinamicos[sliderIndex];
    transicionarBanner(imgElem, capElem, bannerActual);

    let segundosVisibilidad = parseInt(bannerActual.duracion_segundos) || 5;
    let milisegundosEspera = segundosVisibilidad * 1000;

    sliderIndex = (sliderIndex + 1) % listaBannersDinamicos.length;

    if (sliderTimeout) clearTimeout(sliderTimeout);
    sliderTimeout = setTimeout(() => {
        ciclarBannersDinamicos(imgElem, capElem);
    }, milisegundosEspera);
}

function transicionarBanner(imgElem, capElem, banner) {
    const tempImage = new Image();
    tempImage.src = banner.imagen_url;

    tempImage.onload = () => {
        imgElem.style.opacity = 0;
        setTimeout(() => {
            imgElem.src = banner.imagen_url;
            capElem.innerText = banner.caption || `Banner Principal #${banner.posicion}`;
            imgElem.style.opacity = 1;
        }, TIEMPO_TRANSICION_FADE / 2);
    };
}

// ==========================================
// 2. CARGAR CARTELERA DE EVENTOS ACTIVOS
// ==========================================
let cacheEventosPublicos = [];

async function cargarCartelera() {
    const container = document.getElementById("container-cartelera");
    if (!container) return;

    try {
        const res = await fetch(`${API_URL}/api/reservas/eventos/?local_id=1`);
        cacheEventosPublicos = await res.json();

        if (!cacheEventosPublicos || cacheEventosPublicos.length === 0) {
            container.innerHTML = `<p style="text-align:center; color:#888; grid-column: span 3; padding: 20px;">No hay eventos activos en este momento.</p>`;
            return;
        }

        container.innerHTML = cacheEventosPublicos.map(ev => {
            let preciosHtml = '';
            if (ev.precio_cover && Number(ev.precio_cover) > 0) {
                preciosHtml += `<div style="color: #34d399; font-size: 13px; font-weight: 600;">🎟️ Cover: $${Number(ev.precio_cover).toFixed(2)}</div>`;
            }
            if (ev.precio_mesa && Number(ev.precio_mesa) > 0) {
                preciosHtml += `<div style="color: #fbbf24; font-size: 13px; font-weight: 600;">🍾 Mesa: $${Number(ev.precio_mesa).toFixed(2)}</div>`;
            }

            let imagenSrc = '';
            if (ev.imagen) {
                imagenSrc = ev.imagen.startsWith('http') ? ev.imagen : `https://pub-3244093a45bd47d9a30548ef0924bb49.r2.dev/${ev.imagen}`;
            } else {
                imagenSrc = '/static/images/default_evento.jpg';
            }

            return `
            <div class="event-card">
                <img src="${imagenSrc}" alt="${ev.nombre_evento}" loading="lazy">
                <div class="event-title">${ev.nombre_evento}</div>
                <div class="event-artist">🎤 ${ev.artista_orquesta || 'Varios Artistas'}</div>
                <p style="font-size:12px; color:#aaa; margin-bottom:8px;">📅 ${String(ev.fecha_hora).replace('T', ' ')}</p>
                <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 6px; margin-bottom: 14px; min-height: 36px; display: flex; flex-direction: column; justify-content: center; gap: 4px;">
                    ${preciosHtml || '<span style="color:#777; font-size:12px;">Entrada Libre / Consultar</span>'}
                </div>
                <button class="btn-reservar" onclick="abrirModalReserva(${ev.id})">👉 Elegir</button>
            </div>
            `;
        }).join('');

    } catch (error) {
        console.error("Error al cargar cartelera:", error);
    }
}

// 3. Cargar Historia (Eventos Pasados)
function cargarHistoria() {
    const container = document.getElementById("container-historia");
    if (!container) return;

    const historicos = [
        { titulo: "Tributo a Grupo Niche", fecha: "Viernes Pasado", img: "https://images.unsplash.com/photo-1429962714451-bb934ecdc4ec?auto=format&fit=crop&w=600&q=80" },
        { titulo: "Noche Guayaca de Maelo Ruiz", fecha: "Sábado Pasado", img: "https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?auto=format&fit=crop&w=600&q=80" },
        { titulo: "Mano a Mano Orquestas", fecha: "Domingo Pasado", img: "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?auto=format&fit=crop&w=600&q=80" }
    ];

    container.innerHTML = historicos.map(h => `
        <div class="event-card" style="opacity: 0.85;">
            <img src="${h.img}" alt="${h.titulo}" loading="lazy">
            <div class="event-title">${h.titulo}</div>
            <p style="color:#d4af37; font-size:12px;">🗓️ ${h.fecha} — ¡Lleno Total!</p>
        </div>
    `).join('');
}

// ==========================================
// 4. GESTIÓN DEL MODAL Y CÁLCULO DE RESERVA
// ==========================================
let eventoSeleccionadoActual = null;

function abrirModalReserva(eventoId) {
    eventoSeleccionadoActual = cacheEventosPublicos.find(e => Number(e.id) === Number(eventoId));
    
    if (!eventoSeleccionadoActual) {
        console.error("No se encontró el evento con ID:", eventoId);
        return;
    }
    
    const tituloModal = document.getElementById("modal-titulo");
    if (tituloModal) {
        tituloModal.innerHTML = `🎉 ${eventoSeleccionadoActual.nombre_evento} <br><small style="color:#d4af37; font-size:13px;">📅 ${String(eventoSeleccionadoActual.fecha_hora).replace('T', ' ')}</small>`;
    }
    
    document.getElementById("reserva-evento-id").value = eventoSeleccionadoActual.id;

    const inputCover = document.getElementById("input-cant-cover");
    const inputMesas = document.getElementById("input-cant-mesas");
    if (inputCover) inputCover.value = 1;
    if (inputMesas) inputMesas.value = 0;

    const precioCover = Number(eventoSeleccionadoActual.precio_cover) || 0.00;
    const precioMesa = Number(eventoSeleccionadoActual.precio_mesa) || 0.00;

    let htmlTarifas = `🎟️ <b>Cover por persona:</b> $${precioCover.toFixed(2)}`;
    if (precioMesa > 0) {
        htmlTarifas += `<br>🍾 <b>Mesa exclusiva:</b> $${precioMesa.toFixed(2)} (${eventoSeleccionadoActual.descripcion_mesa || 'Incluye atención VIP'})`;
    }
    document.getElementById("modal-detalles-tarifas").innerHTML = htmlTarifas;

    const contenedorMesas = document.getElementById("contenedor-input-mesas");
    if (contenedorMesas) {
        contenedorMesas.style.display = (precioMesa > 0) ? "block" : "none";
    }

    calcularTotalReserva();
    document.getElementById("modal-reserva").style.display = "flex";
}

function calcularTotalReserva() {
    if (!eventoSeleccionadoActual) return;
    
    const p_cover = Number(eventoSeleccionadoActual.precio_cover) || 10.00;
    const p_mesa = Number(eventoSeleccionadoActual.precio_mesa) || 0.00;

    const cantCover = parseInt(document.getElementById('input-cant-cover').value) || 0;
    const cantMesasInput = document.getElementById('input-cant-mesas');
    const cantMesas = cantMesasInput ? (parseInt(cantMesasInput.value) || 0) : 0;

    const total = (cantCover * p_cover) + (cantMesas * p_mesa);
    
    document.getElementById('display-total-pagar').innerText = `$${total.toFixed(2)}`;
    document.getElementById('reserva-monto-total').value = total;
}

function cerrarModal() {
    document.getElementById('modal-reserva').style.display = 'none';
}

// ==========================================
// 5. FUNCIONES DE CARRITO DE COMPRAS Y CHECKOUT
// ==========================================
function agregarItemAlCarritoDesdeModal(e) {
    e.preventDefault();

    if (!eventoSeleccionadoActual) return;

    const cantCover = parseInt(document.getElementById("input-cant-cover").value) || 0;
    const inputMesas = document.getElementById("input-cant-mesas");
    const cantMesas = inputMesas ? (parseInt(inputMesas.value) || 0) : 0;
    const subtotal = parseFloat(document.getElementById("reserva-monto-total").value) || 0;

    if (cantCover === 0 && cantMesas === 0) {
        alert("Debes seleccionar al menos un cover o una mesa.");
        return;
    }

    const itemCarrito = {
        evento_id: eventoSeleccionadoActual.id,
        titulo: eventoSeleccionadoActual.nombre_evento || "Evento Salsoteca",
        tipo: 'local',
        cantidad_covers: cantCover,
        cantidad_mesas: cantMesas,
        subtotal: subtotal
    };

    carrito.push(itemCarrito);
    guardarYActualizarCarrito();
    cerrarModal();
    abrirModalCarrito();
}

function guardarYActualizarCarrito() {
    localStorage.setItem('salsoteca_carrito', JSON.stringify(carrito));
    actualizarBadgeCarrito();
}

function actualizarBadgeCarrito() {
    const badge = document.getElementById('cart-count');
    if (badge) {
        badge.innerText = carrito.length;
    }
}

// Abrir Panel Lateral Derecho del Carrito
function abrirModalCarrito() {
    const sidebar = document.getElementById('cart-sidebar');
    const overlay = document.getElementById('cart-overlay');
    if (sidebar && overlay) {
        renderizarContenidoCarrito();
        overlay.style.display = 'block';
        setTimeout(() => {
            sidebar.style.right = '0px';
        }, 10);
    }
}

// Cerrar Panel Lateral Derecho
function cerrarPanelCarrito() {
    const sidebar = document.getElementById('cart-sidebar');
    const overlay = document.getElementById('cart-overlay');
    if (sidebar && overlay) {
        sidebar.style.right = '-420px';
        setTimeout(() => { 
            overlay.style.display = 'none'; 
        }, 300);
    }
}

// Abrir Modal Central de Checkout desde el Panel Lateral
function abrirModalCheckoutDesdePanel() {
    if (carrito.length === 0) {
        alert("Tu carrito está vacío.");
        return;
    }
    cerrarPanelCarrito();
    const modalCentro = document.getElementById('modal-checkout-centro');
    if (modalCentro) {
        modalCentro.style.display = 'flex';
    }
}

// Cerrar Modal Central de Checkout
function cerrarModalCheckoutCentro() {
    const modalCentro = document.getElementById('modal-checkout-centro');
    if (modalCentro) {
        modalCentro.style.display = 'none';
    }
}

// Volver del Modal Central al Panel Lateral del Carrito
function volverAlPanelCarrito() {
    cerrarModalCheckoutCentro();
    abrirModalCarrito();
}

// Renderizar contenido en el panel lateral derecho
function renderizarContenidoCarrito() {
    const contenedor = document.getElementById('carrito-items-container');
    const totalSpan = document.getElementById('carrito-total-monto');
    
    if (!contenedor) return;

    try {
        const guardado = localStorage.getItem('salsoteca_carrito');
        carrito = guardado ? JSON.parse(guardado) : [];
        if (!Array.isArray(carrito)) carrito = [];
    } catch (e) {
        carrito = [];
    }

    contenedor.innerHTML = '';
    let totalGeneral = 0;

    if (carrito.length === 0) {
        contenedor.innerHTML = `
            <div style="text-align: center; color: #888; padding: 50px 20px;">
                <p style="font-size: 24px; margin-bottom: 10px;">🛒</p>
                <p style="font-size: 14px; color: #d6d5df;">Tu carrito está vacío</p>
            </div>`;
        if (totalSpan) totalSpan.innerText = "$0.00";
        actualizarBadgeCarrito();
        return;
    }

    carrito.forEach((item, index) => {
        const titulo = item.titulo || "Evento Salsoteca";
        const cantCover = Number(item.cantidad_covers) || 0;
        const cantMesas = Number(item.cantidad_mesas) || 0;
        const subtotalItem = Number(item.subtotal) || 0;
        totalGeneral += subtotalItem;

        contenedor.innerHTML += `
            <div style="background: #0b0c10; border: 1px solid rgba(212,175,55,0.25); padding: 12px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                <div style="flex: 1; padding-right: 10px;">
                    <h4 style="color: #fbbf24; font-size: 13px; margin: 0 0 4px 0; font-weight: 600;">${titulo}</h4>
                    <p style="font-size: 11px; color: #aaa; margin: 0;">Covers: ${cantCover} | Mesas: ${cantMesas}</p>
                </div>
                <div style="text-align: right; min-width: 80px;">
                    <span style="color: #34d399; font-weight: bold; font-size: 13px; display: block; margin-bottom: 4px;">$${subtotalItem.toFixed(2)}</span>
                    <button type="button" onclick="eliminarDelCarrito(${index})" style="background: none; border: none; color: #ff5555; font-size: 11px; cursor: pointer; padding: 0;">🗑️ Quitar</button>
                </div>
            </div>
        `;
    });

    if (totalSpan) {
        totalSpan.innerText = `$${totalGeneral.toFixed(2)}`;
    }
    actualizarBadgeCarrito();
}

function eliminarDelCarrito(index) {
    carrito.splice(index, 1);
    guardarYActualizarCarrito();
    renderizarContenidoCarrito();
}

// Envío Final del Checkout del Carrito Masivo
async function enviarCheckoutCarrito(event) {
    event.preventDefault();

    if (carrito.length === 0) {
        alert("El carrito está vacío.");
        return;
    }

    const formData = new FormData();
    formData.append("cedula", document.getElementById("checkout-cedula").value);
    formData.append("nombre", document.getElementById("checkout-nombre").value);
    formData.append("telefono", document.getElementById("checkout-telefono").value);
    formData.append("email", document.getElementById("checkout-email")?.value || "");
    formData.append("items_json", JSON.stringify(carrito));
    
    const archivoInput = document.getElementById("checkout-comprobante");
    if (archivoInput.files.length > 0) {
        formData.append("comprobante", archivoInput.files[0]);
    } else {
        alert("Por favor, adjunta el comprobante de transferencia.");
        return;
    }

    try {
        const response = await fetch('/api/checkout/carrito', {
            method: 'POST',
            body: formData
        });

        const resultado = await response.json();
        if (response.ok) {
            alert(resultado.mensaje);
            localStorage.removeItem('salsoteca_carrito');
            carrito = [];
            actualizarBadgeCarrito();
            cerrarPanelCarrito();
            location.reload();
        } else {
            alert("Error: " + (resultado.detail || "No se pudo procesar la solicitud"));
        }
    } catch (error) {
        console.error("Error en la red:", error);
        alert("Ocurrió un error al procesar el pago.");
    }
}

// ==========================================
// 6. CREACIÓN DE EVENTO PERSONALIZADO (CLIENTE)
// ==========================================
async function agregarEventoPersonalizadoAlCarrito(event) {
    event.preventDefault();

    const nombreEvento = document.getElementById("custom-nombre-evento").value;
    const tipoCelebracion = document.getElementById("custom-tipo-celebracion").value;
    const fechaHora = document.getElementById("custom-fecha-hora").value;
    const cantPersonas = parseInt(document.getElementById("custom-cant-personas").value) || 2;
    const cantMesas = parseInt(document.getElementById("custom-cant-mesas").value) || 0;
    const flyerFile = document.getElementById("custom-flyer-file").files[0];

    if (!nombreEvento || !fechaHora) {
        alert("Por favor completa los campos obligatorios del evento.");
        return;
    }

    // Calculamos el subtotal utilizando las variables globales de precio
    const subtotal = (cantPersonas * PRECIO_COVER_PLANTILLA) + (cantMesas * PRECIO_MESA_PLANTILLA);

    // Guardamos temporalmente en el carrito local o enviamos directamente
    const itemPersonalizado = {
        titulo: `${tipoCelebracion}: ${nombreEvento}`,
        tipo: 'personalizado',
        nombre_evento: nombreEvento,
        tipo_celebracion: tipoCelebracion,
        fecha_hora: fechaHora,
        cantidad_covers: cantPersonas,
        cantidad_mesas: cantMesas,
        subtotal: subtotal,
        has_flyer: !!flyerFile
    };

    carrito.push(itemPersonalizado);
    guardarYActualizarCarrito();
    cerrarModalCreaTuEvento();
    abrirModalCarrito();
}

// Inicialización general de la página
document.addEventListener("DOMContentLoaded", () => {
    cargarBannersDinamicos();
    cargarCartelera();
    cargarHistoria();
    try {
        const guardado = localStorage.getItem('salsoteca_carrito');
        carrito = guardado ? JSON.parse(guardado) : [];
        if (!Array.isArray(carrito)) carrito = [];
    } catch (e) {
        carrito = [];
    }
    actualizarBadgeCarrito();
});