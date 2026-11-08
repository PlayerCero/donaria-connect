/* Datos ficticios del prototipo. Cada colección refleja una tabla del modelo entidad–relación
   del trabajo final (sección 4.6.3). Ningún dato es real. Cuando exista la base en SQL Server,
   este archivo se reemplaza por llamadas a la API REST. */
window.DB = {
  // DONANTE (dni_hash nunca se muestra completo; tipo_sangre y fechas son datos sensibles)
  donante: {
    id_donante: 482, nombres: "Lucía Paredes Rojas", dni_mask: "••••5821", tipo_sangre: "O+",
    distrito: "Pueblo Libre", telefono_whatsapp: "987 654 321", estado_verificacion: "verificado",
    fecha_ultima_donacion: "2026-05-28", sexo: "F", canal: "WhatsApp",
  },
  // CONSENTIMIENTO
  consentimiento: { version_texto: "1.0", fecha_hora: "2025-08-20 19:42", vigente: true },
  // INSTITUCION
  instituciones: [
    { id_institucion: 1, razon_social: "Clínica Delgado Auna", distrito: "Miraflores", direccion: "Calle General Borgoño 1135, sótano 1",
      horario: "Lun–sáb 8:00–19:00 · dom 8:00–13:00", autorizacion_sanitaria: "Vigente", estado_afiliacion: "Piloto" },
    { id_institucion: 2, razon_social: "Clínica Good Hope", distrito: "Miraflores", direccion: "Malecón Balta 956",
      horario: "Lun–vie 7:30–17:00", autorizacion_sanitaria: "Vigente", estado_afiliacion: "En evaluación" },
  ],
  // USUARIO_INSTITUCION
  usuario: { nombre: "Mg. Carla Ríos", rol: "Coordinadora del banco de sangre", id_institucion: 1 },
  // NECESIDAD + OLA_CONVOCATORIA + RESULTADO_AGREGADO
  necesidades: [
    { id_necesidad: 31, tipo_sangre: "O-", zona: "Miraflores y alrededores", unidades_meta: 6, estado: "Activa", fecha_creacion: "2026-10-15 08:10",
      olas: [ { numero_ola: 1, radio_km: 3, donantes_notificados: 38, respondieron: 4, fecha_envio: "08:12" },
              { numero_ola: 2, radio_km: 6, donantes_notificados: 71, respondieron: 3, fecha_envio: "10:15" } ],
      unidades_obtenidas: 2 },
    { id_necesidad: 30, tipo_sangre: "A+", zona: "Miraflores y alrededores", unidades_meta: 8, estado: "Activa", fecha_creacion: "2026-10-14 16:40",
      olas: [ { numero_ola: 1, radio_km: 3, donantes_notificados: 52, respondieron: 6, fecha_envio: "16:42" } ], unidades_obtenidas: 5 },
    { id_necesidad: 29, tipo_sangre: "B+", zona: "Lima centro y sur", unidades_meta: 4, estado: "Cerrada", fecha_creacion: "2026-10-11 09:05",
      olas: [ { numero_ola: 1, radio_km: 3, donantes_notificados: 19, respondieron: 2, fecha_envio: "09:06" },
              { numero_ola: 2, radio_km: 6, donantes_notificados: 33, respondieron: 2, fecha_envio: "12:30" } ], unidades_obtenidas: 4 },
    { id_necesidad: 28, tipo_sangre: "O+", zona: "Miraflores y alrededores", unidades_meta: 10, estado: "Cerrada", fecha_creacion: "2026-10-08 07:55",
      olas: [ { numero_ola: 1, radio_km: 3, donantes_notificados: 96, respondieron: 7, fecha_envio: "07:58" },
              { numero_ola: 2, radio_km: 6, donantes_notificados: 88, respondieron: 4, fecha_envio: "11:00" } ], unidades_obtenidas: 10 },
    { id_necesidad: 27, tipo_sangre: "AB+", zona: "Miraflores y alrededores", unidades_meta: 2, estado: "Cerrada", fecha_creacion: "2026-10-03 13:20",
      olas: [ { numero_ola: 1, radio_km: 3, donantes_notificados: 9, respondieron: 1, fecha_envio: "13:21" },
              { numero_ola: 2, radio_km: 6, donantes_notificados: 15, respondieron: 1, fecha_envio: "15:40" } ], unidades_obtenidas: 2 },
  ],
  // DONACION_CONFIRMADA (vista del donante)
  donaciones: [
    { fecha: "2026-05-28", institucion: "Clínica Delgado Auna", unidades_convocatoria: 14, tipo: "Convocatoria O+" },
    { fecha: "2026-01-16", institucion: "Clínica Delgado Auna", unidades_convocatoria: 9, tipo: "Convocatoria O+" },
    { fecha: "2025-09-03", institucion: "Hospital Rebagliati", unidades_convocatoria: null, tipo: "Donación por iniciativa propia" },
  ],
  // Convocatoria abierta que ve el donante (NOTIFICACION recibida)
  convocatoriaDonante: { id_necesidad: 26, tipo_sangre: "O+", institucion_id: 1, distancia_km: 4.2, recibida: "hoy 9:05", ola: 1 },
  // ALERTA_ANTIFRAUDE
  alertas: [
    { id_alerta: 118, donante: "D-1093", dni_mask: "••••0417", regla: "3 donaciones registradas en 45 días (mínimo 90 días entre donaciones de sangre total)",
      institucion: "Clínica Delgado Auna", fecha: "2026-10-15 07:30", horas_restantes: 69, estado: "Pendiente" },
    { id_alerta: 117, donante: "D-0758", dni_mask: "••••3366", regla: "Mismo celular asociado a 2 DNI distintos",
      institucion: "—", fecha: "2026-10-14 11:02", horas_restantes: 45, estado: "Pendiente" },
    { id_alerta: 116, donante: "D-2210", dni_mask: "••••9180", regla: "Donación confirmada en 2 instituciones el mismo día",
      institucion: "Clínica Good Hope", fecha: "2026-10-13 18:45", horas_restantes: 15, estado: "Pendiente" },
    { id_alerta: 115, donante: "D-0412", dni_mask: "••••2275", regla: "3 donaciones registradas en 45 días",
      institucion: "Clínica Delgado Auna", fecha: "2026-10-10 09:15", horas_restantes: 0, estado: "Revisada" },
  ],
  distritos: ["Barranco", "Breña", "Chorrillos", "Jesús María", "La Molina", "La Victoria", "Lima Cercado", "Lince", "Magdalena del Mar",
    "Miraflores", "Pueblo Libre", "San Borja", "San Isidro", "San Miguel", "Santiago de Surco", "Surquillo", "Callao"],
  tipos: ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"],
};
