import { render, screen, userEvent } from '../../test/test-utils'
import { describe, it, expect } from 'vitest'
import LoginPage from '../Auth/LoginPage'

describe('LoginPage', () => {
  it('renders login form properly', () => {
    render(<LoginPage />)
    expect(screen.getByRole('heading', { name: /sign in to spendos/i })).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: /email address/i })).toBeInTheDocument()
    // By default getByRole 'button' will catch "Sign In"
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('allows typing in email and password', async () => {
    const user = userEvent.setup()
    render(<LoginPage />)
    
    const emailInput = screen.getByRole('textbox', { name: /email address/i })
    const passwordInput = screen.getByLabelText(/password/i) // password inputs don't have 'textbox' role
    
    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'secretpassword')
    
    expect(emailInput).toHaveValue('test@example.com')
    expect(passwordInput).toHaveValue('secretpassword')
  })

  it('submits form with valid credentials', async () => {
    const user = userEvent.setup()
    render(<LoginPage />)
    
    const emailInput = screen.getByRole('textbox', { name: /email address/i })
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'secretpassword')
    await user.click(submitButton)

    // With our MSW mock in place, the login will succeed, and it should transition navigating
    // Since we mocked standard success, we won't see an error box
    expect(screen.queryByText(/invalid credentials/i)).not.toBeInTheDocument()
  })
})
