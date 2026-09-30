/* core.js — requisitos, buses, filtro, puntuación y sensibilidad.
 * Funciones puras, sin DOM. Funciona en el navegador (window.Core) y en Node (module.exports),
 * para que tests/test_core.py lo contraste con su espejo tools/core.py.
 * Nada de lo que describe un candidato, un criterio o un umbral está escrito aquí: todo sale de data/*.csv.
 */
(function (raiz) {
  'use strict';

  var ETIQUETAS = ['fuente', 'vuelo', 'calculo', 'medido', 'criterio_propio', 'pendiente'];
  var FAMILIAS = ['fallo_silencioso', 'recursos_vuelo', 'programa_equipo'];
  // Regla del expediente (Matriz A22): menos de 5 puntos entre primero y segundo es empate técnico.
  var EMPATE_TECNICO_PUNTOS = 5;
  var EPS = 1e-9;

  // ------------------------------------------------------------------ utilidades
  function num(v) {
    if (v === null || v === undefined) return null;
    if (typeof v === 'number') return isFinite(v) ? v : null;
    var t = String(v).trim().replace('−', '-').replace(',', '.');
    if (!/^-?\d+(\.\d+)?$/.test(t)) return null;
    return parseFloat(t);
  }

  function parseEtiqueta(texto) {
    var partes = [], invalidas = [];
    String(texto || '').split('+').forEach(function (p) {
      p = p.trim();
      if (!p) return;
      if (ETIQUETAS.indexOf(p) >= 0) { if (partes.indexOf(p) < 0) partes.push(p); } else invalidas.push(p);
    });
    return { partes: partes, invalidas: invalidas };
  }

  function indexar(filas, clave) {
    var m = {};
    filas.forEach(function (f) { m[f[clave]] = f; });
    return m;
  }

  // Redondeo de presentación con reparto del resto (método del mayor resto): suma exactamente 100.
  function redondearA100(valores, decimales) {
    var d = decimales === undefined ? 1 : decimales;
    var escala = Math.pow(10, d);
    var ids = Object.keys(valores);
    var total = ids.reduce(function (s, k) { return s + valores[k]; }, 0);
    var base = {}, resto = [], suma = 0;
    ids.forEach(function (k) {
      var v = valores[k] / total * 100 * escala;
      base[k] = Math.floor(v + EPS);
      suma += base[k];
      resto.push({ k: k, r: v - base[k] });
    });
    resto.sort(function (a, b) { return b.r - a.r || (a.k < b.k ? -1 : 1); });
    for (var i = 0; i < Math.round(100 * escala) - suma; i++) base[resto[i % resto.length].k] += 1;
    var out = {};
    ids.forEach(function (k) { out[k] = base[k] / escala; });
    return out;
  }

  // ------------------------------------------------------------------ 1. requisitos
  function derivarRequisitos(e) {
    var dur = e.vuelo_s * (1 + e.margen);
    var ops = e.coste_por_paso * Math.pow(e.n_estados, 3);
    var mops = ops * e.f_filtro_hz / 1e6;
    var vuelta = Math.pow(2, 32) / 1e6 / 60;
    return {
      duracion_diseno_s: dur,
      memoria_registro_mb: e.bytes_muestra * e.f_registro_hz * dur / 1048576,
      ops_paso: ops,
      mops_s: mops,
      mciclos_s: mops * e.ciclos_por_op,
      resolucion_ecef_m: Math.pow(2, Math.floor(Math.log(e.escala_ecef_m) / Math.LN2 + EPS) - 23),
      vuelta_contador_min: vuelta,
      vueltas_rampa: e.rampa_h * 60 / vuelta
    };
  }

  // ------------------------------------------------------------------ 2. buses
  // Cuenta SOLO bahia = principal; bahia vacía cuenta como principal provisional (con aviso, D-03).
  function derivarBuses(sensores, busRationale) {
    var porBus = {}, recursos = [], avisos = [], sinBahia = [];
    busRationale.forEach(function (b) {
      var r = {
        bus: b.bus, recurso: b.recurso, tipo: b.tipo, dispositivos: 0,
        buses_pedidos: num(b.buses_pedidos) || 0, reserva: num(b.reserva) || 0,
        total: 0, sensores: [], provisionales: 0, justificacion: b.justificacion, avisos: []
      };
      r.total = r.buses_pedidos + r.reserva;
      porBus[b.bus] = r;
      recursos.push(r);
    });
    sensores.forEach(function (s) {
      if (!s.bus || s.bus === 'ninguna') return;
      var bahia = (s.bahia || '').trim();
      if (bahia === '') sinBahia.push(s.id);
      if (bahia === 'aerofreno') return;
      var r = porBus[s.bus];
      if (!r) { avisos.push('El sensor ' + s.id + ' usa el bus «' + s.bus + '», que no tiene fila en bus_rationale.csv'); return; }
      var n = num(s.cantidad) || 0;
      r.dispositivos += n;
      if (bahia === '') r.provisionales += n;
      r.sensores.push({ id: s.id, modelo: s.modelo, cantidad: n, bahia: bahia || 'sin decidir' });
    });
    recursos.forEach(function (r) {
      if (r.tipo === 'punto_a_punto' && r.buses_pedidos < r.dispositivos)
        r.avisos.push('Faltan canales: ' + r.dispositivos + ' dispositivos punto a punto y solo ' + r.buses_pedidos + ' pedidos.');
      if (r.tipo === 'punto_a_punto' && r.buses_pedidos > r.dispositivos)
        r.avisos.push('Pide ' + r.buses_pedidos + ' y los sensores contados son ' + r.dispositivos + ': la diferencia tiene que estar en la justificación.');
      if (r.tipo === 'compartido' && r.dispositivos > 0 && r.buses_pedidos < 1)
        r.avisos.push('Hay dispositivos y ningún bus pedido.');
      if (r.tipo === 'compartido' && r.buses_pedidos > r.dispositivos)
        r.avisos.push('Más buses que dispositivos (' + r.buses_pedidos + ' frente a ' + r.dispositivos + ').');
    });
    if (sinBahia.length)
      avisos.push(sinBahia.length + ' sensores sin bahía asignada: se cuentan como principal provisional.');
    return { recursos: recursos, porBus: porBus, sin_bahia: sinBahia, avisos: avisos };
  }

  // ------------------------------------------------------------------ 3. filtro
  function exigido(u, buses) {
    if (u.derivado_de && u.derivado_de.indexOf('bus:') === 0) {
      var r = buses && buses.porBus[u.derivado_de.slice(4)];
      return r ? r.total : num(u.minimo);
    }
    return (u.operador === '>=' || u.operador === '<=') ? num(u.minimo) : u.minimo;
  }

  function textoExigido(u, valor) {
    if (u.operador === '>=') return '≥ ' + valor + (u.unidad ? ' ' + u.unidad : '');
    if (u.operador === '<=') return '≤ ' + valor + (u.unidad ? ' ' + u.unidad : '');
    if (u.operador === 'afirmativo') return u.minimo_texto || 'sí';
    if (u.operador === 'contiene_alguno') return 'contiene: ' + String(valor).split(';').join(' / ');
    return String(valor).split(';').join(' / ');
  }

  // datos: {campo: fila de candidate_data}. Devuelve pasa / fallos / sin_dato, sin mezclarlos.
  function aplicarFiltro(datos, umbrales, buses) {
    var fallos = [], sinDato = [], detalle = [];
    umbrales.forEach(function (u) {
      var fila = datos[u.campo];
      var raw = fila ? String(fila.valor || '').trim() : '';
      var req = exigido(u, buses);
      var d = {
        umbral_id: u.id, umbral: u.umbral, campo: u.campo, valor: raw, exigido: req,
        exigido_texto: textoExigido(u, req), etiqueta: fila ? fila.etiqueta : '', estado: 'pasa',
        sospechoso: false, motivo: ''
      };
      var vacio = raw === '-';
      if (raw === '') {
        d.estado = 'sin_dato';
        d.motivo = fila ? 'celda vacía en el registro' : 'no hay dato: no lo he mirado';
      } else if (u.operador === '>=' || u.operador === '<=') {
        var v = vacio ? 0 : num(raw);
        if (v === null) { d.estado = 'sin_dato'; d.motivo = 'valor no numérico: «' + raw + '»'; }
        else {
          var ok = u.operador === '>=' ? v >= req - EPS : v <= req + EPS;
          if (!ok) { d.estado = 'no'; d.sospechoso = vacio || v === 0; }
        }
      } else {
        var bajo = raw.toLowerCase();
        var lista = String(req || '').split(';').map(function (x) { return x.trim().toLowerCase(); }).filter(Boolean);
        var pasa;
        if (u.operador === 'igual') pasa = bajo === lista[0];
        else if (u.operador === 'en') pasa = lista.indexOf(bajo) >= 0;
        else if (u.operador === 'contiene_alguno') pasa = lista.some(function (x) { return bajo.indexOf(x) >= 0; });
        else if (u.operador === 'afirmativo') pasa = !/^(no\b|sin\b|ninguna|-$)/i.test(raw);
        else { d.estado = 'sin_dato'; d.motivo = 'operador desconocido «' + u.operador + '»'; pasa = true; }
        if (!pasa) { d.estado = 'no'; d.sospechoso = vacio; }
      }
      if (d.estado === 'no') {
        d.motivo = d.sospechoso
          ? 'campo vacío o a cero en la fuente: puede ser un hueco de la base de datos, no de la pieza'
          : 'el valor no llega';
        fallos.push(d);
      } else if (d.estado === 'sin_dato') sinDato.push(d);
      detalle.push(d);
    });
    return {
      pasa: fallos.length === 0 && sinDato.length === 0,
      estado: fallos.length ? 'ELIMINADO' : (sinDato.length ? 'SIN_DATO' : 'PASA'),
      fallos: fallos, sin_dato: sinDato,
      sospechosos: fallos.filter(function (f) { return f.sospechoso; }),
      detalle: detalle
    };
  }

  // ------------------------------------------------------------------ 4. puntuación
  // El peso NO se lee: sale de severidad × no detectabilidad.
  function pesos(criterios) {
    var bruto = {}, suma = 0;
    criterios.forEach(function (c) {
      bruto[c.id] = (num(c.severidad) || 0) * (num(c.no_detectabilidad) || 0);
      suma += bruto[c.id];
    });
    var out = {};
    criterios.forEach(function (c) { out[c.id] = suma ? bruto[c.id] / suma * 100 : 0; });
    return out;
  }

  function puntuar(notas, criterios, w) {
    var desglose = [], faltan = [], total = 0;
    criterios.forEach(function (c) {
      var n = notas ? num(notas[c.id]) : null;
      if (n === null) { faltan.push(c.id); return; }
      var aporte = w[c.id] * n / 5;
      total += aporte;
      desglose.push({ criterio: c.id, familia: c.familia, peso: w[c.id], nota: n, aporte: aporte });
    });
    return { total: faltan.length ? null : total, desglose: desglose, faltan: faltan };
  }

  // candidatos: filas de candidates.csv; filtros: {id: aplicarFiltro(...)}; notas: {id: {criterio: nota}}
  // opciones.provisional: admite a los que solo fallan por sin_dato (marcados como condicionados).
  function ranking(candidatos, filtros, notas, criterios, w, opciones) {
    var prov = !!(opciones && opciones.provisional);
    var sup = [], elim = [], sinNotas = [], fuera = [];
    candidatos.forEach(function (c) {
      if (c.rol === 'lista_larga') { fuera.push({ id: c.id, motivo: c.motivo_rol }); return; }
      var f = filtros[c.id];
      var admitido = f.pasa || (prov && f.fallos.length === 0);
      if (!admitido) {
        elim.push({ id: c.id, estado: f.estado, fallos: f.fallos, sin_dato: f.sin_dato, sospechosos: f.sospechosos });
        return;
      }
      var p = puntuar(notas[c.id], criterios, w);
      if (p.total === null) { sinNotas.push({ id: c.id, faltan: p.faltan }); return; }
      sup.push({ id: c.id, total: p.total, desglose: p.desglose, condicionado: !f.pasa, sin_dato: f.sin_dato });
    });
    sup.sort(function (a, b) { return b.total - a.total || (a.id < b.id ? -1 : 1); });
    sup.forEach(function (s, i) {
      s.posicion = (i > 0 && Math.abs(s.total - sup[i - 1].total) < EPS) ? sup[i - 1].posicion : i + 1;
    });
    var margen = sup.length > 1 ? sup[0].total - sup[1].total : null;
    return {
      supervivientes: sup, eliminados: elim, sin_notas: sinNotas, fuera_de_lista: fuera,
      margen: margen,
      empate: margen !== null && margen < EPS,
      empate_tecnico: margen !== null && margen < EMPATE_TECNICO_PUNTOS
    };
  }

  // ------------------------------------------------------------------ 5. sensibilidad
  function totales(ids, notas, criterios, w) {
    var out = {};
    ids.forEach(function (id) { out[id] = puntuar(notas[id], criterios, w).total; });
    return out;
  }

  function ganador(t) {
    var ids = Object.keys(t), max = -Infinity;
    ids.forEach(function (k) { if (t[k] > max) max = t[k]; });
    var g = ids.filter(function (k) { return Math.abs(t[k] - max) < EPS; }).sort();
    return { ganador: g[0], ganadores: g, empate: g.length > 1 };
  }

  // S_c(x) = x·A_c + (100 − x)·R_c. Devuelve el x más cercano a x0 en [0, 100] donde el ganador deja de serlo.
  function vuelcoLineal(ids, A, R, x0) {
    var S = function (c, x) { return x * A[c] + (100 - x) * R[c]; };
    var base = {};
    ids.forEach(function (c) { base[c] = S(c, x0); });
    var g = ganador(base);
    if (g.empate) return { ganador: g.ganador, x: x0, delta: 0, nuevo_ganador: g.ganadores[1], ya_empatado: true };
    var mejor = null;
    ids.forEach(function (c) {
      if (c === g.ganador) return;
      var dA = A[g.ganador] - A[c], dR = R[g.ganador] - R[c], den = dA - dR;
      if (Math.abs(den) < 1e-12) return;
      var x = -100 * dR / den;
      if (x < -EPS || x > 100 + EPS || Math.abs(x - x0) < EPS) return;
      if (!mejor || Math.abs(x - x0) < Math.abs(mejor.x - x0) - EPS) mejor = { x: x, nuevo_ganador: c };
    });
    if (!mejor) return { ganador: g.ganador, x: null, delta: null, nuevo_ganador: null };
    return { ganador: g.ganador, x: mejor.x, delta: mejor.x - x0, nuevo_ganador: mejor.nuevo_ganador };
  }

  function sensibilidad(ids, notas, criterios, w) {
    ids = ids.filter(function (id) { return puntuar(notas[id], criterios, w).total !== null; });
    var n = criterios.length;
    var base = totales(ids, notas, criterios, w);
    var iguales = {};
    criterios.forEach(function (c) { iguales[c.id] = 100 / n; });
    var tIg = totales(ids, notas, criterios, iguales);
    var sin = criterios.map(function (c) {
      var w2 = {}, resto = 100 - w[c.id];
      criterios.forEach(function (k) { w2[k.id] = k.id === c.id ? 0 : (resto > EPS ? w[k.id] / resto * 100 : 0); });
      var t = totales(ids, notas, criterios, w2);
      return { criterio: c.id, totales: t, ganador: ganador(t) };
    });
    var nota = function (id, c) { return num(notas[id][c]); };
    var vuelco = criterios.map(function (c) {
      var wi = w[c.id], A = {}, R = {};
      ids.forEach(function (id) {
        A[id] = nota(id, c.id) / 5;
        R[id] = wi < 100 - EPS ? (base[id] - wi * nota(id, c.id) / 5) / (100 - wi) : 0;
      });
      var v = vuelcoLineal(ids, A, R, wi);
      v.criterio = c.id; v.peso_actual = wi;
      return v;
    });
    var familias = [];
    criterios.forEach(function (c) { if (familias.indexOf(c.familia) < 0) familias.push(c.familia); });
    var vuelcoFamilia = familias.map(function (f) {
      var WF = 0;
      criterios.forEach(function (c) { if (c.familia === f) WF += w[c.id]; });
      var A = {}, R = {};
      ids.forEach(function (id) {
        var a = 0, r = 0;
        criterios.forEach(function (c) {
          var aporte = w[c.id] * nota(id, c.id) / 5;
          if (c.familia === f) a += aporte; else r += aporte;
        });
        A[id] = WF > EPS ? a / WF : 0;
        R[id] = WF < 100 - EPS ? r / (100 - WF) : 0;
      });
      var v = vuelcoLineal(ids, A, R, WF);
      v.familia = f; v.peso_actual = WF;
      return v;
    });
    return {
      ids: ids, base: { totales: base, ganador: ganador(base) },
      iguales: { totales: tIg, ganador: ganador(tIg) },
      sin: sin, vuelco: vuelco, vuelco_familia: vuelcoFamilia
    };
  }

  // ------------------------------------------------------------------ 6. coherencia
  var PALABRAS_BUS = {
    spi: /\bSPI\d?\b/, i2c: /\bI2C\b/i, uart: /\bU(S)?ART\b/, can: /\bCAN\b/, adc: /\bADC\b/,
    qspi_sdmmc: /QSPI|QUADSPI|OCTOSPI|SDMMC|SD\/MMC|microSD|\bSDIO\b/i, gpio: /\bGPIO\b/, pwm: /\bPWM\b/,
    timer: /\btimer\b/i
  };
  // Dispositivo mencionado en un texto de reparto -> cómo se reconoce en sensors.csv.
  var DISPOSITIVOS = [
    ['IMU', /\bIMU\b/, /\bIMU\b/], ['acelerómetro', /aceler[oó]metro/i, /aceler[oó]metro/i],
    ['magnetómetro', /magnet[oó]metro/i, /magnet[oó]metro/i], ['barómetro', /bar[oó]metro/i, /bar[oó]metro/i],
    ['GNSS', /\bGNSS\b/, /\bGNSS\b/], ['radio', /\bradio\b/i, /radio|telemetr[ií]a|mLRS/i],
    ['consola', /consola/i, /consola/i], ['servo', /\bservo\b/i, /\bservo\b/i],
    ['zumbador', /zumbador/i, /zumbador/i], ['giróscopo', /gir[oó]scopo/i, /gir[oó]scopo/i],
    ['termistor', /termistor/i, /termistor|NTC/i], ['continuidad', /continuidad/i, /continuidad/i],
    ['breakwire', /breakwire/i, /breakwire/i], ['armado', /\barmado\b/i, /armad/i],
    ['PPS', /\bPPS\b/, /\bPPS\b/], ['memoria de registro', /memoria de registro/i, /flash NOR|registro|guardar el vuelo/i]
  ];

  function sensoresQue(sensores, re) {
    return sensores.filter(function (s) { return re.test(s.modelo + ' ' + s.para_que); });
  }

  function coherencia(sensores, buses, busRationale, ioc) {
    var out = [];
    var add = function (codigo, nivel, mensaje, ref) { out.push({ codigo: codigo, nivel: nivel, mensaje: mensaje, ref: ref || '' }); };

    // CubeMX (.ioc) frente a sensores y umbrales
    if (ioc && ioc.length) {
      var enIoc = {};
      ioc.forEach(function (p) { enIoc[p.bus] = (enIoc[p.bus] || 0) + (num(p.unidades) || 0); });
      buses.recursos.forEach(function (r) {
        var n = enIoc[r.bus] || 0;
        if (r.dispositivos > 0 && n === 0) add('ioc', 'aviso', r.recurso + ': hay ' + r.dispositivos + ' dispositivos y ningún periférico habilitado en CubeMX.', r.bus);
        else if (n > 0 && r.dispositivos === 0) add('ioc', 'aviso', r.recurso + ': periférico habilitado en CubeMX (' + n + ') sin sensor que lo justifique.', r.bus);
        else if (n > 0 && n < r.buses_pedidos) add('ioc', 'aviso', r.recurso + ': CubeMX tiene ' + n + ', por debajo de los ' + r.buses_pedidos + ' pedidos.', r.bus);
        else if (n > r.total) add('ioc', 'info', r.recurso + ': CubeMX tiene ' + n + ', por encima del umbral de ' + r.total + '.', r.bus);
      });
      Object.keys(enIoc).forEach(function (b) {
        if (!buses.porBus[b]) add('ioc', 'info', 'CubeMX habilita «' + b + '», que no es ningún recurso de bus_rationale.csv.', b);
      });
    }

    sensores.forEach(function (s) {
      // (4) la justificación menciona una interfaz distinta de su campo bus
      Object.keys(PALABRAS_BUS).forEach(function (b) {
        if (b !== s.bus && PALABRAS_BUS[b].test(s.justificacion || ''))
          add('interfaz_incoherente', 'aviso', s.id + ' (' + s.modelo + '): la justificación menciona ' + b.toUpperCase() + ' y su bus es ' + s.bus + '.', s.id);
      });
      // (6) bahía sin decidir; resalta las que el propio texto sitúa en la otra bahía
      if (!(s.bahia || '').trim() && s.bus !== 'ninguna' && /otra bah[ií]a|nodo del aerofreno|nodo de la otra/i.test(s.justificacion || ''))
        add('bahia_dudosa', 'aviso', s.id + ' (' + s.modelo + '): sin bahía y el texto dice que va en el nodo del aerofreno; hoy se cuenta en la principal.', s.id);
      // (7) posible doble cuenta con la electrónica independiente
      if (s.funcion !== 'independiente' && (num(s.cantidad) || 0) >= 2 && /no cuelga de mi|electr[oó]nica (de recuperaci[oó]n )?redundante/i.test(s.justificacion || ''))
        add('doble_cuenta', 'aviso', s.id + ' (' + s.modelo + '): cantidad ' + s.cantidad + ' e incluye una unidad de la electrónica redundante (funcion = independiente): posible doble cuenta en ' + s.bus + '.', s.id);
      if (String(s.critico || '').trim().toLowerCase() === 'si' && (num(s.cantidad) || 0) < 1)
        add('critico_sin_unidades', 'error', s.id + ' (' + s.modelo + '): marcado crítico con cantidad ' + s.cantidad + '.', s.id);
    });
    if (buses.sin_bahia.length)
      add('bahia_sin_decidir', 'aviso', buses.sin_bahia.length + ' sensores sin bahía: se cuentan como principal provisional.', buses.sin_bahia.join(' '));

    // (5) justificación de reparto que menciona dispositivos que ya no están
    busRationale.forEach(function (b) {
      var t = b.justificacion || '';
      DISPOSITIVOS.forEach(function (d) {
        if (d[1].test(t) && sensoresQue(sensores, d[2]).length === 0)
          add('reparto_obsoleto', 'aviso', b.recurso + ': la justificación menciona «' + d[0] + '» y no hay ningún sensor así en sensors.csv.', b.bus);
      });
      if (/IMU redundante|segunda IMU|dos IMU/i.test(t)) {
        var imus = sensoresQue(sensores, /\bIMU\b/).reduce(function (a, s) { return a + (num(s.cantidad) || 0); }, 0);
        if (imus < 2) add('reparto_obsoleto', 'aviso', b.recurso + ': la justificación menciona una IMU redundante y sensors.csv tiene ' + imus + ' IMU.', b.bus);
      }
      var m = t.match(/(\d+)\s+chip-select,\s+uno por dispositivo (\w+)/i);
      if (m) {
        var r = buses.porBus[m[2].toLowerCase()];
        if (r && r.dispositivos !== parseInt(m[1], 10))
          add('reparto_obsoleto', 'aviso', b.recurso + ': cuenta ' + m[1] + ' chip-select «uno por dispositivo ' + m[2] + '» y hay ' + r.dispositivos + ' dispositivos ' + m[2] + '.', b.bus);
      }
    });
    return out;
  }

  var Core = {
    ETIQUETAS: ETIQUETAS, FAMILIAS: FAMILIAS, EMPATE_TECNICO_PUNTOS: EMPATE_TECNICO_PUNTOS,
    num: num, parseEtiqueta: parseEtiqueta, indexar: indexar, redondearA100: redondearA100,
    derivarRequisitos: derivarRequisitos, derivarBuses: derivarBuses, exigido: exigido,
    aplicarFiltro: aplicarFiltro, pesos: pesos, puntuar: puntuar, ranking: ranking,
    totales: totales, ganador: ganador, sensibilidad: sensibilidad, coherencia: coherencia
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = Core;
  else raiz.Core = Core;
})(this);
