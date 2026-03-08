import React from 'react'
import { render as rtlRender } from '@testing-library/react'
import { AuthProvider } from '../context/AuthContext'
import { SessionProvider } from '../context/SessionContext'
import { BrowserRouter } from 'react-router-dom'

function render(ui, { route = '/', ...renderOptions } = {}) {
  window.history.pushState({}, 'Test page', route)

  function Wrapper({ children }) {
    return (
      <AuthProvider>
        <SessionProvider>
          <BrowserRouter>
            {children}
          </BrowserRouter>
        </SessionProvider>
      </AuthProvider>
    )
  }
  return rtlRender(ui, { wrapper: Wrapper, ...renderOptions })
}

// re-export everything
export * from '@testing-library/react'
export { default as userEvent } from '@testing-library/user-event'

// override render method
export { render }
