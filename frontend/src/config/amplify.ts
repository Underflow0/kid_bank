/**
 * AWS Amplify configuration
 */
import { Amplify } from 'aws-amplify';

const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_USER_POOL_ID || '',
      userPoolClientId: import.meta.env.VITE_USER_POOL_CLIENT_ID || '',
      loginWith: {
        oauth: {
          domain: import.meta.env.VITE_COGNITO_DOMAIN?.replace('https://', '') || '',
          scopes: ['email', 'openid', 'profile'],
          redirectSignIn: [window.location.origin + '/callback'],
          redirectSignOut: [window.location.origin + '/logout'],
          responseType: 'code',
        },
        email: true,
      },
    },
  },
};

export const configureAmplify = () => {
  try {
    Amplify.configure(amplifyConfig);
    console.log('Amplify configured successfully');
  } catch (error) {
    console.error('Error configuring Amplify:', error);
  }
};

export default amplifyConfig;
