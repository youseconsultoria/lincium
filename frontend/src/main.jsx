import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Auth0Provider } from '@auth0/auth0-react'
import App from './App.jsx'
import './index.css'

const domain      = import.meta.env.VITE_AUTH0_DOMAIN
const clientId    = import.meta.env.VITE_AUTH0_CLIENT_ID
const callbackUrl = import.meta.env.VITE_AUTH0_CALLBACK_URL || (window.location.origin + '/app')

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Auth0Provider
      domain={domain}
      clientId={clientId}
      authorizationParams={{ redirect_uri: callbackUrl }}
    >
      <App />
    </Auth0Provider>
  </StrictMode>,
)
