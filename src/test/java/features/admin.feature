@admin @parallel=false
Feature: Feature 3 - Flujo Administrador: auditoria de la transaccion

  Usa los datos que regression.feature dejo en el almacen global (usuarios,
  saldos y codigo de transaccion) para validar la operacion desde el backoffice.

  Background:
    * configure headers = { 'x-channel': '#(adminChannel)', 'Content-Type': 'application/json' }
    * def emisor = store.get('emisor')
    * def receptor = store.get('receptor')
    * def codigoTransaccion = store.get('codigoTransaccion')

  @admin-login
  Scenario: Login de administrador con credenciales validas e invalidas
    Given url adminUrl
    And path 'login'
    And request adminCredentials
    When method post
    Then status 200
    And match response == { token: '#notnull', type: 'Bearer', expiresIn: '#number', message: '##string' }
    And match response.expiresIn == 14400

    Given url adminUrl
    And path 'login'
    And request { username: '#(adminCredentials.username)', password: 'clave-incorrecta' }
    When method post
    Then status 401
    And match response == { code: 'AUTH_003', message: '#string' }

  @admin-auditoria
  Scenario: El administrador valida la transaccion en la auditoria global
    * def admin = call read('classpath:features/common/admin-login.feature')

    Given url adminUrl
    And path 'transactions'
    And header Authorization = 'Bearer ' + admin.token
    When method get
    Then status 200
    And match response == '#[_ > 0]'
    And match response[*].referenceCode contains codigoTransaccion

    # La operacion genera dos asientos con la misma referencia: debito y credito
    * def asientos = karate.filter(response, function(t){ return t.referenceCode == codigoTransaccion })
    * match asientos == '#[2]'
    * def debito = karate.filter(asientos, function(t){ return t.type == 'EXPENSE' })[0]
    * def credito = karate.filter(asientos, function(t){ return t.type == 'INCOME' })[0]

    * table asercionesAsiento
      | asiento | userId      | type      | contraparte    |
      | debito  | emisor.id   | 'EXPENSE' | receptor.phone |
      | credito | receptor.id | 'INCOME'  | emisor.phone   |
    * def validar =
      """
      function(r) {
        var esperado = { userId: r.userId, type: r.type, amount: montoTransferencia, counterpartyPhone: r.contraparte, referenceCode: codigoTransaccion, id: '#string', date: '#string' };
        var actual = karate.filterKeys(r.asiento, esperado);
        return karate.match(actual, esperado).pass;
      }
      """
    * def resultados = karate.map(asercionesAsiento, validar)
    * match resultados == [true, true]
    * match debito.description contains notaTransferencia
    * match credito.description contains notaTransferencia

  @admin-usuarios
  Scenario: El administrador confirma los saldos finales de Emisor y Receptor
    * def admin = call read('classpath:features/common/admin-login.feature')
    * def saldoFinalEmisor = store.get('saldoFinalEmisor')
    * def saldoFinalReceptor = store.get('saldoFinalReceptor')

    Given url adminUrl
    And path 'users'
    And header Authorization = 'Bearer ' + admin.token
    When method get
    Then status 200
    And match response == '#[_ > 0]'

    # El entorno es compartido: solo se valida el esquema de los usuarios creados por esta ejecucion
    * def esquemaAdminUsuario = { id: '#string', phone: '#string', name: '#string', email: '##string', pin: '##string', status: '#string', contacts: '#array', balance: '#number' }
    * def buscar = function(id){ return karate.filter(response, function(u){ return u.id == id })[0] }
    * def usuarioEmisor = buscar(emisor.id)
    * def usuarioReceptor = buscar(receptor.id)
    * match usuarioEmisor == esquemaAdminUsuario
    * match usuarioReceptor == esquemaAdminUsuario
    * match usuarioEmisor contains { phone: '#(emisor.phone)', status: 'ACTIVE', balance: '#(saldoFinalEmisor)' }
    * match usuarioReceptor contains { phone: '#(receptor.phone)', status: 'ACTIVE', balance: '#(saldoFinalReceptor)' }

  @admin-seguridad
  Scenario Outline: Acceso a la auditoria sin permisos de administrador - <caso>
    * def sesion = call read('classpath:features/common/login.feature') { phone: '#(emisor.phone)', pin: '#(emisor.pin)' }
    * def tokens = { ninguno: null, usuario: '#(sesion.token)' }
    * def token = tokens['<token>']
    * if (token) karate.set('authHeader', { Authorization: 'Bearer ' + token })
    * if (!token) karate.set('authHeader', {})

    Given url adminUrl
    And path 'transactions'
    And headers authHeader
    When method get
    Then status <status>
    And match response.code == '<codigo>'

    Examples:
      | caso                       | token   | status | codigo  |
      | sin token                  | ninguno | 401    | ADM_001 |
      | token de usuario sin rol   | usuario | 403    | ADM_002 |
