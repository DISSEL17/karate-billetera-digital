function fn() {
  var env = karate.env || 'qa';
  karate.log('karate.env =', env);

  // ---------------------------------------------------------------
  // URLs: la URL base es el frontend (Vite). Los microservicios
  // corren en el mismo host, cada uno en su puerto.
  // ---------------------------------------------------------------
  var baseUrl = karate.properties['base.url'] || 'http://134.209.211.10:5173/';
  var host = baseUrl.replace(/\/+$/, '').replace(/:\d+$/, '');

  // ---------------------------------------------------------------
  // Almacen global compartido entre escenarios y features.
  // Karate aisla las variables por escenario, asi que los datos que
  // deben sobrevivir (usuarios, saldos, codigo de transaccion) se
  // guardan en un mapa estatico de Java. Se serializa a JSON para no
  // compartir objetos JS entre contextos de ejecucion distintos.
  // (Karate re-evalua estas funciones en cada escenario, por eso cada
  // una resuelve Java.type por si misma en lugar de usar un closure.)
  // ---------------------------------------------------------------
  var store = {
    put: function (key, value) {
      Java.type('utils.SharedStore').put(key, JSON.stringify(value));
    },
    get: function (key) {
      var raw = Java.type('utils.SharedStore').get(key);
      if (raw == null) {
        karate.fail('No existe "' + key + '" en el almacen global. Ejecuta el flujo completo con TestRunner.');
      }
      return JSON.parse(raw);
    },
    has: function (key) {
      return Java.type('utils.SharedStore').contains(key);
    }
  };

  // ---------------------------------------------------------------
  // Genera un numero de celular de 9 digitos que empieza con 9.
  // Mezcla los ultimos digitos del timestamp con un aleatorio y
  // registra cada numero emitido para no repetirlo en la ejecucion.
  // ---------------------------------------------------------------
  var generarCelular = function () {
    var SharedStore = Java.type('utils.SharedStore');
    var numero;
    do {
      var tiempo = String(java.lang.System.currentTimeMillis()).slice(-5);
      var aleatorio = String(Math.floor(Math.random() * 1000));
      while (aleatorio.length < 3) aleatorio = '0' + aleatorio;
      numero = '9' + tiempo + aleatorio;
    } while (!SharedStore.reservePhone(numero));
    return numero;
  };

  var config = {
    env: env,
    baseUrl: baseUrl,
    authUrl: host + ':4001/auth/v1',
    walletUrl: host + ':4002/wallet/v1',
    transactionUrl: host + ':4003/transaction/v1',
    adminUrl: host + ':4004/admin/v1',

    channel: 'POSTMAN',
    adminChannel: 'ADMIN',
    pinDefault: '123456',
    saldoAsignado: 2000.00,
    montoTransferencia: 450.00,
    notaTransferencia: 'Pago de Servicios',

    // Credenciales publicadas en la documentacion de la API (sobreescribibles por -D)
    adminCredentials: {
      username: karate.properties['admin.user'] || 'admin',
      password: karate.properties['admin.password'] || 'superpassword'
    },

    store: store,
    generarCelular: generarCelular
  };

  // Timeouts de conexion y lectura (ms)
  karate.configure('connectTimeout', 10000);
  karate.configure('readTimeout', 20000);
  karate.configure('retry', { count: 3, interval: 2000 });
  karate.configure('logPrettyRequest', true);
  karate.configure('logPrettyResponse', true);

  return config;
}
