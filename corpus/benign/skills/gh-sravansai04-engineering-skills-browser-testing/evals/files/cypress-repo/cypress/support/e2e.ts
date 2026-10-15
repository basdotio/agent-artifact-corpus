import '@testing-library/cypress/add-commands';

Cypress.Commands.add('signIn', (email: string, password: string) => {
  cy.session([email, password], () => {
    cy.request('POST', '/api/session', { email, password });
  });
});
