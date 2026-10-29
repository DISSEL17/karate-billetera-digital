@ignore
Feature: Reutilizable - Login de Administrador (Admin Service)

  Uso: * def admin = call read('classpath:features/common/admin-login.feature')
  Retorna: token

  Scenario: Obtener token Bearer con rol ADMIN_SUPERUSER
    Given url adminUrl
    And path 'login'
    And header x-channel = adminChannel
    And request adminCredentials
    When method post
    Then status 200
    And match response == { token: '#string', type: 'Bearer', expiresIn: '#number', message: '##string' }
    * def token = response.token
