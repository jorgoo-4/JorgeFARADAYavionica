/* ui.js — carga data/*.csv, recalcula con Core y pinta las seis secciones.
 * No contiene ningún dato de candidatos, sensores ni criterios: todo sale de los CSV. */
(function () {
  'use strict';

  var ARCHIVOS = ['challenges', 'sensors', 'bus_rationale', 'requirements_inputs', 'requirements_derived_doc',
    'thresholds', 'criteria', 'scale', 'candidates', 'candidate_data', 'scores', 'score_rationale', 'funnel',
    'funnel_series', 'funnel_sospechosos', 'ioc_peripherals'];
  var OPCIONALES = ['funnel_series', 'funnel_sospechosos', 'ioc_peripherals'];
  var D = {};   // datos tal cual vienen de los CSV
  var S = {};   // estado editable en pantalla (no se guarda en los CSV)
  var R = null; // último cálculo

  var NOMBRE_ETQ = { fuente: 'fuente', vuelo: 'vuelo', calculo: 'cálculo', medido: 'medido', criterio_propio: 'criterio propio', pendiente: 'PENDIENTE' };
  var ABREV_ETQ = { fuente: 'F', vuelo: 'V', calculo: 'C', medido: 'M', criterio_propio: 'CP', pendiente: 'P!' };
  var NOMBRE_FAMILIA = { fallo_silencioso: 'fallo silencioso', recursos_vuelo: 'recursos de vuelo', programa_equipo: 'programa y equipo' };
  var COLOR_FAMILIA = { fallo_silencioso: 'var(--f-fallo)', recursos_vuelo: 'var(--f-recursos)', programa_equipo: 'var(--f-programa)' };
  var NOMBRE_FUNCION = { estimar_estado: 'Estimar estados', detectar_eventos: 'Detectar eventos', vigilar_salud: 'Vigilar la salud del sistema', registrar_comunicar: 'Registrar y comunicar', independiente: 'Independientes (no cuelgan del micro)' };
  var DECIMALES_REQ = { duracion_diseno_s: 0, memoria_registro_mb: 2, ops_paso: 0, mops_s: 2, mciclos_s: 1, resolucion_ecef_m: 1, vuelta_contador_min: 2, vueltas_rampa: 2 };
  var TITULO_COH = {
    ioc: 'CubeMX frente a sensores y umbrales', interfaz_incoherente: 'Interfaz incoherente (punto 4)',
    reparto_obsoleto: 'Justificación de reparto obsoleta (punto 5)', bahia_dudosa: 'Bahía sin decidir: filas dudosas (punto 6)',
    bahia_sin_decidir: 'Bahía sin decidir (punto 6)', doble_cuenta: 'Posible doble cuenta (punto 7)',
    critico_sin_unidades: 'Sensor crítico sin unidades'
  };

  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s === null || s === undefined ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function fmt(n, d) {
    if (n === null || n === undefined || isNaN(n)) return '—';
    return Number(n).toLocaleString('es-ES', { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  // Quita el prefijo de familia del número de pieza para las cabeceras estrechas (el id completo va en el title).
  function corto(id) { return String(id).replace(/^[A-Z]{3,}\d{2}(?=[A-Z]\d)/, ''); }
  function porId(filas, clave) { return Core.indexar(filas, clave || 'id'); }

  // ------------------------------------------------------------------ etiquetas de procedencia
  function tituloProcedencia(f) {
    if (!f) return 'sin dato';
    var t = [];
    ['fuente', 'revision', 'fecha_consulta', 'condiciones', 'origen', 'importado_de', 'url'].forEach(function (k) {
      if (f[k]) t.push(k + ': ' + f[k]);
    });
    return t.join('\n') || 'sin procedencia registrada';
  }

  function chips(f, opts) {
    opts = opts || {};
    var e = Core.parseEtiqueta(f ? f.etiqueta : '');
    e.partes = e.partes.filter(function (p) { return p !== 'pendiente'; });
    var tit = esc(tituloProcedencia(f));
    var h = e.partes.map(function (p) {
      return '<span class="etq etq-' + p + '" title="' + NOMBRE_ETQ[p] + '\n' + tit + '">' + (opts.corto ? ABREV_ETQ[p] : NOMBRE_ETQ[p]) + '</span>';
    }).join('');
    h += e.invalidas.map(function (p) { return '<span class="etq etq-invalida" title="etiqueta no válida">' + esc(p) + '</span>'; }).join('');
    if (false) {  // avisos de documento/revisión ocultos hasta añadir la bibliografía
      var doc = String(f.fuente || '').trim() || String(opts.fuenteAlt || '').trim();
      if (!doc) h += '<span class="etq etq-sindoc" title="Etiqueta fuente sin documento citado">' + (opts.corto ? '¿doc?' : 'sin documento') + '</span>';
      else if (!String(f.revision || '').trim() && !String(f.fecha_consulta || '').trim())
        h += '<span class="etq etq-sindoc" title="Fuente sin revisión ni fecha de consulta: ' + esc(doc) + '">' + (opts.corto ? '¿rev?' : 'sin revisión') + '</span>';
    }
    return h;
  }

  function pendientes() {
    var n = 0, por = {};
    var mirar = function (archivo, filas, alt) {
      filas.forEach(function (f) {
        var e = Core.parseEtiqueta(f.etiqueta);
        var p = !e.partes.length || e.partes.indexOf('pendiente') >= 0 || e.invalidas.length;
        if (!p && e.partes.indexOf('fuente') >= 0) {
          var doc = String(f.fuente || '').trim() || (alt ? alt(f) : '');
          p = !doc || (!String(f.revision || '').trim() && !String(f.fecha_consulta || '').trim());
        }
        if (p) { n++; por[archivo] = (por[archivo] || 0) + 1; }
      });
    };
    var escala = porId(D.scale, 'criterio_id');
    mirar('challenges', D.challenges); mirar('sensors', D.sensors);
    mirar('requirements_inputs', D.requirements_inputs, function (f) { return f.origen; });
    mirar('requirements_derived_doc', D.requirements_derived_doc);
    mirar('criteria', D.criteria, function (f) { return (escala[f.id] || {}).origen_dato; });
    mirar('candidate_data', D.candidate_data); mirar('scores', D.scores);
    return { n: n, por: por };
  }

  // ------------------------------------------------------------------ carga
  function cargar() {
    // Abierta con doble clic (file://) el navegador no deja leer los CSV con fetch:
    // se usan los mismos CSV empaquetados en app/data_bundle.js (tools/build_bundle.py).
    if (location.protocol === 'file:') {
      var b = window.DATA_BUNDLE;
      if (!b) return Promise.reject(new Error('falta app/data_bundle.js: ejecuta python3 matriz/tools/build_bundle.py'));
      ARCHIVOS.forEach(function (n) {
        if (b[n] !== undefined) D[n] = CSV.parse(b[n]);
        else if (OPCIONALES.indexOf(n) >= 0) D[n] = [];
        else throw new Error('data/' + n + '.csv no está en data_bundle.js');
      });
      return Promise.resolve();
    }
    return Promise.all(ARCHIVOS.map(function (n) {
      return fetch('data/' + n + '.csv', { cache: 'no-store' }).then(function (r) {
        if (!r.ok) throw new Error('data/' + n + '.csv (' + r.status + ')');
        return r.text();
      }).then(function (t) { D[n] = CSV.parse(t); }).catch(function (e) {
        if (OPCIONALES.indexOf(n) >= 0) { D[n] = []; return; }
        throw e;
      });
    }));
  }

  function estadoInicial() {
    S.entradasExp = {};
    D.requirements_inputs.forEach(function (f) { S.entradasExp[f.id] = Core.num(f.valor); });
    S.entradas = Object.assign({}, S.entradasExp);
    S.sensores = D.sensors.map(function (s) { return Object.assign({}, s); });
    S.pesosExp = Core.pesos(D.criteria);
    S.pesos = Object.assign({}, S.pesosExp);
    S.provisional = true;
    S.derivadosExp = Core.derivarRequisitos(S.entradasExp);
  }

  // ------------------------------------------------------------------ cálculo
  function calcular() {
    var datos = {}, notas = {};
    D.candidate_data.forEach(function (f) { (datos[f.candidato_id] = datos[f.candidato_id] || {})[f.campo] = f; });
    D.scores.forEach(function (f) { (notas[f.candidato_id] = notas[f.candidato_id] || {})[f.criterio_id] = f.nota; });
    var buses = Core.derivarBuses(S.sensores, D.bus_rationale);
    var filtros = {};
    D.candidates.forEach(function (c) { filtros[c.id] = Core.aplicarFiltro(datos[c.id] || {}, D.thresholds, buses); });
    var rk = Core.ranking(D.candidates, filtros, notas, D.criteria, S.pesos, { provisional: S.provisional });
    var ids = rk.supervivientes.map(function (s) { return s.id; });
    return {
      req: Core.derivarRequisitos(S.entradas), buses: buses, datos: datos, notas: notas, filtros: filtros, rk: rk,
      sens: ids.length > 1 ? Core.sensibilidad(ids, notas, D.criteria, S.pesos) : null,
      coh: Core.coherencia(S.sensores, buses, D.bus_rationale, D.ioc_peripherals)
    };
  }

  // ------------------------------------------------------------------ 0. misión
  function pintarMision() {
    var h = '<tr><th>Condición de vuelo</th><th>Dato</th><th>Problema real</th><th>Implicación en la aviónica</th><th>Etiqueta</th></tr>';
    D.challenges.forEach(function (c) {
      h += '<tr><td><strong>' + esc(c.condicion) + '</strong></td><td>' + esc(c.dato) + '</td><td>' + esc(c.problema) +
        '</td><td>' + esc(c.implicacion) + '</td><td>' + chips(c) + '</td></tr>';
    });
    $('tabla-mision').innerHTML = h;
  }

  // ------------------------------------------------------------------ 1. requisitos
  function pintarEntradas() {
    var h = '<tr><th>Parámetro</th><th>Valor</th><th>Unidad</th><th>De dónde sale</th><th>Etiqueta</th></tr>';
    D.requirements_inputs.forEach(function (f) {
      var cambiado = S.entradas[f.id] !== S.entradasExp[f.id];
      h += '<tr' + (cambiado ? ' class="cambiado"' : '') + '><td>' + esc(f.parametro) + '</td><td><input type="number" step="any" data-entrada="' +
        esc(f.id) + '" value="' + esc(S.entradas[f.id]) + '"></td><td>' + esc(f.unidad) + '</td><td class="pequeno">' + esc(f.origen) +
        '</td><td>' + chips(f, { fuenteAlt: f.origen }) + '</td></tr>';
    });
    $('tabla-entradas').innerHTML = h;
  }

  function pintarDerivados() {
    var h = '<tr><th>Requisito</th><th class="num">Valor</th><th>Unidad</th><th>Cómo se obtiene</th><th>Etiqueta</th><th>Se usa en</th></tr>';
    D.requirements_derived_doc.forEach(function (f) {
      var v, cambiado = false;
      if (f.tipo === 'constante') v = esc(f.valor_constante);
      else {
        v = fmt(R.req[f.id], DECIMALES_REQ[f.id] !== undefined ? DECIMALES_REQ[f.id] : 2);
        cambiado = Math.abs(R.req[f.id] - S.derivadosExp[f.id]) > 1e-9;
      }
      var eng = f.enganchado_a ? esc(f.enganchado_a) : '<span class="hueco">HUECO: no está enganchado a ningún umbral ni criterio</span>';
      h += '<tr' + (cambiado ? ' class="cambiado"' : '') + '><td>' + esc(f.requisito) + '</td><td class="num valor-grande">' + v +
        '</td><td>' + esc(f.unidad) + '</td><td class="pequeno">' + esc(f.como_se_obtiene) + '</td><td>' + chips(f) +
        '</td><td class="pequeno">' + eng + '</td></tr>';
    });
    $('tabla-derivados').innerHTML = h;

    var t = '<tr><th>Candidato</th><th class="num">MHz</th><th class="num">% de CPU del filtro</th></tr>';
    D.candidates.forEach(function (c) {
      var f = (R.datos[c.id] || {}).mhz, mhz = f ? Core.num(f.valor) : null;
      t += '<tr><td title="' + esc(c.id) + '">' + esc(c.id) + '</td><td class="num">' + (mhz ? fmt(mhz, 0) + ' ' + chips(f, { corto: true }) : '<span class="st st-sin_dato">sin dato</span>') +
        '</td><td class="num">' + (mhz ? fmt(R.req.mciclos_s / mhz * 100, 1) + ' %' : '—') + '</td></tr>';
    });
    $('tabla-cpu').innerHTML = t;
  }

  // ------------------------------------------------------------------ 2. inventario y buses
  function pintarSensores() {
    var h = '<tr><th>Id</th><th>Para qué lo necesito</th><th>Componente</th><th class="num">Cant.</th><th>Bus</th><th class="num">B/lect.</th><th class="num">Hz</th><th class="num">kbit/s</th><th>Bahía</th><th>Etiqueta</th><th>Por qué</th></tr>';
    var funcion = null, total = 0;
    S.sensores.forEach(function (s, i) {
      if (s.funcion !== funcion) { funcion = s.funcion; h += '<tr class="seccion"><td colspan="11">' + esc(NOMBRE_FUNCION[funcion] || funcion) + '</td></tr>'; }
      var n = Core.num(s.cantidad) || 0, b = Core.num(s.bytes_lectura) || 0, hz = Core.num(s.frecuencia_hz) || 0;
      var kbit = n * b * 8 * hz / 1000;
      total += kbit;
      var orig = D.sensors[i], cambiado = orig.cantidad !== s.cantidad || orig.bahia !== s.bahia;
      var sel = '<select data-bahia="' + i + '">' + ['', 'principal', 'aerofreno'].map(function (o) {
        return '<option value="' + o + '"' + (s.bahia === o ? ' selected' : '') + '>' + (o || 'sin decidir') + '</option>';
      }).join('') + '</select>';
      h += '<tr' + (cambiado ? ' class="cambiado"' : '') + '><td>' + esc(s.id) + '</td><td>' + esc(s.para_que) + '</td><td>' + esc(s.modelo) +
        '</td><td class="num"><input class="corto" type="number" min="0" step="1" data-cantidad="' + i + '" value="' + esc(s.cantidad) + '"></td><td>' + esc(s.bus) +
        '</td><td class="num">' + esc(s.bytes_lectura) + '</td><td class="num">' + esc(s.frecuencia_hz) + '</td><td class="num">' + fmt(kbit, 1) +
        '</td><td>' + sel + '</td><td>' + chips(s) + '</td><td><details><summary>ver</summary><p>' + esc(s.justificacion) + '</p></details></td></tr>';
    });
    $('tabla-sensores').innerHTML = h;
    $('trafico').innerHTML = 'Tráfico total de lectura de sensores: <strong>' + fmt(total, 1) + ' kbit/s</strong>. Un solo bus SPI a 10 MHz mueve 10 000 kbit/s: todo esto junto ocupa un ' +
      fmt(total / 10000 * 100, 1) + ' % de UN bus. Los buses no se separan por ancho de banda, sino por latencia y por aislamiento de fallos.';
  }

  function pintarBuses() {
    var sinB = R.buses.sin_bahia.length, dudosas = R.coh.filter(function (a) { return a.codigo === 'bahia_dudosa'; });
    $('avisos-bahia').innerHTML = sinB ? '<div class="aviso"><strong>' + sinB + ' sensores con bus sin bahía decidida.</strong> La cuenta de buses solo suma <code>bahia = principal</code>; mientras no decidas, las filas sin bahía cuentan como principal provisional (DECISIONES D-03).' +
      (dudosas.length ? '<ul>' + dudosas.map(function (a) { return '<li>' + esc(a.mensaje) + '</li>'; }).join('') + '</ul>' : '') + '</div>' : '';

    var usa = {};
    D.thresholds.forEach(function (u) { if (u.derivado_de && u.derivado_de.indexOf('bus:') === 0) usa[u.derivado_de.slice(4)] = u; });
    var h = '<tr><th>Recurso</th><th class="num">Dispositivos</th><th class="num">Buses pedidos</th><th class="num">Reserva</th><th class="num">Total exigido</th><th>Umbral</th><th>Sensores que lo justifican</th><th>Por qué ese reparto</th></tr>';
    R.buses.recursos.forEach(function (r) {
      var u = usa[r.bus], um = '—';
      if (u) {
        var csvMin = Core.num(u.minimo);
        um = esc(u.id) + ' ' + esc(u.umbral) + (csvMin !== r.total ? '<br><span class="st st-no" title="thresholds.csv dice ' + esc(u.minimo) + '">CSV = ' + esc(u.minimo) + ': ejecuta validate.py</span>' : '');
      }
      var sens = r.sensores.map(function (s) {
        return esc(s.id) + ' ' + esc(s.modelo) + ' ×' + s.cantidad + (s.bahia === 'sin decidir' ? ' <span class="suave">(sin bahía)</span>' : '');
      }).join('<br>') || '<span class="suave">ninguno</span>';
      h += '<tr><td><strong>' + esc(r.recurso) + '</strong></td><td class="num">' + fmt(r.dispositivos, 0) + (r.provisionales ? '<br><span class="suave pequeno">' + r.provisionales + ' provisionales</span>' : '') +
        '</td><td class="num">' + fmt(r.buses_pedidos, 0) + '</td><td class="num">' + fmt(r.reserva, 0) + '</td><td class="num valor-grande">' + fmt(r.total, 0) +
        '</td><td class="pequeno">' + um + '</td><td class="pequeno">' + sens + (r.avisos.length ? '<div class="aviso pequeno">' + r.avisos.map(esc).join('<br>') + '</div>' : '') +
        '</td><td><details><summary>ver</summary><p>' + esc(r.justificacion) + '</p></details></td></tr>';
    });
    $('tabla-buses').innerHTML = h;

    var grupos = {};
    R.coh.forEach(function (a) { if (a.codigo !== 'bahia_dudosa') (grupos[a.codigo] = grupos[a.codigo] || []).push(a); });
    var mcu = D.ioc_peripherals.length ? D.ioc_peripherals[0].mcu + ' (' + D.ioc_peripherals[0].ioc + ')' : 'sin .ioc importado';
    var c = Object.keys(grupos).map(function (k) {
      var err = grupos[k].some(function (a) { return a.nivel === 'error'; });
      return '<div class="aviso' + (err ? ' error' : '') + '"><strong>' + esc(TITULO_COH[k] || k) + (k === 'ioc' ? ' — ' + esc(mcu) : '') + '</strong><ul>' +
        grupos[k].map(function (a) { return '<li>' + esc(a.mensaje) + '</li>'; }).join('') + '</ul></div>';
    }).join('');
    $('coherencia').innerHTML = c || '<p class="suave">Sin avisos de coherencia.</p>';
  }

  // ------------------------------------------------------------------ 3. embudo
  function pintarEmbudo() {
    var pasos = D.funnel;
    if (!pasos.length) { $('grafico-embudo').innerHTML = '<p class="suave">Falta data/funnel.csv: ejecuta tools/import_st_selector.py.</p>'; return; }
    var max = Core.num(pasos[0].piezas_restantes), fila = 26, izq = 300, ancho = 400, alto = pasos.length * fila + 10;
    var svg = '<svg viewBox="0 0 ' + (izq + ancho + 70) + ' ' + alto + '" width="100%" role="img" aria-label="Embudo del selector">';
    pasos.forEach(function (p, i) {
      var n = Core.num(p.piezas_restantes), w = Math.max(1, n / max * ancho), y = i * fila + 5;
      svg += '<text x="' + (izq - 8) + '" y="' + (y + 16) + '" text-anchor="end" font-size="12">' + esc(p.paso) + '</text>' +
        '<rect x="' + izq + '" y="' + (y + 3) + '" width="' + w + '" height="' + (fila - 8) + '" fill="var(--acento)" opacity="' + (i === pasos.length - 1 ? 1 : 0.55) + '"/>' +
        '<text x="' + (izq + w + 6) + '" y="' + (y + 16) + '" font-size="12" font-weight="' + (i === pasos.length - 1 ? 700 : 400) + '">' + n + '</text>';
    });
    $('grafico-embudo').innerHTML = svg + '</svg>';

    var h = '<tr><th>#</th><th>Paso</th><th>Parámetro del selector</th><th class="num">Quedan</th><th class="num">Caen</th><th class="num">Caen por campo vacío</th></tr>';
    pasos.forEach(function (p) {
      h += '<tr><td>' + esc(p.orden) + '</td><td>' + esc(p.paso) + (p.umbral_id ? ' <span class="suave pequeno">' + esc(p.umbral_id) + '</span>' : '') + '</td><td class="pequeno">' + esc(p.selector_param) +
        '</td><td class="num"><strong>' + esc(p.piezas_restantes) + '</strong></td><td class="num">' + esc(p.eliminadas) + '</td><td class="num">' +
        (Core.num(p.eliminadas_campo_vacio) ? '<span class="st st-sosp">' + esc(p.eliminadas_campo_vacio) + '</span>' : '0') + '</td></tr>';
    });
    $('tabla-embudo').innerHTML = h + '<tr><td colspan="6" class="pequeno suave">Regenerable con <code>python3 tools/import_st_selector.py</code> desde el export del selector. Si no coincide con la cifra de referencia, la explicación está en DECISIONES.md (D-05).</td></tr>';

    var s = '<tr><th>Serie</th><th class="num">Piezas</th><th>Representante</th><th>¿Sobrevive?</th></tr>';
    D.funnel_series.forEach(function (x) {
      s += '<tr><td>' + esc(x.serie) + '</td><td class="num">' + esc(x.piezas) + '</td><td>' + (x.representante ? esc(x.representante) : '<span class="st st-sin_dato">sin representante</span>') +
        '</td><td>' + (x.representante_sobrevive === 'si' ? '<span class="st st-pasa">sí</span>' : '<span class="st st-no">no</span>') + '</td></tr>';
    });
    $('tabla-series').innerHTML = s;

    var sp = D.funnel_sospechosos;
    $('sospechosos').innerHTML = sp.length ? '<p class="pequeno">' + sp.length + ' piezas caen <strong>solo</strong> por campos vacíos en el selector: pueden ser huecos de la base de datos y no de la pieza. No se descartan en silencio; se revisan en la ficha.</p><details><summary>ver las ' + sp.length + '</summary><div class="tabla-scroll"><table><tr><th>Pieza</th><th>Serie</th><th>Pasos con campo vacío</th></tr>' +
      sp.map(function (x) { return '<tr><td>' + esc(x.pieza) + '</td><td>' + esc(x.serie) + '</td><td class="pequeno">' + esc(x.pasos_con_campo_vacio) + '</td></tr>'; }).join('') + '</table></div></details>'
      : '<p class="suave">Ninguna.</p>';
  }

  // ------------------------------------------------------------------ 4. filtro
  function ordenCandidatos() {
    var orden = { candidato: 0, control: 1, lista_larga: 2 };
    return D.candidates.slice().sort(function (a, b) { return (orden[a.rol] - orden[b.rol]) || D.candidates.indexOf(a) - D.candidates.indexOf(b); });
  }

  function pintarFiltro() {
    var cands = ordenCandidatos();
    var h = '<tr><th>Umbral</th><th>Exigido</th><th>Selector de ST</th>' + cands.map(function (c) {
      return '<th class="cand" title="' + esc(c.id + ' · ' + c.rol + (c.motivo_rol ? ' · ' + c.motivo_rol : '')) + '">' + esc(corto(c.id)) + '<br><span class="suave">' + esc(c.rol.replace('_', ' ')) + '</span></th>';
    }).join('') + '</tr>';
    D.thresholds.forEach(function (u, iu) {
      var ex = R.filtros[cands[0].id].detalle[iu];
      h += '<tr><td><strong>' + esc(u.umbral) + '</strong> <span class="suave pequeno">' + esc(u.id) + '</span></td><td class="pequeno">' + esc(ex.exigido_texto) +
        (u.derivado_de ? '<br><span class="suave">dispositivos → buses + reserva</span>' : '') + '</td><td class="pequeno suave">' + esc(u.selector_param) + '</td>';
      cands.forEach(function (c) {
        var d = R.filtros[c.id].detalle[iu], f = (R.datos[c.id] || {})[u.campo];
        var clase = d.estado === 'no' && d.sospechoso ? 'sosp' : d.estado;
        var marca = { pasa: '✓', no: '✗', sin_dato: '?', sosp: '✗ ?' }[clase];
        var tit = c.id + ' · ' + u.umbral + '\nvalor: ' + (d.valor || '(vacío)') + '\nexigido: ' + d.exigido_texto + (d.motivo ? '\n' + d.motivo : '') + '\n' + tituloProcedencia(f);
        h += '<td class="celda-filtro celda-' + clase + '" title="' + esc(tit) + '"><span class="v"><span class="st st-' + clase + '">' + marca + '</span> ' +
          esc(d.valor || (f && f.condiciones ? f.condiciones : 'sin dato')) + '</span>' + (f ? chips(f, { corto: true }) : '') + '</td>';
      });
      h += '</tr>';
    });
    h += '<tr class="veredicto"><td colspan="3">Veredicto</td>' + cands.map(function (c) {
      var f = R.filtros[c.id], cl = f.estado === 'PASA' ? 'pasa' : f.estado === 'SIN_DATO' ? 'sin_dato' : 'no';
      return '<td><span class="st st-' + cl + '">' + esc(f.estado.replace('_', ' ')) + '</span>' + (f.sospechosos.length ? ' <span class="st st-sosp" title="alguna eliminación viene de un campo vacío o a cero">sospechoso</span>' : '') + '</td>';
    }).join('') + '</tr>';
    $('tabla-filtro').innerHTML = h;

    $('faltan').innerHTML = '<div class="tabla-scroll"><table><tr><th>Candidato</th><th>Rol</th><th>No cumple</th><th>Sin dato (me falta mirarlo)</th></tr>' + cands.map(function (c) {
      var f = R.filtros[c.id];
      var no = f.fallos.map(function (d) { return esc(d.umbral_id + ' ' + d.umbral) + ': ' + esc(d.valor) + ' frente a ' + esc(d.exigido_texto) + (d.sospechoso ? ' <span class="st st-sosp">campo vacío o a cero: ¿hueco del selector?</span>' : ''); }).join('<br>');
      var sd = f.sin_dato.map(function (d) {
        var fila = (R.datos[c.id] || {})[d.campo];
        return esc(d.umbral_id + ' ' + d.umbral) + ' <span class="suave">(' + esc(fila && fila.condiciones ? fila.condiciones : d.motivo) + ')</span>';
      }).join('<br>');
      return '<tr><td>' + esc(c.id) + '</td><td class="pequeno">' + esc(c.rol) + (c.motivo_rol ? '<br><span class="suave">' + esc(c.motivo_rol) + '</span>' : '') + '</td><td class="pequeno">' + (no || '—') + '</td><td class="pequeno">' + (sd || '—') + '</td></tr>';
    }).join('') + '</table></div>';
  }

  // ------------------------------------------------------------------ 5. ranking
  function criteriosOrdenados() {
    var orden = Core.FAMILIAS;
    return D.criteria.slice().sort(function (a, b) { return orden.indexOf(a.familia) - orden.indexOf(b.familia) || D.criteria.indexOf(a) - D.criteria.indexOf(b); });
  }

  function colorCriterio(c) {
    var mismos = D.criteria.filter(function (k) { return k.familia === c.familia; });
    var i = mismos.indexOf(c), n = mismos.length;
    return { color: COLOR_FAMILIA[c.familia] || 'var(--suave)', opacidad: 1 - i * (0.6 / Math.max(1, n - 1)) };
  }

  function pesosCambiados() {
    return D.criteria.filter(function (c) { return Math.abs(S.pesos[c.id] - S.pesosExp[c.id]) > 1e-6; });
  }

  function pintarRanking() {
    var cambiados = pesosCambiados();
    var red = Core.redondearA100(S.pesos, 1);
    $('aviso-pesos').innerHTML = cambiados.length ? '<div class="aviso error"><strong>Los pesos ya no son los del expediente.</strong> Al mover un deslizador el resto se renormaliza para sumar 100 %. Expediente → ahora: ' +
      cambiados.map(function (c) { return esc(c.criterio) + ' ' + fmt(S.pesosExp[c.id], 1) + ' → ' + fmt(red[c.id], 1) + ' %'; }).join(' · ') +
      '. <button type="button" data-reset-pesos>Volver a los pesos del expediente</button></div>' : '';

    var rk = R.rk, sup = rk.supervivientes, crit = criteriosOrdenados();
    var h = '';
    if (!sup.length) {
      h = '<div class="aviso"><strong>Nadie pasa el filtro completo todavía.</strong> Todos tienen algún umbral sin dato (por ejemplo, la coexistencia en CubeMX sin verificar). Marca «incluir aprobados condicionados» para ver el ranking provisional.</div>';
    } else {
      var fila = 34, izq = 190, ancho = 520, alto = sup.length * fila + 10;
      var svg = '<svg viewBox="0 0 ' + (izq + ancho + 90) + ' ' + alto + '" width="100%" role="img" aria-label="Ranking ponderado">';
      sup.forEach(function (s, i) {
        var y = i * fila + 5, x = izq;
        svg += '<text x="' + (izq - 8) + '" y="' + (y + 19) + '" text-anchor="end" font-size="13" font-weight="600">' + s.posicion + '. ' + esc(s.id) + (s.condicionado ? ' *' : '') + '</text>';
        crit.forEach(function (c) {
          var d = s.desglose.filter(function (x) { return x.criterio === c.id; })[0];
          if (!d) return;
          var w = d.aporte / 100 * ancho, col = colorCriterio(c);
          svg += '<rect x="' + x + '" y="' + (y + 4) + '" width="' + Math.max(0, w - 1) + '" height="' + (fila - 10) + '" fill="' + col.color + '" opacity="' + col.opacidad.toFixed(2) + '"><title>' +
            esc(c.criterio + ': peso ' + fmt(d.peso, 1) + ' % × nota ' + d.nota + '/5 = ' + fmt(d.aporte, 2) + ' puntos') + '</title></rect>';
          x += w;
        });
        svg += '<text x="' + (x + 6) + '" y="' + (y + 19) + '" font-size="13" font-weight="700">' + fmt(s.total, 1) + '</text>';
      });
      svg += '</svg>';
      var ley = '<div class="leyenda">' + crit.map(function (c) {
        var col = colorCriterio(c);
        return '<span><span class="sw" style="background:' + col.color + ';opacity:' + col.opacidad.toFixed(2) + '"></span>' + esc(c.criterio) + ' <span class="suave">(' + esc(NOMBRE_FAMILIA[c.familia]) + ')</span></span>';
      }).join('') + '</div>';
      var margen = rk.margen !== null ? '<p><strong>Margen sobre el segundo: ' + fmt(rk.margen, 1) + ' puntos.</strong> ' +
        (rk.empate ? 'Empate exacto.' : rk.empate_tecnico ? 'Menos de ' + Core.EMPATE_TECNICO_PUNTOS + ' puntos: empate técnico. No presumas de ganador; decide con un criterio de desempate declarado.' : 'Margen suficiente para sostener la elección.') + '</p>' : '';
      var cond = sup.some(function (s) { return s.condicionado; }) ? '<p class="pequeno suave">* aprobado condicionado: no falla ningún umbral, pero tiene alguno sin dato (sección 4).</p>' : '';
      h = svg + ley + margen + cond;
    }
    $('grafico-ranking').innerHTML = h;

    var e = '';
    if (rk.eliminados.length) e += '<h3>Eliminados</h3><ul>' + rk.eliminados.map(function (x) {
      var mot = x.fallos.length ? x.fallos.map(function (d) { return d.umbral + (d.sospechoso ? ' (campo vacío: sospechoso)' : ''); }).join(', ') : 'sin dato en ' + x.sin_dato.map(function (d) { return d.umbral; }).join(', ');
      return '<li><strong>' + esc(x.id) + '</strong>: ' + esc(mot) + '</li>';
    }).join('') + '</ul>';
    if (rk.sin_notas.length) e += '<h3>Pasan, pero sin notas completas</h3><ul>' + rk.sin_notas.map(function (x) { return '<li>' + esc(x.id) + ': faltan ' + esc(x.faltan.join(', ')) + '</li>'; }).join('') + '</ul>';
    if (rk.fuera_de_lista.length) e += '<h3>Fuera de la lista corta</h3><ul>' + rk.fuera_de_lista.map(function (x) { return '<li>' + esc(x.id) + ': ' + esc(x.motivo) + '</li>'; }).join('') + '</ul>';
    $('eliminados').innerHTML = e;

    pintarValoresPesos();
    pintarNotas();
  }

  function crearDeslizadores() {
    var h = '<strong>Criterio</strong><strong class="num">Peso</strong><span></span><strong class="num">Expediente</strong>';
    criteriosOrdenados().forEach(function (c) {
      h += '<span>' + esc(c.criterio) + ' <span class="suave pequeno">' + esc(NOMBRE_FAMILIA[c.familia]) + '</span></span>' +
        '<span class="num" id="peso-' + esc(c.id) + '"></span>' +
        '<input type="range" min="0" max="100" step="0.1" data-peso="' + esc(c.id) + '" aria-label="Peso de ' + esc(c.criterio) + '">' +
        '<span class="num suave" title="severidad ' + esc(c.severidad) + ' × no detectabilidad ' + esc(c.no_detectabilidad) + '">' + fmt(S.pesosExp[c.id], 1) + ' %<br><span class="pequeno">' + esc(c.severidad) + ' × ' + esc(c.no_detectabilidad) + '</span></span>';
    });
    $('pesos').innerHTML = h;
  }

  function pintarValoresPesos() {
    var red = Core.redondearA100(S.pesos, 1);  // lo que se enseña suma exactamente 100
    D.criteria.forEach(function (c) {
      $('peso-' + c.id).textContent = fmt(red[c.id], 1) + ' %';
      var r = document.querySelector('input[data-peso="' + c.id + '"]');
      if (r && document.activeElement !== r) r.value = S.pesos[c.id];
    });
  }

  function moverPeso(id, v) {
    var viejo = S.pesos[id], resto = 100 - viejo, nuevoResto = 100 - v, otros = D.criteria.filter(function (c) { return c.id !== id; });
    otros.forEach(function (c) { S.pesos[c.id] = resto > 1e-9 ? S.pesos[c.id] * nuevoResto / resto : nuevoResto / otros.length; });
    S.pesos[id] = v;
  }

  function pintarNotas() {
    var escala = porId(D.scale, 'criterio_id'), raz = porId(D.score_rationale, 'criterio_id');
    var notas = {};
    D.scores.forEach(function (f) { notas[f.candidato_id + '|' + f.criterio_id] = f; });
    var cands = ordenCandidatos().filter(function (c) { return D.scores.some(function (f) { return f.candidato_id === c.id; }); });
    var h = '<tr><th>Criterio</th><th class="num">Peso</th><th>Ancla 5</th><th>Ancla 3</th><th>Ancla 1</th><th>De dónde sale el dato</th>' +
      cands.map(function (c) { return '<th class="cand num" title="' + esc(c.id) + '">' + esc(corto(c.id)) + '</th>'; }).join('') + '</tr>';
    var fam = null, red = Core.redondearA100(S.pesos, 1);
    criteriosOrdenados().forEach(function (c) {
      if (c.familia !== fam) { fam = c.familia; h += '<tr class="seccion"><td colspan="' + (6 + cands.length) + '">' + esc(NOMBRE_FAMILIA[fam] || fam) + '</td></tr>'; }
      var e = escala[c.id] || {};
      h += '<tr><td><strong>' + esc(c.criterio) + '</strong> ' + chips(c, { corto: true, fuenteAlt: e.origen_dato }) + '<details><summary>por qué estas notas</summary><p>' + esc((raz[c.id] || {}).justificacion || 'SIN JUSTIFICACIÓN') +
        '</p><p class="suave">Qué pasa si me equivoco: ' + esc(c.consecuencia) + '</p></details></td><td class="num">' + fmt(red[c.id], 1) + ' %</td><td class="pequeno">' + esc(e.ancla_5) +
        '</td><td class="pequeno">' + esc(e.ancla_3) + '</td><td class="pequeno">' + esc(e.ancla_1) + '</td><td class="pequeno suave">' + esc(e.origen_dato) + '</td>';
      cands.forEach(function (k) {
        var f = notas[k.id + '|' + c.id];
        h += f ? '<td class="num" title="' + esc(f.observacion || '') + '"><span class="valor-grande">' + esc(f.nota) + '</span>' + (f.observacion ? '<span class="hueco" title="' + esc(f.observacion) + '"> *</span>' : '') + '<br>' + chips(f, { corto: true }) + '</td>'
          : '<td class="num"><span class="st st-sin_dato">—</span></td>';
      });
      h += '</tr>';
    });
    $('tabla-notas').innerHTML = h + '<tr><td colspan="' + (6 + cands.length) + '" class="pequeno suave">* nota con observación (pasa el ratón por encima). Etiquetas abreviadas: F fuente · V vuelo · C cálculo · M medido · CP criterio propio · P! pendiente.</td></tr>';
  }

  // ------------------------------------------------------------------ 6. sensibilidad
  function nombreCrit(id) { return (porId(D.criteria)[id] || {}).criterio || id; }

  function pintarSensibilidad() {
    var s = R.sens;
    if (!s) {
      ['frases', 'tabla-escenarios', 'tabla-vuelco', 'tabla-vuelco-familia'].forEach(function (k) { $(k).innerHTML = ''; });
      $('frases').innerHTML = '<p class="suave">Hacen falta al menos dos candidatos puntuados en el ranking.</p>';
      return;
    }
    var g = s.base.ganador.ganador, escen = [{ n: 'Pesos actuales', t: s.base }, { n: 'Todos los pesos iguales', t: s.iguales }]
      .concat(s.sin.map(function (x) { return { n: 'Sin «' + nombreCrit(x.criterio) + '»', t: { totales: x.totales, ganador: x.ganador } }; }));
    var mismos = escen.filter(function (e) { return e.t.ganador.ganador === g && !e.t.ganador.empate; }).length;

    var fr = '<p class="frase">Con los pesos actuales gana ' + esc(g) + (s.base.ganador.empate ? ' (empatado)' : '') + '. Gana el mismo en ' + mismos + ' de ' + escen.length + ' escenarios' +
      (s.iguales.ganador.ganador !== g ? '; con los pesos iguales gana ' + esc(s.iguales.ganador.ganador) : '') + '.</p>';
    s.vuelco_familia.forEach(function (v) {
      var nom = NOMBRE_FAMILIA[v.familia] || v.familia;
      if (v.x === null) fr += '<p>La familia «' + esc(nom) + '» (hoy ' + fmt(v.peso_actual, 1) + ' %) no cambia el ganador en todo el rango de 0 a 100 %.</p>';
      else fr += '<p' + (v.familia === 'fallo_silencioso' ? ' class="frase"' : '') + '>El ganador cambia si la familia «' + esc(nom) + '» ' + (v.delta < 0 ? 'baja del ' : 'sube del ') + fmt(v.x, 1) +
        ' % (hoy ' + fmt(v.peso_actual, 1) + ' %): pasaría a ganar ' + esc(v.nuevo_ganador) + '.</p>';
    });
    $('frases').innerHTML = '<div class="caja">' + fr + '</div>';

    var ids = s.ids;
    var h = '<tr><th>Escenario</th>' + ids.map(function (id) { return '<th class="num cand" title="' + esc(id) + '">' + esc(corto(id)) + '</th>'; }).join('') + '<th>Ganador</th></tr>';
    escen.forEach(function (e) {
      var max = Math.max.apply(null, ids.map(function (id) { return e.t.totales[id]; }));
      h += '<tr><td>' + esc(e.n) + '</td>' + ids.map(function (id) {
        var v = e.t.totales[id];
        return '<td class="num' + (Math.abs(v - max) < 1e-9 ? ' celda-pasa' : '') + '">' + fmt(v, 1) + '</td>';
      }).join('') + '<td' + (e.t.ganador.ganador !== g ? ' class="celda-no"' : '') + '><strong>' + esc(e.t.ganador.ganadores.join(' = ')) + '</strong></td></tr>';
    });
    $('tabla-escenarios').innerHTML = h;

    var fila = function (nombre, v) {
      return '<tr><td>' + esc(nombre) + '</td><td class="num">' + fmt(v.peso_actual, 1) + ' %</td><td class="num">' + (v.x === null ? '—' : fmt(v.x, 1) + ' %') +
        '</td><td class="num">' + (v.delta === null ? '—' : (v.delta > 0 ? '+' : '') + fmt(v.delta, 1)) + '</td><td>' + (v.nuevo_ganador ? esc(v.nuevo_ganador) : '<span class="suave">no vuelca en 0–100 %</span>') + '</td></tr>';
    };
    var cab = '<tr><th>Criterio</th><th class="num">Peso</th><th class="num">Vuelca en</th><th class="num">Δ</th><th>Nuevo ganador</th></tr>';
    $('tabla-vuelco').innerHTML = cab + s.vuelco.slice().sort(function (a, b) {
      return (a.delta === null) - (b.delta === null) || Math.abs(a.delta) - Math.abs(b.delta);
    }).map(function (v) { return fila(nombreCrit(v.criterio), v); }).join('');
    $('tabla-vuelco-familia').innerHTML = cab.replace('Criterio', 'Familia') + s.vuelco_familia.map(function (v) { return fila(NOMBRE_FAMILIA[v.familia] || v.familia, v); }).join('');
  }

  // ------------------------------------------------------------------ exportación a Markdown
  function md(filas) { return filas.map(function (f) { return '| ' + f.map(function (c) { return String(c).replace(/\|/g, '\\|').replace(/\n/g, ' '); }).join(' | ') + ' |'; }); }
  function tabla(cab, filas) { return md([cab]).concat(['|' + cab.map(function () { return ' --- '; }).join('|') + '|'], md(filas)).join('\n'); }

  function exportar() {
    var L = [], hoy = new Date().toISOString().slice(0, 10);
    L.push('# Selección de aviónica — estado exportado el ' + hoy, '');
    if (pesosCambiados().length) L.push('> **Atención:** los pesos de esta exportación NO son los del expediente.', '');
    L.push('## Requisitos', '', tabla(['Parámetro', 'Valor', 'Unidad', 'Etiqueta'], D.requirements_inputs.map(function (f) { return [f.parametro, S.entradas[f.id], f.unidad, f.etiqueta]; })), '');
    L.push(tabla(['Requisito', 'Valor', 'Unidad', 'Etiqueta', 'Se usa en'], D.requirements_derived_doc.map(function (f) {
      return [f.requisito, f.tipo === 'constante' ? f.valor_constante : fmt(R.req[f.id], DECIMALES_REQ[f.id] !== undefined ? DECIMALES_REQ[f.id] : 2), f.unidad, f.etiqueta, f.enganchado_a || 'HUECO'];
    })), '');
    L.push('## Buses', '', tabla(['Recurso', 'Dispositivos', 'Buses pedidos', 'Reserva', 'Total exigido'], R.buses.recursos.map(function (r) { return [r.recurso, r.dispositivos, r.buses_pedidos, r.reserva, r.total]; })), '');
    if (R.buses.sin_bahia.length) L.push('Sensores sin bahía (cuentan como principal provisional): ' + R.buses.sin_bahia.join(', '), '');
    L.push('## Embudo del selector de ST', '', tabla(['Paso', 'Quedan', 'Caen por campo vacío'], D.funnel.map(function (p) { return [p.paso, p.piezas_restantes, p.eliminadas_campo_vacio]; })), '');
    var cands = ordenCandidatos();
    L.push('## Filtro', '', 'PASA ✓ · NO ✗ · SIN DATO ? · eliminación sospechosa ✗?', '');
    L.push(tabla(['Umbral'].concat(cands.map(function (c) { return corto(c.id); })), D.thresholds.map(function (u, i) {
      return [u.id + ' ' + u.umbral].concat(cands.map(function (c) {
        var d = R.filtros[c.id].detalle[i];
        return (d.estado === 'pasa' ? '✓' : d.estado === 'sin_dato' ? '?' : d.sospechoso ? '✗?' : '✗') + ' ' + (d.valor || '');
      }));
    }).concat([['Veredicto'].concat(cands.map(function (c) { return R.filtros[c.id].estado; }))])), '');
    L.push('## Ranking' + (S.provisional ? ' (incluye aprobados condicionados)' : ''), '');
    L.push(R.rk.supervivientes.length ? tabla(['Pos.', 'Candidato', 'Puntos', 'Condicionado'], R.rk.supervivientes.map(function (s) { return [s.posicion, s.id, fmt(s.total, 1), s.condicionado ? 'sí' : 'no']; })) : 'Nadie pasa el filtro completo.', '');
    if (R.rk.margen !== null) L.push('Margen sobre el segundo: ' + fmt(R.rk.margen, 1) + ' puntos' + (R.rk.empate_tecnico ? ' (empate técnico, < ' + Core.EMPATE_TECNICO_PUNTOS + ')' : '') + '.', '');
    L.push('## Pesos', '');
    var red = Core.redondearA100(S.pesos, 1);
    L.push(tabla(['Criterio', 'Familia', 'Severidad', 'No detectabilidad', 'Peso (%)'], D.criteria.map(function (c) {
      return [c.criterio, NOMBRE_FAMILIA[c.familia], c.severidad, c.no_detectabilidad, fmt(red[c.id], 1)];
    }).concat([['**Total**', '', '', '', fmt(Object.keys(red).reduce(function (a, k) { return a + red[k]; }, 0), 1)]])), '');
    L.push('Redondeo con reparto del resto (mayor resto): los porcentajes suman exactamente 100.', '');
    if (R.sens) {
      L.push('## Sensibilidad', '');
      L.push(tabla(['Escenario', 'Ganador'], [['Pesos actuales', R.sens.base.ganador.ganadores.join(' = ')], ['Pesos iguales', R.sens.iguales.ganador.ganadores.join(' = ')]].concat(
        R.sens.sin.map(function (x) { return ['Sin ' + nombreCrit(x.criterio), x.ganador.ganadores.join(' = ')]; }))), '');
      L.push(tabla(['Criterio / familia', 'Peso', 'Vuelca en', 'Nuevo ganador'], R.sens.vuelco.map(function (v) {
        return [nombreCrit(v.criterio), fmt(v.peso_actual, 1), v.x === null ? '—' : fmt(v.x, 1), v.nuevo_ganador || 'no vuelca'];
      }).concat(R.sens.vuelco_familia.map(function (v) {
        return ['familia ' + NOMBRE_FAMILIA[v.familia], fmt(v.peso_actual, 1), v.x === null ? '—' : fmt(v.x, 1), v.nuevo_ganador || 'no vuelca'];
      }))), '');
    }
    var blob = new Blob([L.join('\n')], { type: 'text/markdown;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'matriz-avionica-' + hoy + '.md';
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 0);
  }

  // ------------------------------------------------------------------ orquestación
  function refrescar(que) {
    R = calcular();
    if (!que || que === 'req') pintarDerivados();
    if (!que || que === 'sensores') { pintarSensores(); }
    if (!que || que === 'sensores' || que === 'pesos') {
      if (que !== 'pesos') { pintarBuses(); pintarFiltro(); }
      pintarRanking();
      pintarSensibilidad();
    }
  }

  function enlazar() {
    $('tabla-entradas').addEventListener('input', function (e) {
      var id = e.target.getAttribute('data-entrada');
      if (!id) return;
      var v = Core.num(e.target.value);
      if (v === null) return;
      S.entradas[id] = v;
      e.target.closest('tr').className = v !== S.entradasExp[id] ? 'cambiado' : '';
      refrescar('req');
    });
    $('btn-reset-req').addEventListener('click', function () { S.entradas = Object.assign({}, S.entradasExp); pintarEntradas(); refrescar('req'); });
    $('tabla-sensores').addEventListener('change', function (e) {
      var i = e.target.getAttribute('data-cantidad'), j = e.target.getAttribute('data-bahia');
      if (i !== null) S.sensores[+i].cantidad = String(Math.max(0, Math.round(Core.num(e.target.value) || 0)));
      if (j !== null) S.sensores[+j].bahia = e.target.value;
      refrescar('sensores');
    });
    $('pesos').addEventListener('input', function (e) {
      var id = e.target.getAttribute('data-peso');
      if (!id) return;
      moverPeso(id, Core.num(e.target.value));
      refrescar('pesos');
    });
    var volver = function () { S.pesos = Object.assign({}, S.pesosExp); refrescar('pesos'); };
    $('btn-reset-pesos').addEventListener('click', volver);
    $('aviso-pesos').addEventListener('click', function (e) { if (e.target.hasAttribute('data-reset-pesos')) volver(); });
    $('chk-provisional').addEventListener('change', function (e) { S.provisional = e.target.checked; refrescar('pesos'); });
    $('btn-export').addEventListener('click', exportar);
  }

  function iniciar() {
    cargar().then(function () {
      estadoInicial();
      pintarMision();
      pintarEntradas();
      pintarEmbudo();
      crearDeslizadores();
      enlazar();
      refrescar();
    }).catch(function (e) {
      $('error-carga').innerHTML = '<div class="aviso error"><strong>No se han podido cargar los datos:</strong> ' + esc(e.message) + '</div>';
      throw e;
    });
  }

  iniciar();
})();
