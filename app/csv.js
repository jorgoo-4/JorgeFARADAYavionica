/* csv.js — lector de CSV (RFC 4180: comillas, comillas dobles escapadas, saltos de línea dentro de campo).
 * Funciona en el navegador (window.CSV) y en Node (module.exports). */
(function (raiz) {
  'use strict';

  function filas(texto) {
    if (texto.charCodeAt(0) === 0xfeff) texto = texto.slice(1);
    var out = [], fila = [], campo = '', i = 0, comillas = false, n = texto.length;
    while (i < n) {
      var c = texto[i];
      if (comillas) {
        if (c === '"') {
          if (texto[i + 1] === '"') { campo += '"'; i += 2; continue; }
          comillas = false; i++; continue;
        }
        campo += c; i++; continue;
      }
      if (c === '"') { comillas = true; i++; continue; }
      if (c === ',') { fila.push(campo); campo = ''; i++; continue; }
      if (c === '\r') { i++; continue; }
      if (c === '\n') { fila.push(campo); out.push(fila); fila = []; campo = ''; i++; continue; }
      campo += c; i++;
    }
    if (campo !== '' || fila.length) { fila.push(campo); out.push(fila); }
    return out;
  }

  function parse(texto) {
    var f = filas(texto);
    if (!f.length) return [];
    var cab = f[0];
    return f.slice(1).filter(function (r) { return r.length > 1 || r[0] !== ''; }).map(function (r) {
      var o = {};
      cab.forEach(function (k, j) { o[k] = r[j] === undefined ? '' : r[j]; });
      return o;
    });
  }

  var CSV = { parse: parse, filas: filas };
  if (typeof module !== 'undefined' && module.exports) module.exports = CSV;
  else raiz.CSV = CSV;
})(this);
