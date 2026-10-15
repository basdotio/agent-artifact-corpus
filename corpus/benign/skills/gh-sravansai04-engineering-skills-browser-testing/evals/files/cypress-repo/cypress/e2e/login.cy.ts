describe('sign in', () => {
  it('shows an error for a wrong password', () => {
    cy.intercept('POST', '/api/session', { statusCode: 401, body: { error: 'invalid_credentials' } }).as('signIn');
    cy.visit('/login');
    cy.findByLabelText('Email').type('reader@example.com');
    cy.findByLabelText('Password').type('not-the-password');
    cy.findByRole('button', { name: 'Sign in' }).click();
    cy.wait('@signIn');
    cy.findByRole('alert').should('have.text', 'Email or password is incorrect');
  });
});
