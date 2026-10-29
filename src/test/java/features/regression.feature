@regression @parallel=false
Feature: Regresion Billetera Digital - Registro, transferencia y validacion en receptor

  Flujo E2E sobre los microservicios Auth (4001), Wallet (4002), Transaction (4003)
  y Admin (4004). Los datos se comparten entre escenarios mediante el almacen
  global "store" definido en karate-config.js, por lo que el orden importa y la
  ejecucion es secuencial (parallel(1)).

  Background:
    * configure headers = { 'x-channel': '#(channel)', 'Content-Type': 'application/json' }
    * def esquemaUsuario =
      """
      {
        id: '#regex u_\\d+',
        phone: '#regex 9\\d{8}',
        name: '#string',
        email: '##string',
        pin: '##string',
        status: 'ACTIVE',
        contacts: '#array'
      }
      """
    * def esquemaSaldo = { balance: '#number', currency: 'USD' }

  @escenario1
  Scenario: Escenario 1 - Registro de usuarios Emisor y Receptor con saldo asignado
    # ---------- Datos de prueba ----------
    * def emisor = { phone: '#(generarCelular())', fullName: 'Emisor QA Karate', pin: '#(pinDefault)' }
    * set emisor.email = 'emisor.' + emisor.phone + '@qa.test'
    * def receptor = { phone: '#(generarCelular())', fullName: 'Receptor QA Karate', pin: '#(pinDefault)' }
    * set receptor.email = 'receptor.' + receptor.phone + '@qa.test'
    * match emisor.phone == '#regex 9\\d{8}'
    * match receptor.phone == '#regex 9\\d{8}'
    * assert emisor.phone != receptor.phone

    # ---------- Registro Emisor ----------
    Given url authUrl
    And path 'register'
    And request emisor
    When method post
    Then status 201
    And match response.message == 'Usuario creado exitosamente'
    And match response.user == esquemaUsuario
    And match response.user contains { phone: '#(emisor.phone)', name: '#(emisor.fullName)', email: '#(emisor.email)' }
    * set emisor.id = response.user.id

    # ---------- Registro Receptor ----------
    Given url authUrl
    And path 'register'
    And request receptor
    When method post
    Then status 201
    And match response.user == esquemaUsuario
    And match response.user contains { phone: '#(receptor.phone)', name: '#(receptor.fullName)', email: '#(receptor.email)' }
    * set receptor.id = response.user.id

    # ---------- Validacion negativa: usuario duplicado ----------
    Given url authUrl
    And path 'register'
    And request { phone: '#(emisor.phone)', fullName: 'Emisor Duplicado', pin: '#(pinDefault)' }
    When method post
    Then match [400, 409] contains responseStatus
    And match response == { code: 'AUTH_006', message: '#string' }

    # ---------- Asignacion de saldo (Admin Service, llamada en bucle) ----------
    * def admin = call read('classpath:features/common/admin-login.feature')
    * table abonos
      | userId      | amount        | adminToken  |
      | emisor.id   | saldoAsignado | admin.token |
      | receptor.id | saldoAsignado | admin.token |
    * call read('classpath:features/common/asignar-saldo.feature') abonos

    # ---------- Verificacion del saldo con el token de cada usuario ----------
    * def sesionEmisor = call read('classpath:features/common/login.feature') { phone: '#(emisor.phone)', pin: '#(emisor.pin)' }
    Given url walletUrl
    And path 'balance'
    And header Authorization = 'Bearer ' + sesionEmisor.token
    When method get
    Then status 200
    And match response == esquemaSaldo
    And match response.balance == saldoAsignado
    * def saldoInicialEmisor = response.balance

    * def sesionReceptor = call read('classpath:features/common/login.feature') { phone: '#(receptor.phone)', pin: '#(receptor.pin)' }
    Given url walletUrl
    And path 'balance'
    And header Authorization = 'Bearer ' + sesionReceptor.token
    When method get
    Then status 200
    And match response == esquemaSaldo
    And match response.balance == saldoAsignado
    * def saldoInicialReceptor = response.balance

    # ---------- Persistencia en el almacen global ----------
    * store.put('emisor', emisor)
    * store.put('receptor', receptor)
    * store.put('saldoInicialEmisor', saldoInicialEmisor)
    * store.put('saldoInicialReceptor', saldoInicialReceptor)
    * karate.log('Emisor:', emisor.phone, emisor.id, '| Receptor:', receptor.phone, receptor.id)

  @escenario2
  Scenario: Escenario 2 - Transferencia del Emisor al Receptor por 450.00
    * def emisor = store.get('emisor')
    * def receptor = store.get('receptor')
    * def saldoInicialEmisor = store.get('saldoInicialEmisor')

    # ---------- Login Emisor y captura del token Bearer ----------
    Given url authUrl
    And path 'login'
    And request { phone: '#(emisor.phone)', pin: '#(emisor.pin)' }
    When method post
    Then status 200
    And match response == { token: '#string', expiresIn: '#number', user: '#object' }
    And match response.user.id == emisor.id
    * def tokenEmisor = response.token

    # ---------- Transferencia ----------
    Given url transactionUrl
    And path 'transfer'
    And header Authorization = 'Bearer ' + tokenEmisor
    And request { recipientId: '#(receptor.id)', amount: '#(montoTransferencia)', description: '#(notaTransferencia)', categoryId: 'cat_tx' }
    When method post
    Then status 200
    And match response == { transactionId: '#notnull', referenceCode: '#notnull', status: '#string', message: '#string' }

    # Tabla de asercion sobre la respuesta de la transferencia
    * def transferencia = response
    * table esperado
      | campo           | valor                               |
      | 'status'        | 'COMPLETED'                         |
      | 'message'       | 'Transferencia realizada con éxito' |
      | 'transactionId' | '#regex tx_\\d+'                    |
      | 'referenceCode' | '#regex REF-\\d+'                   |
    * def validarCampo = function(r){ var m = karate.match(transferencia[r.campo], r.valor); return { campo: r.campo, pass: m.pass, detalle: m.message } }
    * def resultados = karate.map(esperado, validarCampo)
    * match each resultados contains { pass: true }

    # ---------- Persistencia del identificador ----------
    * store.put('transactionId', transferencia.transactionId)
    * store.put('codigoTransaccion', transferencia.referenceCode)
    * karate.log('Transaccion:', transferencia.transactionId, '| Referencia:', transferencia.referenceCode)

    # ---------- Saldo del Emisor: saldo_inicial - 450.00 ----------
    Given url walletUrl
    And path 'balance'
    And header Authorization = 'Bearer ' + tokenEmisor
    When method get
    Then status 200
    And match response == esquemaSaldo
    * def saldoEsperado = saldoInicialEmisor - montoTransferencia
    And match response.balance == saldoEsperado
    * store.put('saldoFinalEmisor', response.balance)

  @escenario3
  Scenario: Escenario 3 - Validacion del saldo y del historial en el Receptor
    * def receptor = store.get('receptor')
    * def emisor = store.get('emisor')
    * def saldoInicialReceptor = store.get('saldoInicialReceptor')
    * def codigoTransaccion = store.get('codigoTransaccion')
    * def transactionId = store.get('transactionId')

    # ---------- Login Receptor y captura del token Bearer ----------
    Given url authUrl
    And path 'login'
    And request { phone: '#(receptor.phone)', pin: '#(receptor.pin)' }
    When method post
    Then status 200
    And match response.token == '#notnull'
    And match response.user.id == receptor.id
    * def tokenReceptor = response.token

    # ---------- Saldo del Receptor: saldo_inicial + 450.00 ----------
    Given url walletUrl
    And path 'balance'
    And header Authorization = 'Bearer ' + tokenReceptor
    When method get
    Then status 200
    And match response == esquemaSaldo
    * def saldoEsperado = saldoInicialReceptor + montoTransferencia
    And match response.balance == saldoEsperado
    * store.put('saldoFinalReceptor', response.balance)

    # ---------- Historial de transacciones del Receptor ----------
    Given url walletUrl
    And path 'transactions'
    And header Authorization = 'Bearer ' + tokenReceptor
    When method get
    Then status 200
    And match response == '#[_ > 0]'
    And match each response contains { id: '#string', referenceCode: '#string', type: '#string', amount: '#number', date: '#string' }
    And match response[*].referenceCode contains codigoTransaccion

    * def movimiento = karate.filter(response, function(t){ return t.referenceCode == codigoTransaccion })[0]
    * def descripcionEsperada = 'De: ' + emisor.phone + '. ' + notaTransferencia
    And match movimiento contains { type: 'INCOME', amount: '#(montoTransferencia)', counterpartyPhone: '#(emisor.phone)', description: '#(descripcionEsperada)' }

    # Hallazgo H-01: el transactionId devuelto por /transfer no se persiste en el historial.
    * def idEnHistorial = karate.filter(response, function(t){ return t.id == transactionId }).length > 0
    * if (!idEnHistorial) karate.log('[HALLAZGO H-01] transactionId', transactionId, 'no figura en el historial; el enlace es referenceCode', codigoTransaccion)
