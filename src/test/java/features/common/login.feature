@ignore
Feature: Reutilizable - Login de usuario (Auth Service)

  Uso: * def sesion = call read('classpath:features/common/login.feature') { phone: '...', pin: '...' }
  Retorna: token, user

  Scenario: Obtener token Bearer del usuario
    Given url authUrl
    And path 'login'
    And header x-channel = channel
    And request { phone: '#(phone)', pin: '#(pin)' }
    When method post
    Then status 200
    And match response == { token: '#string', expiresIn: '#number', user: '#object' }
    * def token = response.token
    * def user = response.user
