/* Donaria Connect – prototipo navegable (Fase I). Sin dependencias.
   Cada pantalla es una ruta con #token para poder capturarla desde el Word. */
(() => {
  const DB = window.DB;
  const $app = document.getElementById("app");
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "set", "oct", "nov", "dic"];
  const fecha = (iso) => { const [y, m, d] = iso.slice(0, 10).split("-").map(Number); return `${d} ${MESES[m - 1]} ${y}`; };
  const addDays = (iso, n) => { const d = new Date(iso + "T12:00:00"); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };
  const HOY = "2026-10-15";

  /* ---------- Iconos (trazo de 1.8, misma familia) ---------- */
  const P = {
    drop: '<path d="M12 3c-3.4 4.6-6.3 8-6.3 11.4a6.3 6.3 0 0 0 12.6 0C18.3 11 15.4 7.6 12 3z"/>',
    clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    person: '<circle cx="12" cy="8" r="3.8"/><path d="M4.5 20c1.4-3.7 4.2-5.6 7.5-5.6s6.1 1.9 7.5 5.6"/>',
    chart: '<path d="M4 20h16M7 16v-5M12 16V6M17 16v-8"/>',
    list: '<path d="M9 6.5h11M9 12h11M9 17.5h11M4.5 6.5h.01M4.5 12h.01M4.5 17.5h.01"/>',
    shield: '<path d="M12 3.2l7 2.8v5.6c0 4.4-2.9 7.6-7 9.2-4.1-1.6-7-4.8-7-9.2V6z"/><path d="M9 12l2.2 2.2L15.5 10"/>',
    building: '<path d="M5 20.5V6l7-2.6L19 6v14.5M3.5 20.5h17M10 20.5v-4h4v4M9 9.5h.01M15 9.5h.01M9 13h.01M15 13h.01"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    alert: '<path d="M12 4.2l8.6 15H3.4z"/><path d="M12 10v4M12 16.8h.01"/>',
    pin: '<path d="M12 20.5s-6.5-5.8-6.5-10.4a6.5 6.5 0 0 1 13 0c0 4.6-6.5 10.4-6.5 10.4z"/><circle cx="12" cy="10" r="2.3"/>',
    back: '<path d="M14.5 5.5L8 12l6.5 6.5"/>',
    chev: '<path d="M9.5 5.5L16 12l-6.5 6.5"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    x: '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
    info: '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.2M12 7.8h.01"/>',
    copy: '<rect x="8.5" y="8.5" width="11" height="11" rx="2"/><path d="M15.5 8.5V6a1.5 1.5 0 0 0-1.5-1.5H6A1.5 1.5 0 0 0 4.5 6v8A1.5 1.5 0 0 0 6 15.5h2.5"/>',
    bell: '<path d="M6.5 16.5V11a5.5 5.5 0 0 1 11 0v5.5l1.5 2h-14z"/><path d="M10 20.5h4"/>',
    map: '<path d="M4 6.5l5-2 6 2 5-2v13l-5 2-6-2-5 2z"/><path d="M9 4.5v13M15 6.5v13"/>',
  };
  const ic = (n, label) => `<svg class="i" viewBox="0 0 24 24" ${label ? `role="img" aria-label="${label}"` : 'aria-hidden="true"'}>${P[n]}</svg>`;
  const dropFill = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2.5c-3.6 4.9-6.6 8.4-6.6 12a6.6 6.6 0 0 0 13.2 0c0-3.6-3-7.1-6.6-12z"/></svg>';

  /* ---------- Grupo sanguíneo (código de color ISBT 128 + letra siempre visible) ---------- */
  const grp = (t) => t.replace(/[+-]/, "");
  const rh = (t) => (t.endsWith("+") ? "+" : "−");
  const abo = (t) => `<span class="abo abo-${grp(t)}" aria-label="Grupo ${grp(t)}, Rh ${t.endsWith("+") ? "positivo" : "negativo"}">${grp(t)}<small>${rh(t)}</small></span>`;
  const aboLabel = (t) => `<div class="abo-label abo-${grp(t)}" role="img" aria-label="Tu grupo sanguíneo: ${grp(t)} Rh ${t.endsWith("+") ? "positivo" : "negativo"}">
      <span class="k">Grupo</span><span class="g">${grp(t)}</span><span class="rh">Rh ${t.endsWith("+") ? "positivo" : "negativo"}</span></div>`;

  /* ---------- Estado de la sesión del prototipo ---------- */
  const S = {
    reg: { nombres: "", dni: "", cel: "", distrito: "", tipo: "", noSabe: false, touched: {} },
    verif: 0, consent: false, sms: true,
    respuesta: null, avisos: true, canal: DB.donante.canal, confirmEliminar: false,
    nueva: { tipo: "", meta: 4, radio: 3 }, filtro: "Activas",
    alertaAbierta: null, decision: "", nota: "", cerrarConfirm: false, unidadesInput: null,
    pre: { nombre: "", contacto: "", distrito: "", tipo: "", ok: false, acepto: false, enviado: false },
  };
  let toastTimer;
  const toast = (msg) => {
    document.querySelector(".toast")?.remove();
    const t = document.createElement("div"); t.className = "toast"; t.setAttribute("role", "status"); t.textContent = msg;
    document.body.appendChild(t); clearTimeout(toastTimer); toastTimer = setTimeout(() => t.remove(), 3600);
  };
  const go = (h) => { if (location.hash === "#" + h) render(); else location.hash = h; };

  /* ======================= APP DEL DONANTE ======================= */
  const tabs = (cur) => `<nav class="tabbar" aria-label="Secciones">
      <a href="#d-hoy" ${cur === "hoy" ? 'aria-current="page"' : ""}>${ic("drop")}Hoy</a>
      <a href="#d-historial" ${cur === "hist" ? 'aria-current="page"' : ""}>${ic("clock")}Historial</a>
      <a href="#d-perfil" ${cur === "perfil" ? 'aria-current="page"' : ""}>${ic("person")}Perfil</a></nav>`;
  const phone = ({ title, sub, back, step, tab, body }) => `<div class="device-wrap"><div class="phone">
      ${step ? `<div class="progress-steps" style="padding-top:14px" aria-label="Paso ${step} de 3">${[1, 2, 3].map((i) => `<span class="${i <= step ? "on" : ""}"></span>`).join("")}</div>` : ""}
      <header class="nav">${back ? `<a class="back" href="#${back[0]}">${ic("back")}${back[1]}</a>` : ""}
        <h1>${title}</h1>${sub ? `<p class="sub">${sub}</p>` : ""}</header>
      <main class="phone-body">${body}</main>${tab ? tabs(tab) : ""}</div></div>`;

  const regErrors = () => {
    const r = S.reg, e = {};
    if (r.nombres.trim().split(/\s+/).filter(Boolean).length < 2) e.nombres = "Escribe tu nombre y al menos un apellido.";
    if (!/^\d{8}$/.test(r.dni)) e.dni = "El DNI tiene 8 dígitos.";
    if (!/^9\d{8}$/.test(r.cel.replace(/\s/g, ""))) e.cel = "Usa un celular peruano de 9 dígitos que empiece con 9.";
    if (!r.distrito) e.distrito = "Elige tu distrito.";
    if (!r.tipo && !r.noSabe) e.tipo = "Elige tu tipo de sangre o marca que no lo sabes.";
    return e;
  };
  const fieldErr = (k, e) => (S.reg.touched[k] && e[k] ? `<p class="err" id="e-${k}">${ic("alert")}${e[k]}</p>` : "");
  const vRegistro = () => {
    const r = S.reg, e = regErrors(), ok = Object.keys(e).length === 0;
    return phone({ title: "Crea tu registro", sub: "Te avisaremos solo cuando tu tipo de sangre haga falta cerca de ti.", step: 1, back: ["inicio", "Mapa"],
      body: `<form class="grid-form" style="display:grid;gap:18px" novalidate data-form="reg">
        <div class="field"><label for="f-nombres">Nombres y apellidos</label>
          <input class="input" id="f-nombres" name="nombres" autocomplete="name" value="${esc(r.nombres)}" placeholder="Lucía Paredes Rojas" ${S.reg.touched.nombres && e.nombres ? 'aria-invalid="true" aria-describedby="e-nombres"' : ""}>${fieldErr("nombres", e)}</div>
        <div class="field"><label for="f-dni">DNI</label>
          <input class="input num" id="f-dni" name="dni" inputmode="numeric" maxlength="8" autocomplete="off" value="${esc(r.dni)}" placeholder="8 dígitos" ${S.reg.touched.dni && e.dni ? 'aria-invalid="true" aria-describedby="e-dni"' : ""}>
          ${fieldErr("dni", e) || '<p class="hint">Lo usamos solo para verificar tu identidad. Se guarda cifrado.</p>'}</div>
        <div class="field"><label for="f-cel">Celular con WhatsApp</label>
          <input class="input num" id="f-cel" name="cel" type="tel" inputmode="tel" autocomplete="tel-national" value="${esc(r.cel)}" placeholder="987 654 321" ${S.reg.touched.cel && e.cel ? 'aria-invalid="true" aria-describedby="e-cel"' : ""}>${fieldErr("cel", e)}</div>
        <div class="field"><label for="f-distrito">Distrito donde vives o trabajas</label>
          <select class="select" id="f-distrito" name="distrito"><option value="">Elige un distrito</option>${DB.distritos.map((d) => `<option ${r.distrito === d ? "selected" : ""}>${d}</option>`).join("")}</select>
          ${fieldErr("distrito", e) || '<p class="hint">Sirve para calcular la distancia a cada banco de sangre. No pedimos tu dirección.</p>'}</div>
        <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="lbl" style="margin-bottom:6px">Tipo de sangre</legend>
          <div class="chips" role="radiogroup" aria-label="Tipo de sangre">${DB.tipos.map((t) => `<button type="button" class="chip-abo" role="radio" aria-checked="${r.tipo === t}" data-act="reg-tipo" data-v="${t}">${abo(t)}</button>`).join("")}</div>
          <label class="check" style="margin-top:10px"><input type="checkbox" id="f-nosabe" data-act="reg-nosabe" ${r.noSabe ? "checked" : ""}><span>No conozco mi tipo de sangre<br><span class="cap">El banco de sangre lo confirmará en tu primera donación.</span></span></label>
          ${fieldErr("tipo", e)}</fieldset>
        <button class="btn btn-primary btn-block" type="submit" ${ok ? "" : "disabled"}>Continuar</button>
        ${ok ? "" : '<p class="cap" style="text-align:center">Completa todos los campos para continuar.</p>'}
      </form>` });
  };
  const VSTEPS = ["Foto de tu DNI", "Selfie con prueba de vida", "Comparación con el DNI"];
  const vVerificacion = () => {
    const v = S.verif, done = v >= 4, running = v > 0 && !done;
    const msg = ["Toca el botón para empezar", "Coloca tu DNI dentro del recuadro", "Mira a la cámara y parpadea", "Comparando tu rostro con el DNI…", "Identidad verificada"][v];
    return phone({ title: "Verifica tu identidad", sub: "Didit compara tu DNI con tu rostro. Así nadie puede registrarse en tu nombre.", step: 2, back: ["d-registro", "Datos"],
      body: `<div class="camera" aria-hidden="true"><div class="oval ${done ? "ok" : ""}"></div><p class="cam-msg">${msg}</p></div>
      <ol class="group verif-steps" style="margin:0;padding:0" aria-live="polite">${VSTEPS.map((s, i) => {
        const st = v > i + 1 || done ? "ok" : v === i + 1 ? "run" : "todo";
        return `<li class="row"><span class="grow">${s}</span>${st === "ok" ? `<span class="pill pill-ok">Listo</span>` : st === "run" ? `<span class="pill pill-accent">En curso</span>` : `<span class="pill pill-neutral">Pendiente</span>`}</li>`; }).join("")}</ol>
      ${done ? `<button class="btn btn-primary btn-block" data-act="nav" data-to="d-consentimiento">Continuar</button>`
        : `<button class="btn btn-primary btn-block" data-act="verif" ${running ? "disabled" : ""}>${running ? "Verificando…" : "Iniciar verificación"}</button>`}
      <p class="note note-neutral">${ic("info")}<span>En el prototipo la verificación es una simulación. En la plataforma se abre el flujo seguro de Didit y no guardamos tu foto.</span></p>` });
  };
  const vConsentimiento = () => phone({ title: "Tus datos, tus reglas", sub: "Lee cómo usamos tu información antes de crear tu registro.", step: 3, back: ["d-verificacion", "Verificación"],
    body: `<div class="legal" tabindex="0" aria-label="Política de privacidad, versión 1.0">
        <h3>Qué guardamos</h3><p>Nombre, DNI cifrado, celular, distrito, tipo de sangre y fechas en que donaste.</p>
        <h3>Para qué</h3><p>Solo para avisarte cuando tu tipo de sangre haga falta cerca de ti. Donar siempre es voluntario y gratuito: nadie puede pagarte ni cobrarte.</p>
        <h3>Qué ven los bancos de sangre</h3><p>Cuántas personas respondieron a una convocatoria, nunca tu nombre ni tu DNI. Tu donación no se asigna a ningún paciente.</p>
        <h3>Tus derechos</h3><p>Puedes pausar los avisos, pedir una copia de tus datos o eliminarlos desde tu perfil, en cualquier momento.</p>
        <p class="cap">Versión 1.0 · Ley N.° 29733 y D.S. N.° 016-2024-JUS</p></div>
      <label class="check"><input type="checkbox" id="f-consent" data-act="consent" ${S.consent ? "checked" : ""}><span>Acepto que Donaria Connect use mis datos para enviarme convocatorias de donación voluntaria.</span></label>
      <label class="check"><input type="checkbox" id="f-sms" data-act="sms" ${S.sms ? "checked" : ""}><span>Si no tengo internet, avisarme también por SMS.</span></label>
      <button class="btn btn-primary btn-block" data-act="crear" ${S.consent ? "" : "disabled"}>Crear mi registro</button>` });

  const elegibleDesde = () => addDays(DB.donante.fecha_ultima_donacion, DB.donante.sexo === "F" ? 120 : 90);
  const vHoy = () => {
    const d = DB.donante, c = DB.convocatoriaDonante, inst = DB.instituciones.find((i) => i.id_institucion === c.institucion_id);
    const desde = elegibleDesde(), apto = desde <= HOY;
    const total = DB.donaciones.reduce((a, x) => a + (x.unidades_convocatoria || 0), 0);
    return phone({ title: `Hola, ${esc(d.nombres.split(" ")[0])}`, sub: "Jueves 15 de octubre", tab: "hoy",
      body: `<section class="donor-card" aria-label="Tu tarjeta de donante">${aboLabel(d.tipo_sangre)}
          <div class="meta"><span class="name">${esc(d.nombres)}</span>
          ${apto ? `<span class="pill pill-ok">Puedes donar</span>` : `<span class="pill pill-neutral">Podrás donar desde el ${fecha(desde)}</span>`}
          <span class="cap">Última donación: ${fecha(d.fecha_ultima_donacion)}<br>Identidad verificada con Didit</span></div></section>
        <section style="display:grid;gap:8px"><h2 class="group-title" style="padding:0 4px">Te necesitan cerca</h2>
          <article class="call-card"><div class="top">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">${abo(c.tipo_sangre)}<span class="cap">Recibida ${c.recibida} · ${c.distancia_km} km</span></div>
            <h2>${inst.razon_social} necesita donantes ${c.tipo_sangre}</h2>
            <p class="muted" style="font-size:var(--t-sub)">${inst.direccion}, ${inst.distrito}</p></div>
            <a class="row" href="#d-convocatoria"><span class="grow" style="font-weight:600;color:var(--accent-text)">Ver detalle y responder</span><span class="chev">${ic("chev")}</span></a></article></section>
        <section class="group" style="padding:16px"><div class="impact"><span class="big num">${total}</span>
          <p style="font-size:var(--t-sub)">unidades reunieron las convocatorias en las que participaste. <a href="#d-historial">Ver historial</a></p></div></section>` });
  };
  const vConvocatoria = () => {
    const c = DB.convocatoriaDonante, inst = DB.instituciones.find((i) => i.id_institucion === c.institucion_id), r = S.respuesta;
    const maps = "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(inst.razon_social + " " + inst.direccion + " Lima");
    return phone({ title: `Convocatoria ${c.tipo_sangre}`, sub: `${inst.razon_social} · a ${c.distancia_km} km`, back: ["d-hoy", "Hoy"], tab: "hoy",
      body: `<section class="group"><dl class="kv" style="padding:16px;margin:0">
          <dt>Dónde</dt><dd>${inst.direccion}, ${inst.distrito}</dd><dt>Horario</dt><dd>${inst.horario}</dd><dt>Tipo</dt><dd>${abo(c.tipo_sangre)}</dd><dt>Lleva</dt><dd>Tu DNI</dd></dl></section>
        <p class="note note-neutral">${ic("info")}<span>No necesitas reservar. Acércate en el horario de atención; el banco de sangre te hará una evaluación médica antes de donar.</span></p>
        <section style="display:grid;gap:8px"><h2 class="group-title" style="padding:0 4px">Antes de ir, confirma que</h2>
          <ul class="group" style="margin:0;padding:0">${["Tienes entre 18 y 60 años y pesas más de 50 kg", "Te sientes bien y comiste algo ligero", "No te hiciste un tatuaje en el último año", "No estás embarazada ni dando de lactar"].map((x) => `<li class="row">${ic("check")}<span class="grow">${x}</span></li>`).join("")}</ul></section>
        <div aria-live="polite" style="display:grid;gap:12px">
        ${r === "voy" ? `<p class="note note-ok">${ic("check")}<span><b>Gracias por responder.</b> La clínica solo ve cuántas personas respondieron, nunca tu nombre.</span></p>
            <a class="btn btn-plain btn-block" href="${maps}" target="_blank" rel="noopener">${ic("map")}Cómo llegar</a>
            <button class="btn btn-text" data-act="resp" data-v="">Cambiar mi respuesta</button>`
          : r === "no" ? `<p class="note note-neutral">${ic("info")}<span>Entendido. No te volveremos a avisar por esta convocatoria.</span></p>
            <button class="btn btn-text" data-act="resp" data-v="">Cambiar mi respuesta</button>`
          : `<button class="btn btn-primary btn-block" data-act="resp" data-v="voy">Voy a ir</button>
            <button class="btn btn-plain btn-block" data-act="resp" data-v="no">Esta vez no puedo</button>`}</div>` });
  };
  const vHistorial = () => {
    const d = DB.donante, desde = elegibleDesde();
    return phone({ title: "Historial", sub: `${DB.donaciones.length} donaciones registradas`, tab: "hist",
      body: `<p class="note ${desde <= HOY ? "note-ok" : "note-neutral"}">${ic(desde <= HOY ? "check" : "clock")}<span>${desde <= HOY ? "Ya puedes volver a donar." : `Podrás volver a donar desde el ${fecha(desde)}.`} Entre donaciones de sangre total deben pasar ${d.sexo === "F" ? "4 meses en mujeres" : "3 meses en hombres"}.</span></p>
        <ul class="group timeline" style="margin:0;padding:0">${DB.donaciones.map((x) => `<li class="row"><span class="dot ${x.unidades_convocatoria ? "" : "gray"}"></span>
          <span class="grow"><b>${fecha(x.fecha)}</b><br><span style="font-size:var(--t-sub)">${x.institucion}</span><br><span class="cap">${x.unidades_convocatoria ? `${x.tipo}: la convocatoria reunió ${x.unidades_convocatoria} unidades` : x.tipo}</span></span></li>`).join("")}</ul>
        <p class="cap" style="padding:0 4px">Las cifras son agregadas por convocatoria. Ninguna donación se asigna a un paciente.</p>` });
  };
  const vPerfil = () => {
    const d = DB.donante, c = DB.consentimiento;
    return phone({ title: "Perfil", tab: "perfil",
      body: `<section style="display:grid;gap:6px"><h2 class="group-title">Tus datos</h2><div class="group">
          <div class="row"><span class="grow">Nombre</span><span class="v">${esc(d.nombres)}</span></div>
          <div class="row"><span class="grow">DNI</span><span class="v num">${d.dni_mask}</span></div>
          <div class="row"><span class="grow">Celular</span><span class="v num">${d.telefono_whatsapp}</span></div>
          <div class="row"><span class="grow">Distrito</span><span class="v">${d.distrito}</span></div>
          <div class="row"><span class="grow">Tipo de sangre</span>${abo(d.tipo_sangre)}</div></div></section>
        <section style="display:grid;gap:6px"><h2 class="group-title">Avisos</h2><div class="group">
          <label class="row" for="f-avisos"><span class="grow">Recibir convocatorias</span><input type="checkbox" role="switch" id="f-avisos" data-act="avisos" ${S.avisos ? "checked" : ""} style="width:22px;height:22px;accent-color:var(--accent)"></label>
          <div class="row"><span class="grow">Canal</span><div class="seg" role="group" aria-label="Canal de aviso">${["WhatsApp", "SMS"].map((k) => `<button type="button" aria-pressed="${S.canal === k}" data-act="canal" data-v="${k}">${k}</button>`).join("")}</div></div></div>
          ${S.avisos ? "" : '<p class="cap" style="padding:0 4px">Avisos en pausa. No recibirás convocatorias hasta que los vuelvas a activar.</p>'}</section>
        <section style="display:grid;gap:6px"><h2 class="group-title">Privacidad</h2><div class="group">
          <div class="row"><span class="grow">Consentimiento</span><span class="v">Versión ${c.version_texto} · ${fecha(c.fecha_hora)}</span></div>
          <button class="row" data-act="copia"><span class="grow">Pedir una copia de mis datos</span><span class="chev">${ic("chev")}</span></button>
          <button class="row" data-act="eliminar" style="color:var(--signal-text)"><span class="grow">Retirar consentimiento y eliminar mis datos</span></button></div>
          ${S.confirmEliminar ? `<div class="note note-signal" role="alert" style="display:grid;gap:10px"><span>Se borrarán tu registro y tu historial. No podrás deshacerlo.</span>
            <div class="btn-row"><button class="btn btn-plain" data-act="eliminar-no">Cancelar</button><button class="btn btn-primary" data-act="eliminar-si">Eliminar mis datos</button></div></div>` : ""}</section>` });
  };

  /* ======================= PANEL INSTITUCIONAL ======================= */
  const inst = DB.instituciones[0];
  const pendientes = () => DB.alertas.filter((a) => a.estado === "Pendiente").length;
  const NAV = [
    { sec: inst.razon_social, items: [["p-resumen", "Resumen", "chart"], ["p-necesidades", "Necesidades", "list"], ["p-reportes", "Reportes", "drop"]] },
    { sec: "Equipo Donaria", items: [["a-alertas", "Alertas antifraude", "shield"], ["a-instituciones", "Instituciones", "building"]] },
  ];
  const panel = (cur, body, extra = "") => `<div class="panel">
      <aside class="side"><div class="brand"><span class="brand-mark">${dropFill}</span>Donaria Connect</div>
        <nav aria-label="Panel">${NAV.map((g) => `<p class="sec">${g.sec}</p>${g.items.map(([h, l, i]) => `<a href="#${h}" ${cur === h ? 'aria-current="page"' : ""}>${ic(i)}${l}${h === "a-alertas" && pendientes() ? `<span class="count" aria-label="${pendientes()} pendientes">${pendientes()}</span>` : ""}</a>`).join("")}`).join("")}</nav>
        <div class="who"><b>${DB.usuario.nombre}</b><span class="cap">${DB.usuario.rol}</span><a href="#inicio" class="cap">Mapa de pantallas</a></div></aside>
      <div class="panel-top"><div class="brand" style="padding:0"><span class="brand-mark">${dropFill}</span>Donaria Connect</div>
        <nav aria-label="Panel">${NAV.flatMap((g) => g.items).map(([h, l]) => `<a href="#${h}" ${cur === h ? 'aria-current="page"' : ""}>${l}</a>`).join("")}</nav></div>
      <main class="main">${body}</main></div>${extra}`;
  const tot = (n) => n.olas.reduce((a, o) => ({ not: a.not + o.donantes_notificados, resp: a.resp + o.respondieron }), { not: 0, resp: 0 });
  const pct = (a, b) => (b ? ((100 * a) / b).toFixed(1) + " %" : "—");
  const meter = (n) => `<div style="display:grid;gap:4px;min-width:110px"><div class="meter ${n.unidades_obtenidas >= n.unidades_meta ? "done" : ""}" role="img" aria-label="${n.unidades_obtenidas} de ${n.unidades_meta} unidades"><i style="width:${Math.min(100, (100 * n.unidades_obtenidas) / n.unidades_meta)}%"></i></div><span class="cap num">${n.unidades_obtenidas} de ${n.unidades_meta} unidades</span></div>`;
  const estadoPill = (e) => `<span class="pill ${e === "Activa" ? "pill-accent" : "pill-neutral"}">${e}</span>`;

  const vResumen = (sheet = "") => {
    const act = DB.necesidades.filter((n) => n.estado === "Activa");
    const unidades = DB.necesidades.reduce((a, n) => a + n.unidades_obtenidas, 0);
    const t = DB.necesidades.reduce((a, n) => { const x = tot(n); return { not: a.not + x.not, resp: a.resp + x.resp }; }, { not: 0, resp: 0 });
    const semanas = [["24 ago", 6], ["31 ago", 9], ["7 set", 7], ["14 set", 12], ["21 set", 10], ["28 set", 14], ["5 oct", 16], ["12 oct", 11]];
    const max = 16;
    return panel("p-resumen", `<div class="head"><div><h1>Resumen</h1><p class="sub">${inst.razon_social} · octubre de 2026</p></div>
        <a class="btn btn-primary" href="#p-nueva">${ic("plus")}Nueva necesidad</a></div>
      <section class="kpis" aria-label="Indicadores del mes">
        <div class="kpi"><span class="l">Unidades conseguidas</span><span class="v">${unidades}</span><span class="d">Octubre, por convocatorias</span></div>
        <div class="kpi"><span class="l">Conversión</span><span class="v">${pct(t.resp, t.not)}</span><span class="d">Respondieron / notificados · meta ≥ 6 %</span></div>
        <div class="kpi"><span class="l">Convocatorias activas</span><span class="v">${act.length}</span><span class="d">${act.map((n) => n.tipo_sangre).join(" y ")}</span></div>
        <div class="kpi"><span class="l">Donantes verificados</span><span class="v">412</span><span class="d">A menos de 6 km de la clínica</span></div></section>
      <div class="grid-2">
        <section class="card"><div class="head" style="align-items:center"><h2>Convocatorias activas</h2><a class="crumb" href="#p-necesidades" style="margin:0">Ver todas</a></div>
          <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Tipo</th><th>Avance</th><th>Olas</th><th class="r">Respondieron</th></tr></thead><tbody>
          ${act.map((n) => `<tr class="link" data-act="nav" data-to="p-conv-${n.id_necesidad}" tabindex="0"><td>${abo(n.tipo_sangre)}</td><td>${meter(n)}</td><td class="num">${n.olas.length}</td><td class="r num">${tot(n).resp} de ${tot(n).not}</td></tr>`).join("")}
          </tbody></table></div></section>
        <section class="card"><h2>Unidades por semana</h2>
          <div class="bars" role="img" aria-label="Unidades por semana, de 6 a 16; semana actual 11 hasta hoy">${semanas.map(([s, v], i) => `<div class="b ${i < 7 ? "past" : ""}"><span>${v}</span><i style="height:${(v / max) * 110}px"></i></div>`).join("")}</div>
          <div class="bars-x">${semanas.map(([s]) => `<span>${s}</span>`).join("")}</div>
          <p class="cap">Semana actual en granate. Incluye solo unidades confirmadas por el banco de sangre.</p></section></div>
      <p class="note note-neutral">${ic("info")}<span>Este panel nunca muestra nombres de donantes ni datos de pacientes. Las convocatorias son por tipo de sangre y zona.</span></p>`, sheet);
  };

  const ESTIM = { "O+": 96, "O-": 38, "A+": 52, "A-": 14, "B+": 19, "B-": 6, "AB+": 9, "AB-": 3 };
  const estimado = () => Math.round((ESTIM[S.nueva.tipo] || 0) * (S.nueva.radio === 3 ? 1 : S.nueva.radio === 6 ? 1.9 : 3.1));
  const vNueva = () => {
    const n = S.nueva;
    const sheet = `<div class="sheet-backdrop" data-act="cerrar-sheet" data-self="1"><div class="sheet" role="dialog" aria-modal="true" aria-labelledby="t-nueva">
      <header><h2 id="t-nueva">Nueva necesidad</h2><button class="btn btn-text" data-act="cerrar-sheet">Cancelar</button></header>
      <div class="body">
        <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="lbl" style="margin-bottom:6px">Tipo de sangre que necesitas</legend>
          <div class="chips" role="radiogroup" aria-label="Tipo de sangre">${DB.tipos.map((t) => `<button type="button" class="chip-abo" role="radio" aria-checked="${n.tipo === t}" data-act="n-tipo" data-v="${t}">${abo(t)}</button>`).join("")}</div></fieldset>
        <div class="field"><span class="lbl" id="l-meta">Unidades que buscas</span>
          <div class="stepper" role="group" aria-labelledby="l-meta"><button type="button" data-act="n-meta" data-v="-1" aria-label="Quitar una unidad">−</button><output aria-live="polite">${n.meta}</output><button type="button" data-act="n-meta" data-v="1" aria-label="Agregar una unidad">+</button></div></div>
        <div class="field"><span class="lbl" id="l-radio">Radio de la primera ola</span>
          <div class="seg" role="group" aria-labelledby="l-radio">${[3, 6, 10].map((r) => `<button type="button" aria-pressed="${n.radio === r}" data-act="n-radio" data-v="${r}">${r} km</button>`).join("")}</div>
          <p class="hint">Si la respuesta no alcanza, puedes lanzar una nueva ola con un radio mayor.</p></div>
        <p class="note note-signal">${ic("alert")}<span>No escribas el nombre ni datos del paciente. Donaria Connect convoca por tipo de sangre y zona, nunca por paciente.</span></p>
        ${n.tipo ? `<p class="note note-neutral">${ic("bell")}<span>Se avisará a unos <b class="num">${estimado()}</b> donantes ${n.tipo} verificados y aptos a menos de ${n.radio} km.</span></p>` : ""}
      </div>
      <footer><button class="btn btn-plain" data-act="cerrar-sheet">Cancelar</button><button class="btn btn-primary" data-act="lanzar" ${n.tipo ? "" : "disabled"}>Lanzar convocatoria</button></footer></div></div>`;
    return vResumen(sheet);
  };

  const ringSVG = (n) => {
    const R = [3, 6, 10], done = n.olas.map((o) => o.radio_km);
    const col = { 3: "var(--ring-1)", 6: "var(--ring-2)", 10: "var(--ring-3)" };
    return `<svg viewBox="0 0 260 260" role="img" aria-label="Olas lanzadas: ${n.olas.map((o) => o.radio_km + " km").join(", ")}">
      ${R.slice().reverse().map((r) => { const rr = 20 + (r / 10) * 100; const on = done.includes(r);
        return `<circle cx="130" cy="130" r="${rr}" fill="${on ? col[r] : "none"}" fill-opacity="${on ? 0.16 : 0}" stroke="${on ? col[r] : "var(--separator)"}" stroke-width="${on ? 2 : 1.2}" ${on ? "" : 'stroke-dasharray="4 4"'}/>
          <text x="130" y="${130 - rr + 14}" text-anchor="middle">${r} km</text>`; }).join("")}
      <circle cx="130" cy="130" r="9" fill="var(--accent)"/><text x="130" y="158" text-anchor="middle" style="fill:var(--label);font-weight:600">Clínica</text></svg>`;
  };
  const vConv = (id) => {
    const n = DB.necesidades.find((x) => x.id_necesidad === id);
    if (!n) return vNecesidades();
    const t = tot(n), next = [3, 6, 10].find((r) => !n.olas.some((o) => o.radio_km === r));
    if (S.unidadesInput === null) S.unidadesInput = n.unidades_obtenidas;
    return panel("p-necesidades", `<div class="head"><div><a class="crumb" href="#p-necesidades">${ic("back")}Necesidades</a>
        <h1 style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">Convocatoria ${abo(n.tipo_sangre)} ${estadoPill(n.estado)}</h1>
        <p class="sub">N.° ${n.id_necesidad} · creada ${fecha(n.fecha_creacion)}, ${n.fecha_creacion.slice(11)} · ${n.zona}</p></div>
        ${n.estado === "Activa" && next ? `<button class="btn btn-primary" data-act="ola" data-id="${n.id_necesidad}">${ic("bell")}Lanzar ola ${n.olas.length + 1} · ${next} km</button>` : ""}</div>
      <section class="kpis"><div class="kpi"><span class="l">Unidades</span><span class="v num">${n.unidades_obtenidas}/${n.unidades_meta}</span></div>
        <div class="kpi"><span class="l">Notificados</span><span class="v num">${t.not}</span></div>
        <div class="kpi"><span class="l">Respondieron</span><span class="v num">${t.resp}</span></div>
        <div class="kpi"><span class="l">Conversión</span><span class="v">${pct(t.resp, t.not)}</span></div></section>
      <section class="card"><h2>Olas de convocatoria</h2><div class="waves">${ringSVG(n)}
        <div class="tbl-wrap"><table class="tbl"><thead><tr><th>Ola</th><th>Radio</th><th>Enviada</th><th class="r">Notificados</th><th class="r">Respondieron</th><th class="r">Conversión</th></tr></thead><tbody>
        ${n.olas.map((o) => `<tr><td>${o.numero_ola}</td><td class="num">${o.radio_km} km</td><td class="num">${o.fecha_envio}</td><td class="r num">${o.donantes_notificados}</td><td class="r num">${o.respondieron}</td><td class="r num">${pct(o.respondieron, o.donantes_notificados)}</td></tr>`).join("")}
        </tbody></table><p class="cap" style="margin-top:10px">Las personas notificadas acuden directo, sin reserva. Aquí solo ves cifras agregadas.</p></div></div></section>
      ${n.estado === "Activa" ? `<div class="grid-2"><section class="card"><h2>Registrar unidades obtenidas</h2>
          <p class="muted" style="font-size:var(--t-sub)">Ingresa el total de unidades extraídas a donantes que llegaron por esta convocatoria, después del tamizaje.</p>
          <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap"><div class="stepper" role="group" aria-label="Unidades obtenidas"><button type="button" data-act="u" data-v="-1" aria-label="Restar">−</button><output aria-live="polite">${S.unidadesInput}</output><button type="button" data-act="u" data-v="1" aria-label="Sumar">+</button></div>
          <button class="btn btn-primary" data-act="guardar-u" data-id="${n.id_necesidad}" ${S.unidadesInput === n.unidades_obtenidas ? "disabled" : ""}>Guardar unidades</button></div></section>
        <section class="card"><h2>Cerrar convocatoria</h2><p class="muted" style="font-size:var(--t-sub)">Al cerrar, dejamos de avisar y los donantes que respondieron reciben un agradecimiento.</p>
          ${S.cerrarConfirm ? `<div class="note note-signal" role="alert" style="display:grid;gap:10px"><span>¿Cerrar con ${n.unidades_obtenidas} de ${n.unidades_meta} unidades?</span><div class="btn-row"><button class="btn btn-plain" data-act="cerrar-no">Cancelar</button><button class="btn btn-primary" data-act="cerrar-si" data-id="${n.id_necesidad}">Cerrar convocatoria</button></div></div>`
            : `<div><button class="btn btn-plain" data-act="cerrar">Cerrar convocatoria</button></div>`}</section></div>`
        : `<p class="note note-ok">${ic("check")}<span>Convocatoria cerrada con ${n.unidades_obtenidas} de ${n.unidades_meta} unidades.</span></p>`}`);
  };
  const vNecesidades = () => {
    const list = DB.necesidades.filter((n) => S.filtro === "Todas" || n.estado === (S.filtro === "Activas" ? "Activa" : "Cerrada"));
    return panel("p-necesidades", `<div class="head"><div><h1>Necesidades</h1><p class="sub">Cada necesidad genera una convocatoria por olas.</p></div>
        <a class="btn btn-primary" href="#p-nueva">${ic("plus")}Nueva necesidad</a></div>
      <div class="seg" role="group" aria-label="Filtrar">${["Activas", "Cerradas", "Todas"].map((f) => `<button type="button" aria-pressed="${S.filtro === f}" data-act="filtro" data-v="${f}">${f}</button>`).join("")}</div>
      <section class="card" style="padding:6px 6px"><div class="tbl-wrap"><table class="tbl"><thead><tr><th>N.°</th><th>Tipo</th><th>Creada</th><th>Avance</th><th class="r">Olas</th><th class="r">Conversión</th><th>Estado</th><th></th></tr></thead><tbody>
      ${list.length ? list.map((n) => `<tr class="link" data-act="nav" data-to="p-conv-${n.id_necesidad}" tabindex="0"><td class="num">${n.id_necesidad}</td><td>${abo(n.tipo_sangre)}</td><td class="num">${fecha(n.fecha_creacion)}</td><td>${meter(n)}</td><td class="r num">${n.olas.length}</td><td class="r num">${pct(tot(n).resp, tot(n).not)}</td><td>${estadoPill(n.estado)}</td><td class="chev">${ic("chev")}</td></tr>`).join("")
        : `<tr><td colspan="8" style="text-align:center;padding:32px" class="muted">No hay necesidades ${S.filtro.toLowerCase()}. <a href="#p-nueva">Crea una nueva</a>.</td></tr>`}
      </tbody></table></div></section>`);
  };
  const vReportes = () => {
    const rows = DB.necesidades.slice().reverse();
    const T = rows.reduce((a, n) => { const t = tot(n); return { meta: a.meta + n.unidades_meta, ob: a.ob + n.unidades_obtenidas, olas: a.olas + n.olas.length, not: a.not + t.not, resp: a.resp + t.resp }; }, { meta: 0, ob: 0, olas: 0, not: 0, resp: 0 });
    return panel("p-reportes", `<div class="head"><div><h1>Reportes</h1><p class="sub">Resultados agregados por convocatoria · octubre de 2026</p></div>
        <button class="btn btn-plain" data-act="copiar">${ic("copy")}Copiar tabla</button></div>
      <section class="card" style="padding:6px"><div class="tbl-wrap"><table class="tbl" id="tbl-reporte"><thead><tr><th>Fecha</th><th>Tipo</th><th class="r">Meta</th><th class="r">Obtenidas</th><th class="r">Olas</th><th class="r">Notificados</th><th class="r">Respondieron</th><th class="r">Conversión</th></tr></thead><tbody>
      ${rows.map((n) => { const t = tot(n); return `<tr><td class="num">${fecha(n.fecha_creacion)}</td><td>${abo(n.tipo_sangre)}</td><td class="r num">${n.unidades_meta}</td><td class="r num">${n.unidades_obtenidas}</td><td class="r num">${n.olas.length}</td><td class="r num">${t.not}</td><td class="r num">${t.resp}</td><td class="r num">${pct(t.resp, t.not)}</td></tr>`; }).join("")}
      <tr style="font-weight:700"><td>Total</td><td></td><td class="r num">${T.meta}</td><td class="r num">${T.ob}</td><td class="r num">${T.olas}</td><td class="r num">${T.not}</td><td class="r num">${T.resp}</td><td class="r num">${pct(T.resp, T.not)}</td></tr>
      </tbody></table></div></section>
      <p class="note note-neutral">${ic("info")}<span>Sin nombres ni DNI. La tarifa de la institución es fija y no depende de estas cifras (art. 9 de la Ley N.° 26454).</span></p>`);
  };
  const slaPill = (a) => a.estado !== "Pendiente" ? `<span class="pill pill-ok">Revisada</span>`
    : a.horas_restantes < 24 ? `<span class="pill pill-signal">Vence en ${a.horas_restantes} h</span>` : `<span class="pill pill-neutral">Quedan ${a.horas_restantes} h</span>`;
  const vAlertas = () => {
    const pend = DB.alertas.filter((a) => a.estado === "Pendiente"), urg = pend.filter((a) => a.horas_restantes < 24);
    const a = DB.alertas.find((x) => x.id_alerta === S.alertaAbierta);
    const sheet = a ? `<div class="sheet-backdrop" data-act="cerrar-alerta" data-self="1"><div class="sheet" role="dialog" aria-modal="true" aria-labelledby="t-al">
        <header><h2 id="t-al">Alerta ${a.id_alerta} · ${a.donante}</h2><button class="btn btn-text" data-act="cerrar-alerta">Cancelar</button></header>
        <div class="body"><dl class="kv"><dt>Regla</dt><dd>${a.regla}</dd><dt>Donante</dt><dd class="num">${a.donante} · DNI ${a.dni_mask}</dd><dt>Institución</dt><dd>${a.institucion}</dd><dt>Recibida</dt><dd class="num">${fecha(a.fecha)}, ${a.fecha.slice(11)}</dd><dt>Plazo</dt><dd>${slaPill(a)}</dd></dl>
          <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="lbl" style="margin-bottom:8px">Decisión</legend>
          ${[["falsa", "Falsa alarma: cerrar la alerta"], ["pausar", "Pausar avisos a este donante mientras se aclara"], ["escalar", "Pedir a la institución que verifique sus registros"]].map(([v, l]) => `<label class="check" style="padding:6px 0"><input type="radio" name="dec" data-act="dec" value="${v}" ${S.decision === v ? "checked" : ""} style="width:22px;height:22px;accent-color:var(--accent)"><span>${l}</span></label>`).join("")}</fieldset>
          <div class="field"><label for="f-nota">Nota interna</label><textarea class="input" id="f-nota" rows="3" data-act="nota" placeholder="Qué revisaste y por qué decidiste así">${esc(S.nota)}</textarea></div></div>
        <footer><button class="btn btn-plain" data-act="cerrar-alerta">Cancelar</button><button class="btn btn-primary" data-act="guardar-alerta" ${S.decision ? "" : "disabled"}>Guardar revisión</button></footer></div></div>` : "";
    return panel("a-alertas", `<div class="head"><div><h1>Alertas antifraude</h1><p class="sub">Equipo Donaria · cada alerta se revisa en menos de 72 horas</p></div></div>
      <section class="kpis"><div class="kpi"><span class="l">Pendientes</span><span class="v">${pend.length}</span></div>
        <div class="kpi"><span class="l">Vencen en menos de 24 h</span><span class="v" style="color:${urg.length ? "var(--signal-text)" : "inherit"}">${urg.length}</span></div>
        <div class="kpi"><span class="l">Revisadas este mes</span><span class="v">${DB.alertas.length - pend.length + 11}</span></div>
        <div class="kpi"><span class="l">Revisadas a tiempo</span><span class="v">100 %</span><span class="d">Meta del criterio de aceptación</span></div></section>
      <section class="card" style="padding:6px"><div class="tbl-wrap"><table class="tbl"><thead><tr><th>Alerta</th><th>Donante</th><th>Regla que se activó</th><th>Institución</th><th>Plazo</th><th></th></tr></thead><tbody>
      ${DB.alertas.map((x) => `<tr><td class="num">${x.id_alerta}<br><span class="cap">${fecha(x.fecha)}</span></td><td class="num">${x.donante}<br><span class="cap">DNI ${x.dni_mask}</span></td><td style="min-width:240px">${x.regla}</td><td>${x.institucion}</td><td>${slaPill(x)}</td>
        <td>${x.estado === "Pendiente" ? `<button class="btn btn-plain" data-act="abrir-alerta" data-id="${x.id_alerta}">Revisar</button>` : `<span class="cap">${x.decision || "Falsa alarma"}</span>`}</td></tr>`).join("")}
      </tbody></table></div></section>`, sheet);
  };
  const vInstituciones = () => panel("a-instituciones", `<div class="head"><div><h1>Instituciones</h1><p class="sub">Red de bancos de sangre afiliados · Lima Metropolitana y Callao</p></div></div>
    <section class="card" style="padding:6px"><div class="tbl-wrap"><table class="tbl"><thead><tr><th>Institución</th><th>Distrito</th><th>Autorización sanitaria</th><th>Afiliación</th><th>Licencia</th></tr></thead><tbody>
    ${DB.instituciones.map((i) => `<tr><td><b>${i.razon_social}</b><br><span class="cap">${i.direccion}</span></td><td>${i.distrito}</td><td><span class="pill pill-ok">${i.autorizacion_sanitaria}</span></td><td><span class="pill ${i.estado_afiliacion === "Piloto" ? "pill-accent" : "pill-neutral"}">${i.estado_afiliacion}</span></td><td class="num">${i.estado_afiliacion === "Piloto" ? "S/ 1,500 al mes, fija" : "—"}</td></tr>`).join("")}
    </tbody></table></div></section>
    <p class="note note-neutral">${ic("info")}<span>Antes de afiliar una institución verificamos su autorización sanitaria vigente. La tarifa es fija y nunca se calcula por unidad obtenida.</span></p>`);

  /* ======================= PRE-REGISTRO Y MAPA ======================= */
  const vPre = () => {
    const p = S.pre, valid = p.nombre.trim().length > 2 && /^(9\d{8}|[^@\s]+@[^@\s]+\.[^@\s]+)$/.test(p.contacto.replace(/\s/g, "")) && p.distrito && p.acepto;
    return `<div class="landing">
      <header style="display:flex;justify-content:space-between;align-items:center;gap:12px"><div class="brand" style="padding:0"><span class="brand-mark">${dropFill}</span>Donaria Connect</div><a class="cap" href="#inicio">Mapa de pantallas</a></header>
      <section class="landing-hero"><div><h1>Tu tipo de sangre puede ser el que hoy falta en Miraflores.</h1>
        <p class="lead">Regístrate una vez. Te avisaremos solo cuando un banco de sangre cercano necesite tu tipo, y tú decides si vas. Donar es voluntario y nunca tiene pago.</p>
        <div class="label-stack" style="margin-top:24px" aria-hidden="true">${["O+", "A+", "B+", "AB+"].map(aboLabel).join("")}</div></div>
        <form class="card" style="padding:22px;box-shadow:var(--shadow)" novalidate data-form="pre" aria-labelledby="t-pre">
          ${p.enviado ? `<div style="display:grid;gap:12px;text-align:center;padding:24px 0"><span style="color:var(--ok-text);justify-self:center">${ic("check")}</span><h2 id="t-pre" style="font-size:var(--t-title)">Listo, ${esc(p.nombre.split(" ")[0])}</h2><p class="muted">Te escribiremos cuando empiece el piloto en 2027. Puedes darte de baja respondiendo "BAJA".</p></div>`
          : `<h2 id="t-pre" style="font-size:var(--t-title)">Avísame cuando empiece</h2>
          <div class="field"><label for="p-nombre">Nombre</label><input class="input" id="p-nombre" data-pre="nombre" autocomplete="given-name" value="${esc(p.nombre)}" placeholder="Tu nombre"></div>
          <div class="field"><label for="p-contacto">Celular o correo</label><input class="input" id="p-contacto" data-pre="contacto" autocomplete="email" value="${esc(p.contacto)}" placeholder="987 654 321 o nombre@correo.com"></div>
          <div class="field"><label for="p-distrito">Distrito</label><select class="select" id="p-distrito" data-pre="distrito"><option value="">Elige un distrito</option>${DB.distritos.map((d) => `<option ${p.distrito === d ? "selected" : ""}>${d}</option>`).join("")}</select></div>
          <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="lbl" style="margin-bottom:6px">Tipo de sangre (opcional)</legend>
            <div class="chips" role="radiogroup" aria-label="Tipo de sangre">${DB.tipos.map((t) => `<button type="button" class="chip-abo" role="radio" aria-checked="${p.tipo === t}" data-act="pre-tipo" data-v="${t}">${abo(t)}</button>`).join("")}</div></fieldset>
          <label class="check"><input type="checkbox" id="p-acepto" data-act="pre-acepto" ${p.acepto ? "checked" : ""}><span style="font-size:var(--t-sub)">Acepto que me contacten solo para avisarme del inicio del piloto.</span></label>
          <button class="btn btn-primary btn-block" type="submit" ${valid ? "" : "disabled"}>Avísame</button>`}
        </form></section>
      <section class="facts">
        <div class="card"><span class="v">1.36 %</span><p>de la población dona sangre de forma voluntaria en el Perú.</p></div>
        <div class="card"><span class="v num">420 mil</span><p>unidades se recolectan al año, de las 680 mil que se necesitan.</p></div>
        <div class="card"><span class="v">S/ 0</span><p>es lo que cuesta donar. Si alguien cobra por "conseguir donantes", es ilegal.</p></div></section>
      <section style="display:grid;gap:14px"><h2 style="font-size:var(--t-title)">Cómo funciona</h2><div class="how">
        <div class="card"><span class="n">Paso 1</span><h3 style="font-size:var(--t-head)">Te registras y verificas tu identidad</h3><p class="muted" style="font-size:var(--t-sub)">Con tu DNI y una selfie, en unos minutos.</p></div>
        <div class="card"><span class="n">Paso 2</span><h3 style="font-size:var(--t-head)">Te avisamos si eres compatible y estás cerca</h3><p class="muted" style="font-size:var(--t-sub)">Por WhatsApp o SMS, y nunca antes de que puedas volver a donar.</p></div>
        <div class="card"><span class="n">Paso 3</span><h3 style="font-size:var(--t-head)">Donas directo en el banco de sangre</h3><p class="muted" style="font-size:var(--t-sub)">Sin reservas ni intermediarios. Ellos hacen la evaluación médica.</p></div></div></section>
      <footer class="cap">Proyecto académico · Universidad de Piura · Dirección de Proyectos 2026-II. Datos de referencia: prefactibilidad del equipo (2026).</footer></div>`;
  };
  const SCREENS = [
    { t: "App del donante", d: "Web responsiva en el celular", l: [["d-registro", "Registro · paso 1: datos"], ["d-verificacion", "Registro · paso 2: verificación Didit"], ["d-consentimiento", "Registro · paso 3: consentimiento"], ["d-hoy", "Hoy"], ["d-convocatoria", "Detalle de convocatoria"], ["d-historial", "Historial"], ["d-perfil", "Perfil y privacidad"]] },
    { t: "Panel institucional", d: "Banco de sangre afiliado, en escritorio", l: [["p-resumen", "Resumen"], ["p-nueva", "Nueva necesidad"], ["p-conv-31", "Convocatoria y olas"], ["p-necesidades", "Necesidades"], ["p-reportes", "Reportes agregados"]] },
    { t: "Equipo Donaria", d: "Administración interna", l: [["a-alertas", "Alertas antifraude"], ["a-instituciones", "Instituciones afiliadas"]] },
    { t: "Público", d: "Campaña de pre-registro", l: [["preregistro", "Página de pre-registro"]] },
  ];
  const vHub = () => `<div class="hub"><header class="hub-head"><h1><span class="brand-mark" style="width:40px;height:40px;border-radius:11px">${dropFill}</span>Donaria Connect</h1>
      <p class="muted">Prototipo navegable de la Fase I. Convoca donantes voluntarios por tipo de sangre y zona, nunca por paciente. Todos los datos son ficticios.</p>
      <div class="legend"><span>${abo("O+")} ${abo("A+")} ${abo("B+")} ${abo("AB+")} Código de color ISBT 128</span><span class="pill pill-accent">Acción principal</span><span class="pill pill-ok">Confirmado o apto</span><span class="pill pill-signal">Requiere atención</span></div></header>
    <div class="hub-grid">${SCREENS.map((g) => `<section class="group"><div class="gh"><h2>${g.t}</h2><p class="cap">${g.d}</p></div>
      ${g.l.map(([h, l]) => `<a class="row" href="#${h}"><span class="grow">${l}<span class="cap num">#${h}</span></span><span class="chev">${ic("chev")}</span></a>`).join("")}</section>`).join("")}</div></div>`;

  /* ======================= ROUTER ======================= */
  const VIEWS = { inicio: vHub, "d-registro": vRegistro, "d-verificacion": vVerificacion, "d-consentimiento": vConsentimiento, "d-hoy": vHoy, "d-convocatoria": vConvocatoria,
    "d-historial": vHistorial, "d-perfil": vPerfil, "p-resumen": () => vResumen(), "p-nueva": vNueva, "p-necesidades": vNecesidades, "p-reportes": vReportes,
    "a-alertas": vAlertas, "a-instituciones": vInstituciones, preregistro: vPre };
  const TITLES = { inicio: "Mapa de pantallas", "d-registro": "Registro", "d-verificacion": "Verificación", "d-consentimiento": "Consentimiento", "d-hoy": "Hoy", "d-convocatoria": "Convocatoria",
    "d-historial": "Historial", "d-perfil": "Perfil", "p-resumen": "Resumen", "p-nueva": "Nueva necesidad", "p-necesidades": "Necesidades", "p-reportes": "Reportes", "a-alertas": "Alertas antifraude", "a-instituciones": "Instituciones", preregistro: "Pre-registro" };
  let last = "";
  function render() {
    const h = location.hash.slice(1) || "inicio";
    const m = h.match(/^p-conv-(\d+)$/);
    if (h !== last && !m) { S.cerrarConfirm = false; S.unidadesInput = null; }
    if (m && last !== h) { S.cerrarConfirm = false; S.unidadesInput = null; }
    const focusId = document.activeElement?.id, sel = [document.activeElement?.selectionStart, document.activeElement?.selectionEnd];
    $app.innerHTML = m ? vConv(Number(m[1])) : (VIEWS[h] || vHub)();
    document.title = "Donaria Connect · " + (m ? "Convocatoria" : TITLES[h] || "Mapa");
    if (focusId && h === last) { const el = document.getElementById(focusId); if (el) { el.focus(); try { el.setSelectionRange(sel[0], sel[1]); } catch (e) {} } }
    if (h !== last) window.scrollTo(0, 0);
    last = h;
  }

  /* ======================= EVENTOS ======================= */
  document.addEventListener("input", (e) => {
    const t = e.target;
    if (t.closest('[data-form="reg"]') && t.name) { S.reg[t.name] = t.name === "dni" ? t.value.replace(/\D/g, "").slice(0, 8) : t.value; if (t.name !== "nombres") S.reg.touched[t.name] = true; render(); }
    if (t.dataset.pre) { S.pre[t.dataset.pre] = t.value; render(); }
    if (t.dataset.act === "nota") S.nota = t.value;
  });
  document.addEventListener("focusout", (e) => { const t = e.target; if (t.closest?.('[data-form="reg"]') && t.name && !S.reg.touched[t.name]) { S.reg.touched[t.name] = true; setTimeout(render, 0); } });
  document.addEventListener("submit", (e) => {
    e.preventDefault();
    if (e.target.dataset.form === "reg") { Object.keys(S.reg).forEach((k) => (S.reg.touched[k] = true)); if (!Object.keys(regErrors()).length) go("d-verificacion"); else render(); }
    if (e.target.dataset.form === "pre") { S.pre.enviado = true; render(); }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { if (location.hash === "#p-nueva") go("p-resumen"); if (S.alertaAbierta) { S.alertaAbierta = null; render(); } }
    if ((e.key === "Enter" || e.key === " ") && e.target.matches("tr[data-act]")) { e.preventDefault(); e.target.click(); }
  });
  document.addEventListener("click", (e) => {
    const el = e.target.closest("[data-act]"); if (!el) return;
    if (el.dataset.self && e.target !== el) return;
    const a = el.dataset.act, v = el.dataset.v;
    const N = (id) => DB.necesidades.find((x) => x.id_necesidad === Number(id));
    switch (a) {
      case "nav": go(el.dataset.to); break;
      case "reg-tipo": S.reg.tipo = v; S.reg.noSabe = false; S.reg.touched.tipo = true; render(); break;
      case "reg-nosabe": S.reg.noSabe = el.checked; if (el.checked) S.reg.tipo = ""; S.reg.touched.tipo = true; render(); break;
      case "verif": { const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches; let i = 1; S.verif = 1; render();
        const tick = () => { i++; S.verif = i; render(); if (i < 4) setTimeout(tick, reduce ? 250 : 1100); }; setTimeout(tick, reduce ? 250 : 1100); break; }
      case "consent": S.consent = el.checked; render(); break;
      case "sms": S.sms = el.checked; break;
      case "crear": go("d-hoy"); toast("Registro creado. Te avisaremos cuando te necesiten."); break;
      case "resp": S.respuesta = v || null; render(); break;
      case "avisos": S.avisos = el.checked; render(); toast(el.checked ? "Avisos activados" : "Avisos en pausa"); break;
      case "canal": S.canal = v; render(); break;
      case "copia": toast("Te enviaremos una copia de tus datos por WhatsApp en un máximo de 48 horas."); break;
      case "eliminar": S.confirmEliminar = true; render(); break;
      case "eliminar-no": S.confirmEliminar = false; render(); break;
      case "eliminar-si": S.confirmEliminar = false; go("preregistro"); toast("Tus datos fueron eliminados."); break;
      case "n-tipo": S.nueva.tipo = v; render(); break;
      case "n-meta": S.nueva.meta = Math.max(1, Math.min(20, S.nueva.meta + Number(v))); render(); break;
      case "n-radio": S.nueva.radio = Number(v); render(); break;
      case "cerrar-sheet": go("p-resumen"); break;
      case "lanzar": { const id = Math.max(...DB.necesidades.map((x) => x.id_necesidad)) + 1, est = estimado();
        DB.necesidades.unshift({ id_necesidad: id, tipo_sangre: S.nueva.tipo, zona: "Miraflores y alrededores", unidades_meta: S.nueva.meta, estado: "Activa", fecha_creacion: HOY + " 13:05",
          olas: [{ numero_ola: 1, radio_km: S.nueva.radio, donantes_notificados: est, respondieron: 0, fecha_envio: "13:05" }], unidades_obtenidas: 0 });
        S.nueva = { tipo: "", meta: 4, radio: 3 }; go("p-conv-" + id); toast(`Convocatoria lanzada: ola 1 enviada a ${est} donantes`); break; }
      case "ola": { const n = N(el.dataset.id), r = [3, 6, 10].find((x) => !n.olas.some((o) => o.radio_km === x)), cnt = Math.round((ESTIM[n.tipo_sangre] || 20) * (r === 6 ? 0.9 : 1.2));
        n.olas.push({ numero_ola: n.olas.length + 1, radio_km: r, donantes_notificados: cnt, respondieron: 0, fecha_envio: "13:10" }); render(); toast(`Ola ${n.olas.length} enviada a ${cnt} donantes a menos de ${r} km`); break; }
      case "u": S.unidadesInput = Math.max(0, Math.min(40, S.unidadesInput + Number(v))); render(); break;
      case "guardar-u": { const n = N(el.dataset.id); n.unidades_obtenidas = S.unidadesInput; render(); toast(`Unidades guardadas: ${n.unidades_obtenidas} de ${n.unidades_meta}`); break; }
      case "cerrar": S.cerrarConfirm = true; render(); break;
      case "cerrar-no": S.cerrarConfirm = false; render(); break;
      case "cerrar-si": { const n = N(el.dataset.id); n.estado = "Cerrada"; S.cerrarConfirm = false; render(); toast("Convocatoria cerrada"); break; }
      case "filtro": S.filtro = v; render(); break;
      case "copiar": { const tb = document.getElementById("tbl-reporte"); const txt = [...tb.rows].map((r) => [...r.cells].map((c) => c.innerText.trim()).join("\t")).join("\n");
        navigator.clipboard?.writeText(txt).then(() => toast("Tabla copiada. Pégala en Excel."), () => { const r = document.createRange(); r.selectNodeContents(tb); getSelection().removeAllRanges(); getSelection().addRange(r); toast("Tabla seleccionada: usa Ctrl+C para copiarla."); }); break; }
      case "abrir-alerta": S.alertaAbierta = Number(el.dataset.id); S.decision = ""; S.nota = ""; render(); break;
      case "cerrar-alerta": S.alertaAbierta = null; render(); break;
      case "dec": S.decision = el.value; render(); break;
      case "guardar-alerta": { const x = DB.alertas.find((q) => q.id_alerta === S.alertaAbierta); x.estado = "Revisada";
        x.decision = { falsa: "Falsa alarma", pausar: "Avisos pausados", escalar: "Enviada a la institución" }[S.decision]; S.alertaAbierta = null; render(); toast(`Alerta ${x.id_alerta} revisada: ${x.decision.toLowerCase()}`); break; }
      case "pre-tipo": S.pre.tipo = S.pre.tipo === v ? "" : v; render(); break;
      case "pre-acepto": S.pre.acepto = el.checked; render(); break;
    }
  });
  window.addEventListener("hashchange", render);
  render();
})();
