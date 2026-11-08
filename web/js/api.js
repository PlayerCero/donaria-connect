/* Donaria Connect – conexión con la API (fase 3).
   Si la API responde, reemplaza los datos de ejemplo de data.js por los de la base y las acciones
   (registrar, responder, lanzar olas, revisar alertas) se guardan de verdad. Si no responde en
   unos segundos, la web sigue funcionando con data.js, como el prototipo original.

   Dirección de la API: http://127.0.0.1:8000 por defecto. Para otra: index.html?api=https://…
   Para forzar los datos de ejemplo: index.html?modo=ejemplo */
(() => {
  const qs = new URLSearchParams(location.search);
  const guardar = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) {} };
  const leer = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  if (qs.get("api")) guardar("donaria.api", qs.get("api"));
  const BASE = (qs.get("api") || leer("donaria.api") || "http://127.0.0.1:8000").replace(/\/+$/, "");

  const API = { base: BASE, conectado: false, error: null, tokens: {}, ahora: null };
  window.API = API;

  /* ---------- HTTP ---------- */
  async function pedir(metodo, ruta, { cuerpo, rol, espera = 150000 } = {}) {
    const ctl = new AbortController(), t = setTimeout(() => ctl.abort(), espera);
    const headers = { "Content-Type": "application/json" };
    if (rol) headers.Authorization = "Bearer " + API.tokens[rol];
    try {
      const r = await fetch(BASE + ruta, { method: metodo, headers, body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo), signal: ctl.signal });
      const texto = await r.text();
      const datos = texto ? JSON.parse(texto) : null;
      if (!r.ok) {
        const d = datos && datos.detail;
        const msg = typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => String(x.msg || "").replace(/^Value error, /, "")).join(" ") : `Error ${r.status}`;
        throw Object.assign(new Error(msg), { status: r.status });
      }
      return datos;
    } catch (e) {
      if (e.name === "AbortError") throw new Error("La base tardó demasiado en responder. Inténtalo otra vez.");
      if (e instanceof TypeError) throw new Error("No hay conexión con la API.");
      throw e;
    } finally { clearTimeout(t); }
  }
  const token = async (rol, id) => (API.tokens[rol] = (await pedir("POST", "/auth/token-demo", { cuerpo: { rol, id } })).token);

  /* ---------- Formatos: del JSON de la API a la forma de data.js ---------- */
  const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"];
  const fh = (iso) => (iso ? String(iso).replace("T", " ").slice(0, 16) : null);
  const hora = (iso) => fh(iso).slice(11);
  const enDia = (iso, ref) => { const f = fh(iso); if (f.slice(0, 10) === ref.slice(0, 10)) return hora(iso);
    const [, m, d] = f.slice(0, 10).split("-").map(Number); return `${d} ${MESES[m - 1]} ${hora(iso)}`; };
  const recibida = (iso, hoy) => { const f = fh(iso); if (f.slice(0, 10) === hoy) return "hoy " + hora(iso).replace(/^0/, "");
    const [, m, d] = f.slice(0, 10).split("-").map(Number); return `el ${d} ${MESES[m - 1]}`; };
  const cel = (t) => (t && /^\d{9}$/.test(t) ? `${t.slice(0, 3)} ${t.slice(3, 6)} ${t.slice(6)}` : t || "—");
  const horas = (hasta) => Math.max(0, Math.ceil((new Date(hasta) - new Date(API.ahora)) / 3.6e6));

  // Dirección y horario no están en la base: se toman de data.js (o de aquí) por id de institución.
  const INFO_EXTRA = { 3: { distrito: "Jesús María", direccion: "Av. Edgardo Rebagliati 490", horario: "Consulta el horario en el hospital" } };
  const infoInst = (id) => (window.DB.instituciones || []).find((i) => i.id_institucion === id) || INFO_EXTRA[id] || {};

  const aNecesidad = (n) => ({
    id_necesidad: n.id_necesidad, tipo_sangre: n.tipo_sangre, zona: n.zona, unidades_meta: n.unidades_meta, estado: n.estado,
    fecha_creacion: fh(n.fecha_creacion), unidades_obtenidas: n.unidades_obtenidas,
    olas: n.olas.map((o) => ({ numero_ola: o.numero_ola, radio_km: o.radio_km, donantes_notificados: o.donantes_notificados,
      respondieron: o.respondieron, fecha_envio: enDia(o.fecha_envio, n.fecha_creacion) })),
  });
  const aDonante = (p) => ({
    id_donante: p.id_donante, nombres: p.nombres, dni_mask: p.dni.replace(/\*/g, "•"), tipo_sangre: p.tipo_sangre, distrito: p.distrito,
    telefono_whatsapp: cel(p.telefono_whatsapp), estado_verificacion: p.estado_verificacion, fecha_ultima_donacion: p.ultima_donacion,
    sexo: p.sexo, canal: window.DB.donante?.canal || "WhatsApp",
    proxima: p.proxima_fecha_posible, puede: p.puede_donar_hoy, motivo: p.motivo_si_no_puede, unidades: p.unidades_convocatorias,
  });
  const aConvocatoria = (c, hoy) => c && ({ id_necesidad: c.id_necesidad, tipo_sangre: c.tipo_sangre, institucion_id: c.id_institucion,
    distancia_km: c.distancia_km, recibida: recibida(c.fecha_envio, hoy), ola: c.numero_ola, respuesta: c.respuesta });
  const aAlerta = (a) => ({ id_alerta: a.id_alerta, donante: a.codigo_donante, dni_mask: a.dni.replace(/\*/g, "•"), regla: a.regla_disparada,
    institucion: a.institucion, fecha: fh(a.fecha), horas_restantes: horas(a.revisar_antes_de), estado: a.estado_revision });

  /* ---------- Carga ---------- */
  async function cargarDonante(hoy) {
    const [p, c] = await Promise.all([pedir("GET", "/donantes/me", { rol: "donante" }), pedir("GET", "/donantes/me/convocatoria", { rol: "donante" })]);
    return {
      donante: aDonante(p),
      consentimiento: { version_texto: "1.0", fecha_hora: fh(p.consentimiento_fecha), vigente: p.consentimiento_vigente },
      donaciones: p.historial.map((h) => ({ fecha: h.fecha, institucion: h.institucion, unidades_convocatoria: null,
        tipo: h.fuente === "institucion" ? "Confirmada por el banco de sangre" : "Registrada por ti" })),
      convocatoriaDonante: aConvocatoria(c, hoy),
    };
  }
  const cargarNecesidades = async () => (await pedir("GET", "/necesidades", { rol: "clinica" })).map(aNecesidad);

  async function cargarTodo() {
    const salud = await pedir("GET", "/health", { espera: 3000 });   // ¿la API está viva? (si no, data.js)
    API.ahora = salud.ahora; API.didit = !!salud.didit;
    pantallaCarga();
    // Una sola llamada primero: despierta la base sin servidor de Azure y, si hace falta, abre el
    // inicio de sesión de Microsoft una sola vez. Luego todo va en paralelo.
    await pedir("GET", "/health/db");
    const idDonante = Number(leer("donaria.donante")) || 0;
    // El donante que se registró desde esta web (guardado en el navegador) o, si no hay, uno de demostración.
    const tokDonante = token("donante", idDonante).then(() => { API.donanteRegistrado = idDonante > 0; },
      () => { guardar("donaria.donante", null); return token("donante", 0); });
    const tc = await token("clinica", 1);
    await Promise.all([token("equipo", 0), tokDonante]);
    const idInst = JSON.parse(atob(tc.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))).inst;
    const [necesidades, est, inst, alertas, resumen, don] = await Promise.all([
      cargarNecesidades(),
      pedir("GET", "/necesidades/estimado?radio_km=6", { rol: "clinica" }),
      pedir("GET", "/instituciones", { rol: "equipo" }),
      pedir("GET", "/alertas", { rol: "equipo" }),
      pedir("GET", "/alertas/resumen", { rol: "equipo" }),
      cargarDonante(salud.fecha_referencia),
    ]);
    const instituciones = inst.map((i) => ({ distrito: "—", direccion: "", horario: "Consulta el horario con el banco de sangre",
      ...infoInst(i.id_institucion), id_institucion: i.id_institucion, razon_social: i.razon_social,
      autorizacion_sanitaria: i.autorizacion_sanitaria, estado_afiliacion: i.estado_afiliacion }));
    // Todo listo: recién ahora se reemplazan los datos de ejemplo (nunca queda a medias).
    Object.assign(window.DB, {
      hoy: salud.fecha_referencia, necesidades, instituciones, verificados6km: est.donantes_elegibles,
      alertas: alertas.map(aAlerta), alertasRevisadas: resumen.revisadas,
      usuario: { ...window.DB.usuario, id_institucion: idInst }, ...don,
    });
    API.conectado = true;
  }

  function pantallaCarga() {
    const app = document.getElementById("app");
    if (app) app.innerHTML = `<div class="hub"><header class="hub-head"><h1>Donaria Connect</h1>
      <p class="muted" role="status">Conectando con la base de datos… La primera vez puede tardar hasta un minuto
      y abrir el inicio de sesión de Microsoft en otra pestaña.</p></header></div>`;
  }

  API.listo = qs.get("modo") === "ejemplo" ? Promise.resolve()
    : cargarTodo().catch((e) => { API.conectado = false; API.error = e.message; console.warn("[Donaria] Sin API, se usan datos de ejemplo:", e.message); });

  /* ---------- Acciones (cada una guarda en la base y refresca los datos de esa pantalla) ---------- */
  const refrescarNecesidades = async () => { window.DB.necesidades = await cargarNecesidades(); };
  const refrescarDonante = async () => Object.assign(window.DB, await cargarDonante(window.DB.hoy));

  API.registrar = async (datos) => {
    const r = await pedir("POST", "/donantes", { cuerpo: datos });
    API.tokens.donante = r.token; guardar("donaria.donante", String(r.id_donante)); API.donanteRegistrado = true;
    await refrescarDonante(); return r;
  };
  API.usarDonanteDemo = async () => { guardar("donaria.donante", null); API.donanteRegistrado = false; await token("donante", 0); await refrescarDonante(); };
  API.responder = async (idNecesidad, respuesta) => {
    await pedir("PUT", `/donantes/me/convocatorias/${idNecesidad}/respuesta`, { rol: "donante", cuerpo: { respuesta } });
    await refrescarDonante();
  };
  API.revocar = async () => { await pedir("DELETE", "/donantes/me/consentimiento", { rol: "donante" }); await refrescarDonante(); };
  API.crearNecesidad = async (tipo, meta, radio) => {
    const n = await pedir("POST", "/necesidades", { rol: "clinica", cuerpo: { tipo_sangre: tipo, unidades_meta: meta } });
    // La primera ola puede llegar hasta 6 o 10 km: se lanzan en orden las olas hasta ese radio.
    let notificados = 0, whatsapp = 0, error = null;
    for (const _ of [3, 6, 10].filter((r) => r <= radio)) {
      const o = await pedir("POST", `/necesidades/${n.id_necesidad}/olas`, { rol: "clinica" });
      notificados += o.donantes_notificados; whatsapp += o.whatsapp_enviados || 0; error = error || o.whatsapp_error;
    }
    await refrescarNecesidades(); return { id: n.id_necesidad, notificados, whatsapp, error };
  };
  API.lanzarOla = async (id) => { const o = await pedir("POST", `/necesidades/${id}/olas`, { rol: "clinica" }); await refrescarNecesidades(); return o; };
  API.guardarUnidades = async (id, unidades, cerrar = false) => {
    await pedir("POST", `/necesidades/${id}/resultado`, { rol: "clinica", cuerpo: { unidades_obtenidas: unidades, cerrar } });
    await refrescarNecesidades();
  };
  API.iniciarVerificacion = async () => {
    const v = await pedir("POST", "/verificacion", { rol: "donante" });
    // El SVG del QR viene en milímetros: se ajusta al recuadro.
    return { ...v, qr: (v.qr_svg || "").replace(/width="[^"]*" height="[^"]*"/, 'width="100%" height="100%"') };
  };
  API.consultarVerificacion = async () => {
    const v = await pedir("GET", "/verificacion", { rol: "donante" });
    if (v.estado_verificacion !== window.DB.donante.estado_verificacion) await refrescarDonante();
    return v;
  };
  API.revisarAlerta = (id, decision, nota) => pedir("PATCH", `/alertas/${id}/revisar`, { rol: "equipo", cuerpo: { decision, nota } });

  // Cuántos donantes elegibles hay en un radio (para la hoja «Nueva necesidad»). Guarda en memoria.
  const estimados = {};
  API.estimado = (tipo, radio, alLlegar) => {
    const k = tipo + "|" + radio;
    if (!(k in estimados)) {
      estimados[k] = null;
      pedir("GET", `/necesidades/estimado?radio_km=${radio}&tipo_sangre=${encodeURIComponent(tipo)}`, { rol: "clinica" })
        .then((r) => { estimados[k] = r.donantes_elegibles; alLlegar(); }, () => { delete estimados[k]; });
    }
    return estimados[k];
  };
})();
