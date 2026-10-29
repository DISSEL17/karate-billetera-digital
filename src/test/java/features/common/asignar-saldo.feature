@ignore
Feature: Reutilizable - Asignar saldo a un usuario (Admin Service)

  Uso: * call read('classpath:features/common/asignar-saldo.feature') { userId: '...', amount: 2000, adminToken: '...' }

  Scenario: Abono administrativo (CREDIT)
    Given url adminUrl
    And path 'balance'
    And header x-channel = adminChannel
    And header Authorization = 'Bearer ' + adminToken
    And request { userId: '#(userId)', amount: '#(amount)', type: 'CREDIT', description: 'Saldo inicial QA' }
    When method post
    Then status 200
    And match response == { success: true, newBalance: '#number' }
    And match response.newBalance == amount
